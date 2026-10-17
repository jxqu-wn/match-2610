"""Select 6k generation candidates from tuning metrics and report stage effects."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def eligible(row, baseline):
    return all(row['tuning_groups'][g][k] >= b[k]
               for g, b in baseline['tuning_groups'].items()
               for k in ('complete_db', 'complete_table'))


def select(base):
    out = base / 'inference'
    report = read(out / 'comparison.json')
    expected = {p['name'] for grid in (base / 'public/grid.json', base / 'stage_b_grid.json', base / 'namespace_grid.json')
                for p in read(grid)}
    if set(report) != expected:
        raise ValueError(f'Incomplete experiment: expected {len(expected)}, found {len(report)}')
    candidates = [(n, r) for n, r in report.items() if eligible(r, report['frozen_original'])]
    max_gap = max(r['reviewed_gap_hits'] for _, r in candidates)
    high = [(n, r) for n, r in candidates if r['reviewed_gap_hits'] == max_gap]
    best_k = max(r['tuning']['positive_knowledge_hits'] for _, r in high)
    high = [(n, r) for n, r in high if r['tuning']['positive_knowledge_hits'] >= best_k - 1]

    def key(item):
        n, r = item
        t = r['tuning']
        return (-t['complete_table'], -t['complete_db'], -t['positive_knowledge_hits'], t['tokens_p95'],
                bool(r['parameters'].get('namespace_quota')), n)

    def stable_choice(items, seed_name):
        first = min(items, key=key)[1]['tuning']
        peers = [(n, r) for n, r in items if all(r['tuning'][k] == first[k]
                 for k in ('complete_table', 'complete_db', 'positive_knowledge_hits'))]
        minimum = min(r['tuning']['tokens_p95'] for _, r in peers)
        peers = [(n, r) for n, r in peers if r['tuning']['tokens_p95'] <= minimum + 64]
        seed = report[seed_name]['parameters']

        def stable_key(item):
            n, r = item
            changes = sum(v != seed.get(k) for k, v in r['parameters'].items() if k != 'name')
            return changes, r['tuning']['tokens_p95'], n

        return min(peers, key=stable_key)[0]

    high_name = stable_choice(high, 'quota_t8_k18_e0')
    lean = [(n, r) for n, r in candidates if r['reviewed_gap_hits'] >= max_gap - 1
            and r['tuning']['positive_knowledge_hits'] >= best_k - 1]
    lean_name = stable_choice(lean, 'quota_t8_k4_e0')
    values = [(n, r) for n, r in candidates if r['parameters']['value_samples'] > 0]
    values_name = min(values, key=key)[0] if values else None
    roles = {'baseline': 'frozen_original', 'reviewed_knowledge': high_name, 'schema_coverage': lean_name,
             'original_value_samples': values_name}
    # Compare semantic payloads, excluding retrieval/debug-only provenance.
    split = read(base / 'public/partition.json')
    ids = set(split['generation_ids']) | {171, 395, 441, 935, 1038, 1050, 2125, 2462, 2487, 2908, 3012}
    chosen, fingerprints, dedup = [], {}, []
    for role, name in roles.items():
        if name is None or name in chosen:
            continue
        payload = []
        for line in (out / 'runs' / name / 'prompts.jsonl').open():
            row = json.loads(line)
            if row['question_id'] not in ids:
                continue
            c = row['context']
            payload.append([row['question_id'], c['initial_databases'],
                            [[t['table_id'], t.get('source_values')] for t in c['candidate_tables']],
                            [k['knowledge_id'] for k in c['knowledge']], [e['source_id'] for e in c['examples']]])
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if digest in fingerprints:
            dedup.append({'role': role, 'configuration': name, 'same_evidence_as': fingerprints[digest]})
            continue
        fingerprints[digest] = name
        chosen.append(name)
    selection = {'configurations': chosen, 'roles': roles, 'selection_partition': 'tuning_only',
                 'heldback_used_for_selection': False, 'regression_generation_question_ids': [171, 395, 1038, 3012],
                 'policy': 'knowledge branch maximizes reviewed-gap hits; schema branch allows one missing partial positive; both then maximize complete reference-table coverage, complete DB, positive hits; P95 differences within64 tokens are ties, prefer fewer changes from the matched seed then lower P95',
                 'deduplicated_evidence': dedup,
                 'limits': 'knowledge IDs are partial labels, not complete necessary-fact coverage; development results only'}
    path = out / 'selection.json'
    if (out / 'sql_experiment_config.json').exists() and read(path) != selection:
        raise ValueError('SQL inputs already frozen; do not overwrite selection')
    write(path, selection)
    write(base / 'recommended_parameters.json', {role: report[name]['parameters'] for role, name in roles.items() if name})
    print(json.dumps(selection, ensure_ascii=False))


def effects(base):
    report = read(base / 'inference/comparison.json')
    result = []
    for name, row in report.items():
        if name.startswith('lean_stage_') or name.startswith('namespace_lean_'):
            control = 'quota_t8_k4_e0'
        elif name.startswith('stage_example_'):
            control = 'example_branch_control'
        elif name.startswith(('stage_', 'support_', 'routing_', 'namespace_knowledge_')):
            control = 'quota_t8_k18_e0'
        else:
            continue
        baseline = report[control]
        result.append({'configuration': name, 'matched_control': control,
                       'parameter_changes': {k: v for k, v in row['parameters'].items()
                                             if k != 'name' and baseline['parameters'].get(k) != v},
                       'tuning_delta': {k: row['tuning'][k] - baseline['tuning'][k]
                                        for k in ('complete_db', 'complete_table', 'positive_knowledge_hits', 'tokens_p95')},
                       'reviewed_gap_delta': row['reviewed_gap_hits'] - baseline['reviewed_gap_hits']})
    write(base / 'stage_effects.json', result)
    print(json.dumps({'stage_comparisons': len(result)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('select', 'effects'))
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    {'select': select, 'effects': effects}[args.command](args.root)
