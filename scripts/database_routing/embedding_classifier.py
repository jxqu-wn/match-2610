"""Local Qwen embedding classifier and offline evaluation.

Training labels are used only to fit/select classifiers. Validation labels are
used only for reporting. Cache entries are keyed by text and model settings.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
from sklearn.linear_model import LogisticRegression

from experiment import Model as CharacterModel, features, label

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / 'models/Qwen3-Embedding-0.6B'
DEFAULT_OUTPUT = ROOT / 'outputs/database_routing/embedding'
INSTRUCTION = 'Identify the business entities and data requirements of this database query for database routing.'


def load_rows(name):
    return json.loads((ROOT / 'data/赛题8/splits' / f'{name}.json').read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def resolve_runtime(device, dtype, quantize):
    import torch
    if device == 'auto':
        device = 'cpu' if quantize or not torch.cuda.is_available() else 'cuda'
    resolved = torch.device(device)
    if resolved.type not in ('cpu', 'cuda'):
        raise ValueError('仅支持 cpu、cuda、cuda:N 或 auto')
    if resolved.type == 'cuda':
        if not torch.cuda.is_available():
            raise ValueError('CUDA 不可用，请安装 CUDA 版 PyTorch 并检查 GPU，或使用 --device cpu')
        index = resolved.index if resolved.index is not None else torch.cuda.current_device()
        if index < 0 or index >= torch.cuda.device_count():
            raise ValueError(f'CUDA 设备编号无效：{index}')
        resolved = torch.device(f'cuda:{index}')
    if quantize and resolved.type != 'cpu':
        raise ValueError('--int8 是 CPU 动态量化，不能与 CUDA 一起使用')
    if dtype == 'auto':
        dtype = 'float32' if resolved.type == 'cpu' else 'float16'
    if dtype not in ('float32', 'float16', 'bfloat16'):
        raise ValueError(f'不支持的 dtype：{dtype}')
    if resolved.type == 'cpu' and dtype != 'float32':
        raise ValueError('CPU 路径使用 float32；低精度请使用 CUDA')
    if resolved.type == 'cuda' and dtype == 'bfloat16':
        with torch.cuda.device(resolved):
            if not torch.cuda.is_bf16_supported():
                raise ValueError('所选 GPU 不支持 bfloat16，请使用 float16 或 float32')
    return resolved, dtype


class LocalEncoder:
    def __init__(self, model_path, output, batch_size=8, max_length=256,
                 threads=6, quantize=False, device='cpu', dtype='auto', instruction=INSTRUCTION):
        self.device, self.dtype = resolve_runtime(device, dtype, quantize)
        if batch_size < 1 or max_length < 1 or threads < 1:
            raise ValueError('batch-size、max-length 和 threads 必须为正整数')
        self.model_path = Path(model_path).resolve()
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.batch_size, self.max_length = batch_size, max_length
        self.threads, self.quantize = threads, quantize
        self.instruction = instruction
        signature = {'model_path': str(self.model_path), 'max_length': max_length,
                     'instruction': instruction, 'quantize': quantize,
                     'pooling': 'last_token', 'normalization': 'l2',
                     'files': {name: [ (self.model_path/name).stat().st_size,
                                      (self.model_path/name).stat().st_mtime_ns]
                               for name in ('model.safetensors', 'tokenizer.json', 'config.json')}}
        self.signature = signature
        # Preserve existing CPU fp32 caches/classifiers. GPU precision and
        # backend have separate caches to avoid silently mixing embeddings.
        if self.device.type != 'cpu' or self.dtype != 'float32':
            signature.update(device=self.device.type, dtype=self.dtype)
        digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16]
        self.cache_path = self.output / f'embeddings_{digest}.npz'
        self.cache = {}
        if self.cache_path.exists():
            with np.load(self.cache_path, allow_pickle=False) as cached:
                self.cache = dict(zip(cached['texts'].tolist(), cached['vectors']))
        self.model = self.tokenizer = None

    def _load(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        torch.set_num_threads(self.threads)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, padding_side='left', local_files_only=True)
        self.model = AutoModel.from_pretrained(
            self.model_path, local_files_only=True, dtype=getattr(torch, self.dtype)).eval()
        if self.quantize:
            # CPU dynamic int8 applies to Linear layers; embedding table stays fp32.
            self.model = torch.ao.quantization.quantize_dynamic(
                self.model, {torch.nn.Linear}, dtype=torch.qint8)
        self.model = self.model.to(self.device)

    def _save(self):
        temporary = self.cache_path.with_suffix('.tmp.npz')
        np.savez_compressed(temporary, texts=np.array(list(self.cache)),
                            vectors=np.stack(list(self.cache.values())))
        temporary.replace(self.cache_path)

    def encode(self, texts):
        import torch
        missing = list(dict.fromkeys(t for t in texts if t not in self.cache))
        if missing and self.model is None:
            self._load()
        start = time.time()
        for offset in range(0, len(missing), self.batch_size):
            batch = missing[offset:offset+self.batch_size]
            inputs = self.tokenizer([f'Instruct: {self.instruction}\nQuery: {t}' for t in batch],
                                    padding=True, truncation=True,
                                    max_length=self.max_length, return_tensors='pt')
            inputs = inputs.to(self.device)
            with torch.inference_mode():
                outputs = self.model(**inputs, use_cache=False)
                # Left padding puts every sequence's last actual token at -1.
                vectors = torch.nn.functional.normalize(outputs.last_hidden_state[:, -1].float(), dim=1)
            vectors = vectors.cpu().numpy()
            self.cache.update(zip(batch, vectors))
            done = min(offset+self.batch_size, len(missing))
            if done % (self.batch_size*16) == 0 or done == len(missing):
                self._save()
                print(f'Encoded {done}/{len(missing)} new questions in {time.time()-start:.1f}s', flush=True)
        return np.stack([self.cache[t] for t in texts])


def nearest_predict(train_x, train_y, query_x, k=1):
    similarities = query_x @ train_x.T
    indices = np.argsort(-similarities, axis=1, kind='stable')[:, :k]
    predictions = []
    for row, neighbors in enumerate(indices):
        votes = Counter()
        for i in neighbors:
            votes[train_y[i]] += max(float(similarities[row, i]), 0)**3
        predictions.append(max(votes, key=votes.get))
    return np.array(predictions)


def internal_split(rows):
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(label(row), []).append(i)
    rng = random.Random(2026)
    fit, dev = [], []
    for key in sorted(groups):
        indices = groups[key][:]
        rng.shuffle(indices)
        count = max(1, round(len(indices)*0.1))
        dev.extend(indices[:count])
        fit.extend(indices[count:])
    dev_texts = {rows[i]['question'] for i in dev}
    fit = [i for i in fit if rows[i]['question'] not in dev_texts]
    return fit, dev


def metrics(rows, predictions):
    actual = np.array([label(r) for r in rows])
    predicted = np.array(predictions)
    return {'count': len(rows), 'correct': int((actual == predicted).sum()),
            'database_set_accuracy': float((actual == predicted).mean()),
            'single_multi_accuracy': float(np.mean([
                ('|' in a) == ('|' in p) for a, p in zip(actual, predicted)])),
            'by_database': {c: {'count': int((actual == c).sum()),
                                'accuracy': float((predicted[actual == c] == c).mean())}
                            for c in sorted(set(actual))}}


def evaluate(args, encoder):
    train, validation = load_rows('train'), load_rows('validation')
    # Exclude exact evaluation texts, including all duplicate training instances.
    validation_texts = {row['question'] for row in validation}
    train = [row for row in train if row['question'] not in validation_texts]
    fit, dev = internal_split(train)
    all_x = encoder.encode([r['question'] for r in train+validation])
    train_x, validation_x = all_x[:len(train)], all_x[len(train):]
    train_y = np.array([label(r) for r in train])
    candidates = {}
    for k in (1, 3, 5):
        predicted = nearest_predict(train_x[fit], train_y[fit], train_x[dev], k)
        candidates[f'knn{k}'] = float((predicted == train_y[dev]).mean())
    for c in (0.1, 1.0, 10.0, 100.0):
        model = LogisticRegression(C=c, max_iter=2000, random_state=42)
        model.fit(train_x[fit], train_y[fit])
        candidates[f'logistic_C{c}'] = float((model.predict(train_x[dev]) == train_y[dev]).mean())
    selected = max(candidates, key=candidates.get)
    if selected.startswith('knn'):
        prediction = nearest_predict(train_x, train_y, validation_x, int(selected[3:]))
    else:
        model = LogisticRegression(C=float(selected.split('_C')[1]), max_iter=2000, random_state=42)
        model.fit(train_x, train_y)
        prediction = model.predict(validation_x)
        # Store coefficients as data, no executable pickle. Multiclass softmax argmax.
        np.savez(args.output/'classifier.npz', coef=model.coef_, intercept=model.intercept_,
                 classes=model.classes_)
    char_model = CharacterModel(train)
    character_predictions = []
    for row in validation:
        scores = char_model.linear_scores(char_model.vector(features(row['question'])))
        character_predictions.append(max(scores, key=scores.get))
    details = [dict(question_id=row['question_id'], question=row['question'], expected=label(row),
                    predicted=str(p), character_predicted=cp, correct=p == label(row))
               for row, p, cp in zip(validation, prediction, character_predictions)]
    summary = {'model': str(args.model), 'encoder_settings': encoder.signature,
               'training_size': len(train), 'internal_fit_size': len(fit), 'internal_dev_size': len(dev),
               'dev_candidates': candidates, 'selected_method': selected,
               'embedding': metrics(validation, prediction),
               'character_linear': metrics(validation, character_predictions),
               'scope': 'Database engine sets only; excludes exact validation texts from training.'}
    write_json(args.output/'summary.json', summary)
    write_json(args.output/'predictions.json', details)
    write_json(args.output/'errors.json', [r for r in details if not r['correct']])
    write_json(args.output/'split_ids.json', {'fit': [train[i]['question_id'] for i in fit],
                                            'dev': [train[i]['question_id'] for i in dev]})
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def predict(args, encoder):
    if not args.question.strip():
        raise ValueError('问题不能为空')
    summary = json.loads((args.output/'summary.json').read_text())
    if summary['encoder_settings'] != encoder.signature:
        raise ValueError('模型设置与评估时不同，请使用相同参数或重新评估')
    vector = encoder.encode([args.question])
    method = summary['selected_method']
    if method.startswith('logistic'):
        with np.load(args.output/'classifier.npz', allow_pickle=False) as classifier:
            scores = vector @ classifier['coef'].T + classifier['intercept']
            prediction = str(classifier['classes'][scores.argmax(axis=1)[0]])
    else:
        validation_texts = {r['question'] for r in load_rows('validation')}
        rows = [r for r in load_rows('train') if r['question'] not in validation_texts]
        train_x = encoder.encode([r['question'] for r in rows])
        prediction = str(nearest_predict(train_x, np.array([label(r) for r in rows]),
                                         vector, int(method[3:]))[0])
    print(json.dumps({'question': args.question, 'databases': prediction.split('|'),
                      'query_type': 'multi' if '|' in prediction else 'single',
                      'method': method}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('evaluate', 'predict'))
    parser.add_argument('--question', default='')
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--max-length', type=int, default=256)
    parser.add_argument('--threads', type=int, default=6)
    parser.add_argument('--int8', action='store_true', help='CPU dynamic int8 for Linear layers')
    parser.add_argument('--device', default='cpu', help='cpu (默认)、auto、cuda 或 cuda:N')
    parser.add_argument('--dtype', default='auto', choices=('auto', 'float32', 'float16', 'bfloat16'),
                        help='auto: CPU float32 / CUDA float16')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    encoder = LocalEncoder(args.model, args.output, args.batch_size, args.max_length,
                           args.threads, args.int8, args.device, args.dtype)
    if args.command == 'evaluate':
        evaluate(args, encoder)
    else:
        predict(args, encoder)


if __name__ == '__main__':
    main()
