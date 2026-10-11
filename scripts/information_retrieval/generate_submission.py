"""Generate a resumable submission using test questions and training-only retrieval."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import math

import numpy as np
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope
from index import ROOT, DEFAULT_INDEX, RetrievalIndex, SourceResolver, KeywordIndex, make_encoder, write_json
from context import ContextBuilder
from planner import DeepSeekClient

MODEL = 'deepseek-v4-pro'
TRAINING_SOURCE = 'data/赛题8/QA_train.json'
ENGINES = {'MYSQL', 'POSTGRESQL', 'SQLite', 'Elasticsearch'}
SYSTEM = '''根据提供的问题、schema、原始知识和训练案例生成最终可执行查询。仅返回JSON对象：
{"status":"complete","answer":{"question_id":原ID,"db":"数据库系统","query":"查询字符串"},"requirements":[{"requirement":"题目的一项要求","tables":["table_id"],"columns":["字段"]}],"assumptions":[]}。
跨系统查询answer使用db1/query1、db2/query2，必要时db3/query3；后续查询以result代替前一步执行结果。单系统跨业务库仍使用db/query。
跨系统完整answer格式示例：{"question_id":原ID,"db1":"MYSQL","query1":"真实的第一步SELECT语句","db2":"POSTGRESQL","query2":"真实的第二步SELECT语句，其中引用result"}。禁止MYSQL/POSTGRESQL之类组合db值，禁止以db1/query1等占位文字代替真实查询。
SQL数据库系统名仅MYSQL、POSTGRESQL、SQLite；Elasticsearch的query为JSON DSL字符串。SQL使用schema中的真实库表与字段，按对应方言引用特殊标识符；仅生成读取查询，不执行查询。SQLite表使用业务库.表名限定，MySQL同理；PostgreSQL使用schema.表名。
逐项覆盖输出、过滤、日期、分组、统计对象、去重及引用方向，检查统计粒度、必要连接、分母和排序。每张最终表必须承担需求或必要关联任务，不能因存在外键就添加连接。不要遗漏仅用于条件的字段。训练案例不是保证正确的答案，先检查问题差异；不得编造schema字段。优先采用已有明确知识，冲突或问题歧义在assumptions中如实记录，仍给出最有依据的查询，不把明确未满足的要求当成假设。
如果缺少必要schema，不猜表字段，返回{"status":"need_more_evidence","search_queries":["具体检索词"],"engines":["系统名"],"reason":"缺少的需求"}。分类和候选排序不是业务正确性证明。不得输出Markdown。'''


def validate_answer(answer, row, resolver):
    errors = []
    if not isinstance(answer, dict) or answer.get('question_id') != row['question_id']:
        return ['answer/question_id invalid']
    if 'db' in answer:
        pairs = [('db', 'query')]
    else:
        pairs = [(f'db{i}', f'query{i}') for i in range(1, 4) if f'db{i}' in answer]
        if len(pairs) < 2 or pairs != [(f'db{i}', f'query{i}') for i in range(1, len(pairs)+1)]:
            errors.append('Multiple steps must be contiguous and contain at least two steps')
    allowed = {'question_id'} | {key for pair in pairs for key in pair}
    if set(answer) != allowed:
        errors.append('Unexpected or missing submission keys')
    for dbkey, querykey in pairs:
        engine, query = answer.get(dbkey), answer.get(querykey)
        if engine not in ENGINES or not isinstance(query, str) or not query.strip():
            errors.append(f'Invalid {dbkey}/{querykey}'); continue
        try:
            if engine == 'Elasticsearch':
                if not isinstance(json.loads(query), dict):
                    errors.append('DSL must be an object')
            else:
                trees = sqlglot.parse(query, read={'MYSQL':'mysql','SQLite':'sqlite','POSTGRESQL':'postgres'}[engine])
                if len(trees) != 1 or not isinstance(trees[0], exp.Query):
                    errors.append('Expected exactly one read query'); continue
                if any(isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Into)) for node in trees[0].walk()):
                    errors.append('Non-read SQL forbidden')
                parsed = resolver.parse(query, engine)
                # result is an official inter-system result placeholder.
                unknown = [x for x in parsed.get('unresolved_tables', []) if x.lower() != 'result']
                if parsed['parse_status'] == 'parse_error' or unknown:
                    errors.append('SQL unresolved: ' + str(unknown or parsed.get('parse_error')))
                for scope in traverse_scope(trees[0]):
                    aliases = {}
                    for alias, table in scope.sources.items():
                        if isinstance(table, exp.Table):
                            key = resolver.resolve(engine, table)
                            if key:
                                aliases[alias.lower()] = {c['name'].lower() for c in resolver.tables[key]['columns']}
                    for column in scope.columns:
                        if column.table.lower() in aliases and column.name != '*' and column.name.lower() not in aliases[column.table.lower()]:
                            errors.append('Unknown qualified column: ' + column.sql())
        except Exception as error:
            errors.append(f'{querykey}: {type(error).__name__}: {str(error)[:200]}')
    if len(pairs) > 1 and any(not re.search(r'\bresult\b', answer.get(q, ''), re.I) for _, q in pairs[1:]):
        errors.append('Later steps must use result')
    return errors


def prepare(rows, directory):
    sys.path.insert(0, str(ROOT / 'scripts/database_routing'))
    from embedding_classifier import LocalEncoder, DEFAULT_MODEL
    from sklearn.linear_model import LogisticRegression
    from experiment import label
    train = {r['question_id']:r for r in json.loads((ROOT/TRAINING_SOURCE).read_text())}
    route_path = directory / 'routing_full_train'
    route_path.mkdir(parents=True, exist_ok=True)
    import shutil
    for cached in (ROOT/'outputs/database_routing/embedding_gpu').glob('embeddings_*.npz'):
        if not (route_path/cached.name).exists():
            shutil.copy2(cached, route_path/cached.name)
    encoder = LocalEncoder(DEFAULT_MODEL, route_path, max_length=256, device='cuda', dtype='float16')
    if not (route_path/'classifier.npz').exists():
        train_vectors = encoder.encode([r['question'] for r in train.values()])
        classifier = LogisticRegression(C=10.0, max_iter=2000, random_state=42)
        classifier.fit(train_vectors, np.array([label(r) for r in train.values()]))
        np.savez(route_path/'classifier.npz',coef=classifier.coef_,intercept=classifier.intercept_,classes=classifier.classes_)
        write_json(route_path/'summary.json',{'training_source':TRAINING_SOURCE,'training_size':len(train),'encoder_settings':encoder.signature,'method':'logistic_C10.0; fixed prior training-dev hyperparameter; refit on full QA_train'})
    assert json.loads((route_path/'summary.json').read_text())['encoder_settings'] == encoder.signature
    vectors = encoder.encode([r['question'] for r in rows])
    with np.load(route_path/'classifier.npz', allow_pickle=False) as saved:
        labels = saved['classes'][(vectors @ saved['coef'].T + saved['intercept']).argmax(axis=1)]
    del encoder
    import gc, torch
    gc.collect(); torch.cuda.empty_cache()
    index_path = directory / 'index_full_train'
    retrieval_encoder = make_encoder(device='cuda', dtype='float16')
    if (index_path/'manifest.json').exists():
        index = RetrievalIndex.load(index_path, retrieval_encoder, training_source=TRAINING_SOURCE)
    else:
        index = RetrievalIndex.build(index_path, retrieval_encoder, training_source=TRAINING_SOURCE)
    for doc in index.documents:
        if doc['kind'] == 'example':
            data = doc['data']; source = train.get(data['question_id'])
            assert source and data['question'] == source['question']
            assert all(source[s['step']] == s['query'] for s in data['steps'])
        if doc['kind'] == 'schema':
            assert all(x['question_id'] in train for x in doc['data'].get('training_examples', []))
    builder = ContextBuilder(index)
    index.encoder.encode([r['question'] for r in rows])
    for row, label in zip(rows, labels):
        target = directory/f"prepared_{row['question_id']}.json"
        if target.exists(): continue
        context = builder.assemble(row['question'], str(label).split('|'), row['question_id'])
        context, _ = builder.fit(context, SYSTEM)
        # Precompute explicit missing-evidence expansion locally before concurrent API workers.
        write_json(target, {'question':row, 'context':context})
        print(json.dumps({'prepared':row['question_id']}), flush=True)
    indexed_ids = {d['data']['question_id'] for d in index.documents if d['kind']=='example'}
    assert indexed_ids == set(train)
    write_json(directory/'leakage_audit.json', {'training_source':TRAINING_SOURCE,'index_examples_full_training_only':True, 'train_examples':len(train),'indexed_examples':len(indexed_ids), 'test_answers_available':False, 'test_questions':len(rows), 'validation_split_policy':'Only prior validation experiments use the split. Official test uses all QA_train.'})


def worker(row, directory, tables):
    target = directory/f"question_{row['question_id']}.json"
    resolver = SourceResolver(tables)
    if target.exists():
        old = json.loads(target.read_text())
        if old.get('model') == MODEL and old.get('question') == row and not validate_answer(old.get('answer'), row, resolver):
            return old
    prepared = json.loads((directory/f"prepared_{row['question_id']}.json").read_text())
    client = DeepSeekClient(os.environ.get('DEEPSEEK_API_KEY'), MODEL)
    context = prepared['context']
    messages = [{'role':'system','content':SYSTEM}, {'role':'user','content':json.dumps(context,ensure_ascii=False)}]
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(ROOT/'models/Qwen3-Embedding-0.6B', local_files_only=True)
    def estimated_input(items):
        return math.ceil(1.2 * sum(len(tokenizer.encode(m['content'])) + 8 for m in items)) + 256
    supplied = {t['table_id'] for t in context['candidate_tables']}
    def add_schemas(schema, query):
        keyword = KeywordIndex([json.dumps(t,ensure_ascii=False) for t in schema])
        ranked = sorted(range(len(schema)),key=lambda i:(-keyword.score(query,i),schema[i]['table_id']))
        chosen = []
        instruction = '以下是按缺口文本检索的真实schema。严格使用其中字段；跨系统使用db1/query1、db2/query2和result。请生成最终answer。'
        for i in ranked:
            if schema[i]['table_id'] in supplied: continue
            trial = {'role':'user','content':json.dumps({'additional_schemas':chosen+[schema[i]],'instruction':instruction},ensure_ascii=False)}
            if estimated_input(messages+[trial]) <= 20000:
                chosen.append(schema[i])
            if len(chosen) >= 12: break
        messages.append({'role':'user','content':json.dumps({'additional_schemas':chosen,'instruction':instruction},ensure_ascii=False)})
        supplied.update(t['table_id'] for t in chosen)
    failed = directory/f"failed_{row['question_id']}.json"
    if failed.exists():
        previous = json.loads(failed.read_text())
        write_json(directory/'retry_history'/f"question_{row['question_id']}_{time.time_ns()}.json", previous)
        errors = [e for item in previous.get('trace',[]) for e in item.get('validation_errors',[])]
        names = {e.rsplit('.',1)[-1] for e in errors if e.startswith('Unknown qualified column:')}
        for item in previous.get('trace', []):
            try:
                prior = json.loads(item['raw'])
                names.update(c.rsplit('.',1)[-1] for requirement in prior.get('requirements', [])
                             for c in requirement.get('columns', []) if isinstance(c,str))
            except (ValueError, TypeError):
                pass
        witnesses = [{'table_id':key,'columns':[c['name'] for c in t['columns']]} for key,t in tables.items()
                     if sum(c['name'] in names for c in t['columns']) >= (2 if len(names)>1 else 1)]
        messages.append({'role':'user','content':json.dumps({'previous_validation_errors':sorted(set(errors)),
                            'exact_column_matches_in_catalog':witnesses,
                            'instruction':'此前尝试因真实schema校验失败，不能复用无效语句。字段不存在不是可接受的假设。table_id前缀是该表的真实数据库系统，不能迁移表到另一系统。需求字段分属不同系统时，必须使用db1/query1、db2/query2和result分步查询。请按实际schema重新选择库表；如需完整描述返回need_more_evidence。'},ensure_ascii=False)})
    trace = []
    try:
        for attempt in range(4):
            estimate = estimated_input(messages)
            if estimate > 21000:
                raise ValueError('Input estimate exceeds 21000; preserve schemas and fail rather than silently truncate')
            raw = client.complete(messages, 3000, 'generation' if attempt == 0 else 'repair_or_expansion')
            trace.append({'attempt':attempt+1,'raw':raw,'estimated_input_tokens':estimate})
            try:
                value = json.loads(raw)
                if value.get('status') == 'need_more_evidence':
                    # Exact schema fallback: all schemas in requested systems, no test labels or business rules.
                    engines = value.get('engines') or context['searched_databases']
                    if not isinstance(engines,list) or not set(engines)<=ENGINES: engines=context['searched_databases']
                    fallback = json.loads((directory/'schema_fallback.json').read_text())
                    schema = [t for t in fallback if t['engine'] in engines]
                    messages.append({'role':'assistant','content':raw})
                    add_schemas(schema, row['question']+' '+json.dumps(value,ensure_ascii=False))
                    continue
                answer = value.get('answer')
                if isinstance(answer, dict):
                    for dbkey, querykey in [('db','query')] + [(f'db{i}',f'query{i}') for i in range(1,4)]:
                        if answer.get(dbkey) == 'Elasticsearch' and isinstance(answer.get(querykey), dict):
                            answer[querykey] = json.dumps(answer[querykey], ensure_ascii=False, separators=(',', ':'))
                errors = validate_answer(answer, row, resolver)
            except Exception as error:
                errors = [f'Invalid output: {type(error).__name__}: {str(error)[:200]}']
            if not errors:
                output={'model':MODEL,'question':row,'answer':answer,'analysis':value,'trace':trace,'calls':client.calls}
                write_json(target,output)
                if failed.exists(): failed.unlink()
                return output
            trace[-1]['validation_errors'] = errors
            if any('unresolved' in e or 'Invalid db/' in e or 'Unknown qualified column' in e for e in errors):
                fallback = json.loads((directory/'schema_fallback.json').read_text())
                add_schemas(fallback, row['question']+' '+json.dumps(errors,ensure_ascii=False))
            messages.extend([{'role':'assistant','content':raw},{'role':'user','content':json.dumps({'validation_errors':errors,'instruction':'修正错误并返回完整最终对象。若Elasticsearch query字符串内JSON不合法，请将query改为JSON对象而非转义字符串，程序会自动序列化成提交字符串。不要重复之前无效的query。'},ensure_ascii=False)}])
        raise ValueError('No valid submission answer after four calls')
    except Exception as error:
        output={'model':MODEL,'question':row,'error':str(error),'trace':trace,'calls':client.calls}
        write_json(directory/f"failed_{row['question_id']}.json",output)
        return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--directory',type=Path,default=ROOT/'outputs/qa_test_deepseek_v4_pro_full_train')
    args=parser.parse_args(); directory=args.directory; directory.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/赛题8/QA_test.json'
    rows=json.loads(source.read_text())
    assert len({r['question_id'] for r in rows})==len(rows)
    assert all(set(r)=={'question_id','question'} for r in rows)
    write_json(directory/'run_config.json', {'model':MODEL,'training_source':TRAINING_SOURCE,'training_sha256':hashlib.sha256((ROOT/TRAINING_SOURCE).read_bytes()).hexdigest(),'input':str(source),'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'questions':len(rows),'workers':args.workers,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    if not all((directory/f"prepared_{r['question_id']}.json").exists() for r in rows): prepare(rows,directory)
    catalog=json.loads((ROOT/'data/preprocessed/schema_catalog.json').read_text())
    tables={t['table_id']:t for t in catalog['tables']}
    # Full fallback contains schema only, never validation or test answers.
    fallback=[{'table_id':key,'engine':t['engine'],'description':t['description'],'columns':[[c['name'],c['data_type'],c['description']] for c in t['columns']],'primary_key':t['primary_key'],'foreign_keys':t['foreign_keys']} for key,t in tables.items()]
    write_json(directory/'schema_fallback.json',fallback)
    if args.prepare_only:return
    if not os.environ.get('DEEPSEEK_API_KEY'): parser.error('DEEPSEEK_API_KEY is required')
    results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(worker,r,directory,tables):r['question_id'] for r in rows}
        for future in as_completed(futures):
            output=future.result();results.append(output)
            print(json.dumps({'finished':len(results),'question_id':output['question']['question_id'],'success':'answer' in output},ensure_ascii=False),flush=True)
            write_json(directory/'progress.json', {'finished':len(results),'success':sum('answer' in x for x in results),'failed':[x['question']['question_id'] for x in results if 'answer' not in x]})
    usage=Counter()
    histories=[json.loads(f.read_text()) for f in (directory/'retry_history').glob('*.json')]
    for output in results + histories:
        for call in output.get('calls',[]): usage.update({k:v for k,v in call.get('usage',{}).items() if isinstance(v,(float,int))})
    write_json(directory/'report.json',{'model':MODEL,'training_source':TRAINING_SOURCE,'questions':len(rows),'completed':sum('answer' in r for r in results),'usage':dict(usage),'transport_calls':sum(len(r.get('calls',[])) for r in results+histories),'retry_history_records':len(histories),'execution_accuracy':None})
    if any('answer' not in x for x in results):raise SystemExit('Incomplete; successful answers saved. Rerun to retry failed questions.')
    by_id={x['question']['question_id']:x['answer'] for x in results}
    submission=[by_id[r['question_id']] for r in rows]
    write_json(ROOT/'result.json',submission)
    print(json.dumps({'result':str(ROOT/'result.json'),'questions':len(submission),'usage':dict(usage)},ensure_ascii=False))


if __name__=='__main__':main()
