"""Check every saved provider usage and all generation/repair input estimates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def audit(output):
    config = json.loads((output / 'sql_experiment_config.json').read_text())
    if config.get('input_limit') != 6000:
        raise ValueError('Not a frozen 6000-token experiment')
    selection = config['selection']
    done = json.loads((output / 'generation_complete.json').read_text())
    jobs = len(selection['configurations']) * len(selection['generation_question_ids'])
    if done['jobs'] != jobs:
        raise ValueError('Generation job count differs from frozen configuration')
    rows, failures = [], []
    estimates = []
    for name in selection['configurations']:
        for qid in selection['generation_question_ids']:
            folder = output / 'generation' / name
            path = folder / f'question_{qid}.json'
            if not path.exists():
                path = folder / f'failed_{qid}.json'
            record = json.loads(path.read_text())
            if 'answer' not in record:
                failures.append({'configuration': name, 'question_id': qid})
            for t in record.get('trace', []):
                estimates.append(t['estimated_input_tokens'])
            for i, call in enumerate(record.get('calls', []), 1):
                usage = call.get('usage') or {}
                rows.append({'configuration': name, 'question_id': qid, 'call': i,
                             'purpose': call.get('purpose'), 'success': call.get('success'),
                             'prompt_tokens': usage.get('prompt_tokens'),
                             'completion_tokens': usage.get('completion_tokens')})
    missing = [r for r in rows if r['success'] and not isinstance(r['prompt_tokens'], int)]
    excessive = [r for r in rows if isinstance(r['prompt_tokens'], int) and r['prompt_tokens'] > 6000]
    summary = {'jobs': jobs, 'calls': len(rows), 'generation_failures': failures,
               'max_prompt_tokens': max((r['prompt_tokens'] for r in rows if isinstance(r['prompt_tokens'], int)), default=None),
               'max_local_estimated_input_tokens': max(estimates, default=None),
               'over_limit_calls': len(excessive), 'missing_usage_calls': len(missing),
               'violations': excessive, 'missing_usage': missing, 'calls_detail': rows,
               'scope': 'input tokens only, system/user/all repair history; output excluded'}
    (output / 'provider_token_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'calls_detail'}, ensure_ascii=False))
    if excessive or missing or any(t > 6000 for t in estimates):
        raise SystemExit('Input token verification failed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    audit(p.parse_args().output)
