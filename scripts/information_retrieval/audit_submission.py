"""Offline format, provenance, budget and token audit for the official test run."""
from collections import Counter
import hashlib
import json
import numpy as np

from generate_submission import TRAINING_SOURCE, validate_answer
from index import ROOT, SourceResolver, write_json


def main():
    directory = ROOT / 'outputs/qa_test_deepseek_v4_pro_full_train'
    rows = json.loads((ROOT/'data/赛题8/QA_test.json').read_text())
    answers = json.loads((ROOT/'result.json').read_text())
    assert [r['question_id'] for r in rows] == [a['question_id'] for a in answers]
    assert len(answers) == len({a['question_id'] for a in answers}) == 400
    catalog = json.loads((ROOT/'data/preprocessed/schema_catalog.json').read_text())
    resolver = SourceResolver({t['table_id']:t for t in catalog['tables']})
    assert not any(validate_answer(answer,row,resolver) for row,answer in zip(rows,answers))
    train = {r['question_id']:r for r in json.loads((ROOT/TRAINING_SOURCE).read_text())}
    docs = [json.loads(line) for line in (directory/'index_full_train/documents.jsonl').read_text().splitlines()]
    examples = [d for d in docs if d['kind']=='example']
    assert {d['data']['question_id'] for d in examples} == set(train)
    for doc in examples:
        data=doc['data']; source=train[data['question_id']]
        assert source['question']==data['question']
        assert all(source[s['step']]==s['query'] for s in data['steps'])
    outputs=[json.loads((directory/f"question_{r['question_id']}.json").read_text()) for r in rows]
    assert all(output['answer']==answer for output,answer in zip(outputs,answers))
    histories=[json.loads(f.read_text()) for f in (directory/'retry_history').glob('*.json')]
    calls=[c for output in outputs+histories for c in output['calls']]
    models=Counter(c.get('response_model') for c in calls if c.get('success'))
    assert set(models)=={'deepseek-v4-pro'}
    final_calls=[c for output in outputs for c in output['calls'] if c.get('success')]
    assert all(c['usage']['prompt_tokens']+c['output_token_limit']<=24000 for c in final_calls)
    tokens=[sum(c.get('usage',{}).get('total_tokens',0) for c in o['calls']) for o in outputs]
    audit={'questions':len(answers),'ids_unique':True,'ids_and_order_equal_test':True,
           'format_and_static_errors':{},'single_system':sum('db' in a for a in answers),
           'multiple_system':sum('db1' in a for a in answers),
           'engine_combinations':dict(Counter('|'.join([a['db']] if 'db' in a else [a[f'db{i}'] for i in range(1,4) if f'db{i}' in a]) for a in answers)),
           'actual_response_models':dict(models),'training_source':TRAINING_SOURCE,
           'training_cases_verified':len(examples),
           'routing_training_size':json.loads((directory/'routing_full_train/summary.json').read_text())['training_size'],
           'result_sha256':hashlib.sha256((ROOT/'result.json').read_bytes()).hexdigest(),
           'result_bytes':(ROOT/'result.json').stat().st_size,'execution_accuracy':None,
           'final_result_calls_within_24000_actual_input_plus_output_reserve':True,
           'max_final_call_input_tokens':max(c['usage']['prompt_tokens'] for c in final_calls),
           'token_per_final_question_including_its_repairs':{'mean':float(np.mean(tokens)),'p50':float(np.percentile(tokens,50)),'p95':float(np.percentile(tokens,95)),'max':max(tokens)},
           'superseded_over_budget_question_ids':[2990,3684,5028],
           'historical_usage_note':'Superseded outputs and failed attempts count toward billing; none replace final audited answers.'}
    write_json(directory/'submission_audit.json',audit)
    report=json.loads((directory/'report.json').read_text())
    old=json.loads((ROOT/'outputs/qa_test_deepseek_v4_pro/report.json').read_text())
    billing={'full_train_final_batch':{'calls':report['transport_calls'],'usage':report['usage']},
             'prior_split_batch_excluded_from_result':{'calls':old['transport_calls'],'usage':old['usage']},
             'all_recorded_calls':report['transport_calls']+old['transport_calls'],
             'all_recorded_total_tokens':report['usage']['total_tokens']+old['usage']['total_tokens']}
    write_json(directory/'billing_summary.json',billing)
    print(json.dumps({'audit':audit,'billing':billing},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
