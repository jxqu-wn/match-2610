"""Resumable live validation sampling; reference answers remain local."""
import argparse
import json
import os
import random
import unicodedata
import sys
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path

from index import ROOT, DEFAULT_INDEX, RetrievalIndex, SourceResolver, engine_set, make_encoder, write_json
from planner import DeepSeekClient, Planner, SYSTEM
from context import ContextBuilder
from business_routing import database_id
from planner import PIPELINE_VERSION
from token_report import context_profile, summarize_tokens

OUTPUT = ROOT / 'outputs/information_retrieval/live_explicit_knowledge_v5'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    global OUTPUT
    parser.add_argument('--output-directory', type=Path, default=OUTPUT)
    parser.add_argument('--sample-size', type=int, default=20)
    parser.add_argument('--random-seed', type=int)
    parser.add_argument('--exclude-selection', type=Path)
    parser.add_argument('--selection-file', type=Path, help='Reuse question IDs from a previous selection; labels are not used for inference')
    parser.add_argument('--predicted-routing', action='store_true')
    parser.add_argument('--prepare-only', action='store_true', help='Prepare sampled contexts and proxy token profiles locally; no API calls')
    args = parser.parse_args()
    OUTPUT = args.output_directory
    for target in OUTPUT.glob('question_*.json'):
        if json.loads(target.read_text()).get('pipeline_version') != PIPELINE_VERSION:
            raise ValueError('Old pipeline outputs in target directory; use a new --output-directory')
    index = RetrievalIndex.load(DEFAULT_INDEX, make_encoder(device='cuda', dtype='float16'))
    train_questions = {d['text'] for d in index.documents if d['kind'] == 'example'}
    rows = json.loads((ROOT / 'data/赛题8/splits/validation.json').read_text())
    normalize = lambda text: ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())
    train_rows = json.loads((ROOT / 'data/赛题8/splits/train.json').read_text())
    training_by_id = {r['question_id']: r for r in train_rows}
    validation_ids = {r['question_id'] for r in rows}
    assert not set(training_by_id) & validation_ids, 'Train/validation IDs overlap'
    for doc in index.documents:
        if doc['kind'] == 'example':
            row = training_by_id.get(doc['data']['question_id'])
            assert row and row['question'] == doc['data']['question'], 'Non-training example in index'
            for step in doc['data']['steps']:
                assert row[step['step']] == step['query'], 'Indexed SQL differs from training split'
        if doc['kind'] == 'schema':
            assert all(t['question_id'] in training_by_id for t in doc['data'].get('training_examples', [])), 'Non-training catalog example'
    blocked = set()
    if args.exclude_selection:
        blocked = {r['question_id'] for r in json.loads(args.exclude_selection.read_text())}
    normalized_train = {normalize(r['question']) for r in train_rows}
    eligible = [r for r in rows if r['question_id'] not in blocked and normalize(r['question']) not in normalized_train]
    if args.selection_file:
        selection = json.loads(args.selection_file.read_text())
        ids = [r['question_id'] for r in selection]
        eligible_by_id = {r['question_id']: r for r in eligible}
        if len(ids) != args.sample_size or len(set(ids)) != len(ids) or not set(ids) <= set(eligible_by_id):
            raise ValueError('Selection must contain the requested number of unique eligible validation question IDs')
        chosen = [eligible_by_id[qid] for qid in ids]
    elif args.random_seed is not None:
        chosen = random.Random(args.random_seed).sample(eligible, args.sample_size)
    else:
        groups = defaultdict(list)
        for row in eligible:
            groups[tuple(engine_set(row))].append(row)
        chosen = []
        while len(chosen) < args.sample_size and any(groups.values()):
            for engines in sorted(groups):
                if groups[engines] and len(chosen) < args.sample_size:
                    chosen.append(groups[engines].pop(0))
    if len(chosen) != args.sample_size:
        raise ValueError('Insufficient nonduplicate validation questions')
    routing = {r['question_id']: engine_set(r) for r in chosen}
    if args.predicted_routing:
        sys.path.insert(0, str(ROOT / 'scripts/database_routing'))
        from embedding_classifier import LocalEncoder, DEFAULT_MODEL
        route_path = ROOT / 'outputs/database_routing/embedding_gpu'
        encoder = LocalEncoder(DEFAULT_MODEL, route_path, max_length=256, device='cuda', dtype='float16')
        summary = json.loads((route_path / 'summary.json').read_text())
        assert summary['encoder_settings'] == encoder.signature, 'Classifier signature mismatch'
        vectors = encoder.encode([r['question'] for r in chosen])
        with np.load(route_path / 'classifier.npz', allow_pickle=False) as classifier:
            predictions = classifier['classes'][(vectors @ classifier['coef'].T + classifier['intercept']).argmax(axis=1)]
        routing = {r['question_id']: str(label).split('|') for r, label in zip(chosen, predictions)}
    write_json(OUTPUT / 'leakage_audit.json', {'train_examples_verified': len(training_by_id),
               'index_examples_train_only': True, 'train_validation_id_overlap': 0,
               'normalized_train_question_overlap_in_selection': 0, 'previous_selection_overlap': 0,
               'random_seed': args.random_seed, 'reference_sql_sent': False,
               'selection_file': str(args.selection_file) if args.selection_file else None,
               'routing': 'training-only saved classifier predictions' if args.predicted_routing else 'oracle engine labels',
               'pipeline_version': PIPELINE_VERSION,
               'source_fingerprints': json.loads((DEFAULT_INDEX / 'manifest.json').read_text())['sources']})
    write_json(OUTPUT / 'selection.json', [{'question_id': r['question_id'], 'question': r['question'],
                                          'engines': routing[r['question_id']]} for r in chosen])
    index.encoder.encode([r['question'] for r in chosen])
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(index.encoder.model_path, local_files_only=True)
    builder = ContextBuilder(index)
    profiles = {}
    for row in chosen:
        raw = builder.assemble(row['question'], routing[row['question_id']], row['question_id'])
        fitted, _ = builder.fit(raw, SYSTEM)
        profiles[row['question_id']] = {'raw': context_profile(raw, SYSTEM, tokenizer),
                                       'fitted': context_profile(fitted, SYSTEM, tokenizer)}
        write_json(OUTPUT / f"prepared_{row['question_id']}.json", {'pipeline_version': PIPELINE_VERSION, 'context': fitted, 'context_profiles': profiles[row['question_id']]})
    write_json(OUTPUT / 'prepared_profiles.json', profiles)
    if args.prepare_only:
        print(json.dumps({'prepared_questions': len(chosen), 'directory': str(OUTPUT), 'external_calls': 0}))
        return
    client = DeepSeekClient(os.environ.get('DEEPSEEK_API_KEY'))
    planner = Planner(index, client)
    resolver = SourceResolver(index.tables)
    results = []
    for row in chosen:
        target = OUTPUT / f"question_{row['question_id']}.json"
        if target.exists():
            output = json.loads(target.read_text())
            if output.get('pipeline_version') != PIPELINE_VERSION:
                raise ValueError('Old pipeline outputs in target directory; use a new --output-directory')
            if output.get('context', {}).get('question') != row['question'] or output['result']['initial_databases'] != routing[row['question_id']]:
                raise ValueError('Saved output question or system routing differs; use a new output directory')
        else:
            call_start = len(client.calls)
            output = planner.run(row['question'], routing[row['question_id']], row['question_id'])
            output['execution']['transport_calls'] = client.calls[call_start:]
            output['pipeline_version'] = PIPELINE_VERSION
            write_json(target, output)
        expected = set()
        for db, query in [('db', 'query')] + [(f'db{i}', f'query{i}') for i in range(1, 4)]:
            if db in row:
                expected.update(resolver.parse(row[query], row[db])['table_ids'])
        actual = {t['table_id'] for t in output['result'].get('selected_tables', [])}
        expected_business = {database_id(index.tables[k]) for k in expected}
        routed_business = {database_id(index.tables[k]) for k in actual}
        table_context = output['context']
        measured_profiles = profiles[row['question_id']]
        measured_profiles = output['execution'].get('table_context_profiles', measured_profiles)
        results.append({'context_profiles': measured_profiles, 'question_id': row['question_id'], 'engines': engine_set(row),
                        'status': output['result']['status'], 'expected': sorted(expected), 'selected': sorted(actual),
                        'expected_business_databases': sorted(expected_business), 'selected_table_business_databases': sorted(routed_business),
                        'business_database_exact_match': expected_business == routed_business,
                        'business_database_recall': len(expected_business & routed_business) / len(expected_business) if expected_business else None,
                        'failed_stage': output['result'].get('failed_stage'),
                        'exact_table_match': expected == actual, 'table_recall': len(expected & actual) / len(expected) if expected else None,
                        'execution': output['execution']})
        write_json(OUTPUT / 'progress.json', results)
        print(json.dumps({k: results[-1][k] for k in ('question_id', 'status', 'exact_table_match')}, ensure_ascii=False), flush=True)
    calls = [c for r in results for c in r['execution']['transport_calls']]
    usage = Counter()
    for call in calls:
        usage.update({k: v for k, v in call.get('usage', {}).items() if isinstance(v, (int, float))})
    write_json(OUTPUT / 'report.json', {'scope': f'{args.sample_size} nonduplicate validation questions; fixed selection={bool(args.selection_file)}; reference answers used only for local scoring; predicted routing={args.predicted_routing}',
                                       'model': client.model, 'questions': len(results),
                                       'status_counts': dict(Counter(r['status'] for r in results)),
                                       'exact_table_match_rate': sum(r['exact_table_match'] for r in results) / args.sample_size,
                                       'pipeline_version': PIPELINE_VERSION,
                                       'business_database_exact_match_rate': sum(r['business_database_exact_match'] for r in results) / args.sample_size,
                                       'mean_business_database_recall': sum(r['business_database_recall'] or 0 for r in results) / args.sample_size,
                                       'mean_table_recall': sum(r['table_recall'] or 0 for r in results) / args.sample_size,
                                       'token_profile': summarize_tokens(results), 'transport_calls': len(calls), 'usage': dict(usage), 'cases': results})


if __name__ == '__main__':
    main()
