"""Generate result.json with a fine-tuned model.

This script builds the same ``instruction`` / ``input`` prompt format that was
used to fine-tune the model (see ``tmp/train.json``), connects to the model
through an OpenAI-compatible HTTP endpoint (vLLM/SGLang style), and normalizes
the model output into the competition ``result.json`` format.

Routing and schema retrieval reuse existing scripts:

* ``scripts/database_routing/embedding_classifier.py`` -- engine-set routing
* ``scripts/information_retrieval/index.py`` -- schema/example retrieval index
* ``scripts/information_retrieval/context.py`` -- bounded candidate-table recall

The fine-tuned model is not bundled in this repository.  Point the script at a
running OpenAI-compatible server with ``--endpoint`` (default
``http://127.0.0.1:8000/v1/chat/completions``).  Set ``--model`` to the model
name served by that server.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / 'scripts/information_retrieval', ROOT / 'scripts/database_routing'):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from index import RetrievalIndex, make_encoder, write_json  # noqa: E402
from context import Budget, ContextBuilder  # noqa: E402
from embedding_classifier import DEFAULT_MODEL, LocalEncoder  # noqa: E402

ROUTING_INSTRUCTION = 'Identify the business entities and data requirements of this database query for database routing.'

CATALOG_PATH = ROOT / 'data/preprocessed/schema_catalog.json'
QA_TEST_PATH = ROOT / 'data/赛题8/QA_test.json'
TRAINING_SOURCE = 'data/赛题8/QA_train.json'

# The official instruction labels PostgreSQL and Elasticsearch with these fixed
# database names even though the catalog stores schema/index names instead.
PG_DATABASE = 'ais'
ES_DATABASE = 'medical_institutions'

# The competition treats the administrative division table as knowledge; the
# fine-tuning instructions never contain it, so never inject it into prompts.
EXCLUDED_SOURCE_IDS = {'schema:MYSQL:common.administrative_division'}
EXCLUDED_TABLE_IDS = {'MYSQL:common.administrative_division'}

ENGINES = {'MYSQL', 'POSTGRESQL', 'SQLite', 'Elasticsearch'}


# --------------------------------------------------------------------------- #
# Instruction builder (mirrors tmp/train.json exactly)
# --------------------------------------------------------------------------- #

def normalize_ddl(raw_definition: str) -> str:
    """Convert a catalog raw_definition into the DDL block used by prompts."""
    text = (raw_definition or '').rstrip()
    if text.endswith(';'):
        text = text[:-1].rstrip()
    index = text.rfind(')')
    if index == -1:
        return text + ';'
    return text[:index + 1].rstrip() + ';'


def es_mapping_block(table: dict) -> str:
    """Build the compact Elasticsearch mapping line used by prompts."""
    properties = {c['name']: c['mapping'] for c in table['columns']
                  if '.' not in c['name'] and c.get('mapping')}
    mapping = {'mappings': {'properties': properties}}
    return f"{table['name']} mapping: {json.dumps(mapping, ensure_ascii=False, separators=(',', ':'))}"


def database_label(table: dict) -> str:
    if table['engine'] == 'POSTGRESQL':
        return PG_DATABASE
    if table['engine'] == 'Elasticsearch':
        return ES_DATABASE
    return table.get('database') or table.get('schema') or table['name']


def order_tables_by_fk(table_ids, tables: dict) -> list:
    """Put FK-referencing tables before the tables they reference.

    Training prompts list tables in query FROM/JOIN order, so a fact table
    (for example ``transportation.vehicle``) precedes its lookup table
    (``common.vehicle_type_dict``) even though the common prefix sorts first.
    """
    ordered = list(table_ids)
    for a in ordered:
        for fk in tables[a].get('foreign_keys', []) or []:
            b = (fk.get('references') or {}).get('table_id')
            if b in ordered and b != a:
                ia, ib = ordered.index(a), ordered.index(b)
                if ia > ib:
                    ordered.pop(ib)
                    ordered.insert(ia, b)
    return ordered


def build_instruction(table_ids, tables: dict) -> str:
    """Build the fine-tuning instruction for an ordered list of table_ids."""
    ordered_ids = order_tables_by_fk(table_ids, tables)
    grouped = []
    by_key = {}
    for table_id in ordered_ids:
        table = tables[table_id]
        key = (table['engine'], database_label(table))
        if key not in by_key:
            by_key[key] = {'engine': table['engine'], 'database': key[1], 'blocks': []}
            grouped.append(by_key[key])
        block = es_mapping_block(table) if table['engine'] == 'Elasticsearch' else normalize_ddl(table['raw_definition'])
        by_key[key]['blocks'].append(block)

    groups = grouped

    engines = list(dict.fromkeys(g['engine'] for g in groups))
    databases = [g['database'] for g in groups]
    if len(engines) > 1:
        output_instruction = ('这是跨数据源的两步查询。只输出一个 JSON 对象，字段依次为 '
                              'db1、query1、db2、query2；第二步按原赛题协议使用第一步结果 result。不要解释。')
    elif engines[0] == 'Elasticsearch':
        output_instruction = '只输出 Elasticsearch JSON DSL 字符串，不要解释、Markdown 或 HTTP 路径。'
    else:
        output_instruction = '只输出一条只读 SQL 查询，不要解释、Markdown 或附加字段。'

    header = '\n'.join([
        '根据下列官方数据库结构，将问题转换为查询。',
        output_instruction,
        '涉及的数据源：' + '、'.join(engines),
        '涉及的数据库：' + '、'.join(databases),
        '官方表结构：',
    ])
    body = []
    for group in groups:
        body.append(f"[{group['engine']} / {group['database']}]")
        body.append('\n'.join(group['blocks']))
    return header + '\n' + '\n'.join(body)


# --------------------------------------------------------------------------- #
# Routing reuse
# --------------------------------------------------------------------------- #

def load_routing_predictor(routing_dir: Path, device: str, dtype: str):
    """Return ``(predict, encoder)`` for engine-set labels."""
    summary_path = routing_dir / 'summary.json'
    classifier_path = routing_dir / 'classifier.npz'
    if not summary_path.exists() or not classifier_path.exists():
        raise FileNotFoundError(
            f'Routing classifier not found under {routing_dir}. '
            'Run scripts/information_retrieval/generate_submission.py --prepare-only first, '
            'or point --routing-dir at a directory containing summary.json + classifier.npz.')
    encoder = LocalEncoder(DEFAULT_MODEL, routing_dir, max_length=256,
                           device=device, dtype=dtype, instruction=ROUTING_INSTRUCTION)
    summary = json.loads(summary_path.read_text())
    if summary.get('encoder_settings') != encoder.signature:
        raise ValueError('Routing encoder settings mismatch; use the same device/dtype or rebuild the classifier.')
    with np.load(classifier_path, allow_pickle=False) as saved:
        coef, intercept, classes = saved['coef'], saved['intercept'], saved['classes']

    def predict(questions):
        vectors = encoder.encode(list(questions))
        scores = vectors @ coef.T + intercept
        return [str(classes[i]) for i in scores.argmax(axis=1)]

    return predict, encoder


# --------------------------------------------------------------------------- #
# Output parsing / normalization
# --------------------------------------------------------------------------- #

def strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```[a-zA-Z]*\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def normalize_output(raw: str, engines, question_id: int) -> dict:
    """Turn raw model text into a result.json entry."""
    text = strip_fences(raw)
    if len(engines) > 1:
        try:
            value = json.loads(text)
        except ValueError as error:
            raise ValueError(f'跨数据源输出不是合法 JSON：{text[:200]}') from error
        if not isinstance(value, dict):
            raise ValueError('跨数据源输出必须是 JSON 对象')
        pairs = []
        for index in range(1, 5):
            db_key, query_key = f'db{index}', f'query{index}'
            if db_key in value or query_key in value:
                if db_key not in value or query_key not in value:
                    raise ValueError(f'{db_key}/{query_key} 必须成对出现')
                if value[db_key] not in ENGINES or not isinstance(value[query_key], str):
                    raise ValueError(f'{db_key}/{query_key} 内容无效')
                pairs.append((db_key, query_key))
        if len(pairs) < 2:
            raise ValueError('跨数据源输出至少需要 db1/query1 与 db2/query2')
        entry = {'question_id': question_id}
        for db_key, query_key in pairs:
            entry[db_key] = value[db_key]
            entry[query_key] = value[query_key].strip()
        return entry

    if len(engines) != 1:
        raise ValueError('无法确定目标数据源')
    engine = engines[0]
    if engine == 'Elasticsearch':
        # Accept an object and serialize it; otherwise keep the raw DSL string.
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
        except ValueError:
            pass
    if not text:
        raise ValueError('查询为空')
    return {'question_id': question_id, 'db': engine, 'query': text}


# --------------------------------------------------------------------------- #
# Fine-tuned model client (OpenAI-compatible)
# --------------------------------------------------------------------------- #

class ModelClient:
    def __init__(self, endpoint, model, api_key=None, temperature=0.0, max_tokens=4096,
                 timeout=300, retries=2, prompt_style='chat'):
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries
        self.prompt_style = prompt_style
        self.calls = []

    def complete(self, instruction: str, question: str) -> str:
        if self.prompt_style == 'alpaca':
            prompt = f'### Instruction:\n{instruction}\n\n### Input:\n{question}\n\n### Response:\n'
            messages = [{'role': 'user', 'content': prompt}]
        else:
            messages = [{'role': 'system', 'content': instruction},
                        {'role': 'user', 'content': question}]
        payload = {'model': self.model, 'messages': messages,
                   'temperature': self.temperature, 'max_tokens': self.max_tokens}
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        for attempt in range(self.retries + 1):
            started = time.monotonic()
            record = {'attempt': attempt + 1}
            self.calls.append(record)
            try:
                request = urllib.request.Request(self.endpoint, json.dumps(payload).encode(), headers)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    value = json.load(response)
                record.update(latency_seconds=time.monotonic() - started, success=True,
                              usage=value.get('usage', {}), response_model=value.get('model'),
                              finish_reason=value['choices'][0].get('finish_reason'))
                return value['choices'][0]['message']['content']
            except (urllib.error.URLError, TimeoutError, OSError, KeyError, json.JSONDecodeError) as error:
                record.update(latency_seconds=time.monotonic() - started, success=False,
                              error_type=type(error).__name__, error=str(error)[:200])
                retryable = not isinstance(error, urllib.error.HTTPError) or error.code in (408, 429) or error.code >= 500
                if not retryable or attempt == self.retries:
                    raise RuntimeError(f'模型请求失败：{type(error).__name__}: {str(error)[:200]}') from error
                time.sleep(min(2 ** attempt, 4))


# --------------------------------------------------------------------------- #
# Candidate table recall
# --------------------------------------------------------------------------- #

def order_engines(question: str, engine_set, index) -> list:
    """Preserve db1/db2 order for cross-source questions via nearest example."""
    engines = sorted(engine_set)
    if len(engines) == 1:
        return engines
    hits = index.search(question, 'example', engines, limit=1, exact_engines=True)
    if hits:
        steps = index.by_id[hits[0]['source_id']]['data']['steps']
        ordered = list(dict.fromkeys(s['engine'] for s in steps if s['engine'] in engines))
        if set(ordered) == set(engines):
            return ordered
    return engines


def recall_tables(question: str, engines, index, max_tables: int, mode: str, example_k: int) -> list:
    """Recall candidate tables.

    ``examples`` reuses the exact table sets of the nearest training examples,
    which is closest to the fine-tuning prompt distribution.  ``schema`` reuses
    the bounded schema/keyword retrieval from the existing information
    retrieval pipeline, which has higher recall for cross-domain questions.
    """
    if mode == 'examples':
        hits = index.search(question, 'example', engines, limit=example_k, exact_engines=True)
        if hits:
            def _database(tid):
                return tid.split(':', 1)[1].rsplit('.', 1)[0]
            table_ids = []
            base_databases = set()
            # The nearest example defines the coherent database set.
            for step in index.by_id[hits[0]['source_id']]['data']['steps']:
                for tid in step['table_ids']:
                    if tid not in EXCLUDED_TABLE_IDS and tid not in table_ids:
                        table_ids.append(tid)
                        base_databases.add(_database(tid))
            # Other examples only add tables inside that database set, so a
            # single SQLite/MySQL question never mixes unrelated databases.
            for hit in hits[1:]:
                for step in index.by_id[hit['source_id']]['data']['steps']:
                    for tid in step['table_ids']:
                        if (_database(tid) in base_databases and tid not in EXCLUDED_TABLE_IDS
                                and tid not in table_ids):
                            table_ids.append(tid)
                        if len(table_ids) >= max_tables:
                            return table_ids
            return table_ids
        mode = 'schema'
    builder = ContextBuilder(index, Budget(initial_tables=max_tables, extra_tables=4,
                                           total_tables=max(8, max_tables + 2)))
    table_ids = []
    for item in builder.retrieve(question, engines, limit=max_tables, exclude=EXCLUDED_SOURCE_IDS):
        for table_id in item['table_ids']:
            if table_id not in table_ids and table_id not in EXCLUDED_TABLE_IDS:
                table_ids.append(table_id)
    return table_ids[:max_tables]


# --------------------------------------------------------------------------- #
# Worker
# --------------------------------------------------------------------------- #

def worker(question_row, directory, client_kwargs):
    target = directory / f"question_{question_row['question_id']}.json"
    if target.exists():
        previous = json.loads(target.read_text())
        if previous.get('result') and not previous.get('error'):
            return previous
    prepared = json.loads((directory / f"prepared_{question_row['question_id']}.json").read_text())
    engines = prepared['engines']
    client = ModelClient(**client_kwargs)
    raw = client.complete(prepared['instruction'], question_row['question'])
    try:
        result = normalize_output(raw, engines, question_row['question_id'])
        output = {'question': question_row, 'engines': engines, 'raw': raw,
                  'result': result, 'calls': client.calls, 'error': None}
    except Exception as error:
        output = {'question': question_row, 'engines': engines, 'raw': raw,
                  'result': None, 'calls': client.calls, 'error': str(error)}
    write_json(target, output)
    return output


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/finetuned_inference')
    parser.add_argument('--routing-dir', type=Path,
                        default=ROOT / 'outputs/qa_test_deepseek_v4_pro_full_train/routing_full_train')
    parser.add_argument('--index-dir', type=Path,
                        default=ROOT / 'outputs/qa_test_deepseek_v4_pro_full_train/index_full_train')
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--dtype', default='float16')
    parser.add_argument('--max-tables', type=int, default=6)
    parser.add_argument('--recall', choices=('examples', 'schema'), default='examples')
    parser.add_argument('--example-k', type=int, default=3)
    parser.add_argument('--endpoint', default=os.environ.get('FINETUNED_ENDPOINT', 'http://127.0.0.1:8000/v1/chat/completions'))
    parser.add_argument('--model', default=os.environ.get('FINETUNED_MODEL', 'finetuned-model'))
    parser.add_argument('--api-key', default=os.environ.get('FINETUNED_API_KEY', ''))
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--max-tokens', type=int, default=4096)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--retries', type=int, default=2)
    parser.add_argument('--prompt-style', choices=('chat', 'alpaca'), default='chat')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--limit', type=int, default=0, help='只处理前 N 题（0 表示全部）')
    parser.add_argument('--result-path', type=Path, default=ROOT / 'result.json')
    parser.add_argument('--prepare-only', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    directory = args.output_dir
    directory.mkdir(parents=True, exist_ok=True)
    rows = json.loads(QA_TEST_PATH.read_text())
    if args.limit:
        rows = rows[:args.limit]
    assert len({r['question_id'] for r in rows}) == len(rows)
    assert all(set(r) == {'question_id', 'question'} for r in rows)

    write_json(directory / 'run_config.json', {
        'script': str(Path(__file__).relative_to(ROOT)),
        'questions': len(rows),
        'endpoint': args.endpoint,
        'model': args.model,
        'prompt_style': args.prompt_style,
        'temperature': args.temperature,
        'max_tokens': args.max_tokens,
        'max_tables': args.max_tables,
        'device': args.device,
        'dtype': args.dtype,
        'routing_dir': str(args.routing_dir),
        'index_dir': str(args.index_dir),
    })

    catalog = json.loads(CATALOG_PATH.read_text())
    tables = {t['table_id']: t for t in catalog['tables']}
    assert EXCLUDED_TABLE_IDS <= set(tables)

    # 1) Engine-set routing (reuse cached classifier + Qwen embedding encoder).
    predict_engines, _routing_encoder = load_routing_predictor(args.routing_dir, args.device, args.dtype)
    labels = predict_engines([r['question'] for r in rows])
    engine_sets = [set(lbl.split('|')) for lbl in labels]
    del _routing_encoder

    # 2) Schema retrieval index (reuse full-training index).
    retrieval_encoder = make_encoder(device=args.device, dtype=args.dtype)
    index = RetrievalIndex.load(args.index_dir, retrieval_encoder, training_source=TRAINING_SOURCE)

    # 3) Prepare instruction/input per question (resumable).
    for row, engine_set in zip(rows, engine_sets):
        prepared_path = directory / f"prepared_{row['question_id']}.json"
        if prepared_path.exists():
            continue
        engines = order_engines(row['question'], engine_set, index)
        table_ids = recall_tables(row['question'], engines, index, args.max_tables, args.recall, args.example_k)
        instruction = build_instruction(table_ids, tables)
        write_json(prepared_path, {
            'question': row,
            'engines': engines,
            'table_ids': table_ids,
            'instruction': instruction,
            'input': row['question'],
        })
        print(json.dumps({'prepared': row['question_id'], 'engines': engines, 'tables': table_ids},
                         ensure_ascii=False), flush=True)

    if args.prepare_only:
        print(json.dumps({'status': 'prepared', 'directory': str(directory), 'questions': len(rows)},
                         ensure_ascii=False))
        return

    if not args.endpoint:
        raise SystemExit('--endpoint is required (or set FINETUNED_ENDPOINT)')

    client_kwargs = dict(endpoint=args.endpoint, model=args.model, api_key=args.api_key or None,
                         temperature=args.temperature, max_tokens=args.max_tokens,
                         timeout=args.timeout, retries=args.retries, prompt_style=args.prompt_style)

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(worker, row, directory, client_kwargs): row['question_id']
                   for row in rows}
        for future in as_completed(futures):
            output = future.result()
            results.append(output)
            print(json.dumps({'finished': len(results), 'question_id': output['question']['question_id'],
                              'success': bool(output.get('result'))}, ensure_ascii=False), flush=True)
            write_json(directory / 'progress.json', {
                'finished': len(results),
                'success': sum(bool(x.get('result')) for x in results),
                'failed': [x['question']['question_id'] for x in results if not x.get('result')],
            })

    failed = [x['question']['question_id'] for x in results if not x.get('result')]
    if failed:
        write_json(directory / 'failed.json', failed)
        raise SystemExit(f'有 {len(failed)} 题未成功，结果已落盘。重跑可续传。')

    by_id = {x['question']['question_id']: x['result'] for x in results}
    submission = [by_id[r['question_id']] for r in rows]
    write_json(args.result_path, submission)
    print(json.dumps({'result': str(args.result_path), 'questions': len(submission)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
