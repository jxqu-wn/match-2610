"""Offline audit of frozen contexts; references never leave local evaluation.

Replay uses cached query embeddings only and fails if any are missing.
No model inference, API requests, index writes or retrieval tuning.
"""
import argparse
import json, hashlib
from pathlib import Path
import numpy as np
from index import RetrievalIndex, ROOT, DEFAULT_INDEX
from context import ContextBuilder
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', type=Path, default=ROOT/'outputs/information_retrieval/live50')
args = parser.parse_args()
p=args.directory
m=json.loads((DEFAULT_INDEX/'manifest.json').read_text())
sig=m['encoder']; digest=hashlib.sha256(json.dumps(sig,sort_keys=True).encode()).hexdigest()[:16]
class CachedEncoder:
    signature=sig
    model_path=Path(sig['model_path'])
    def __init__(self):
        with np.load(ROOT/f'outputs/information_retrieval/embedding_cache/embeddings_{digest}.npz',allow_pickle=False) as z:
            self.cache=dict(zip(z['texts'].tolist(),z['vectors']))
    def encode(self,texts):
        absent=[t for t in texts if t not in self.cache]
        if absent: raise ValueError('Missing frozen embeddings: '+repr(absent))
        return np.stack([self.cache[t] for t in texts])
encoder=CachedEncoder(); index=RetrievalIndex.load(encoder=encoder);builder=ContextBuilder(index)
tok=builder.tokenizer
count=lambda x:len(tok.encode(json.dumps(x,ensure_ascii=False)))
report=json.loads((p/'report.json').read_text()); reviews={x['question_id']:x for x in json.loads((p/'semantic_review.json').read_text())['cases']};packets={x['question_id']:x for x in json.loads((p/'local_review_packets.json').read_text())}
rows=[]
for case in report['cases']:
    qid=case['question_id'];o=json.loads((p/f'question_{qid}.json').read_text());c=o['context'];expected=set(case['expected']);tables=c['candidate_tables'];provided={t['table_id'] for t in tables};q=c['question'];eng=c['initial_databases']
    ranks={};full=[]
    for e in eng:
        hits=index.search(q,'schema',[e],len(index.tables));full+=hits
        ranks.update({h['table_ids'][0]:dict(fused_rank=n+1,**h) for n,h in enumerate(hits)})
    init=builder.retrieve(q,eng);initkeys={h['table_ids'][0] for h in init}
    verified=0
    for t in tables:
        ev=t['retrieval_evidence'];rr=ranks.get(t['table_id'],{})
        if 'score' in ev:
            assert abs(rr['score']-ev['score'])<1e-9,(qid,t['table_id'])
            assert abs(rr['semantic_similarity']-ev['semantic_similarity'])<1e-6
            verified+=1
    expecteddb={(index.tables[k]['engine'],index.tables[k]['database']) for k in expected}
    outside=lambda keys:bool(keys) and not any((index.tables[k]['engine'],index.tables[k]['database']) in expecteddb for k in keys)
    schema_total=sum(count(t) for t in tables);schema_extra=sum(count(t) for t in tables if t['table_id'] not in expected);schema_cross=sum(count(t) for t in tables if outside([t['table_id']]))
    field_total=sum(len(t['columns']) for t in tables);field_needed=sum(len(packets[qid]['required_fields'].get(t['table_id'],[])) for t in tables)
    for t in tables:
        assert {x[0] for x in t['columns']} == {x['name'] for x in index.tables[t['table_id']]['columns']}
        assert set(packets[qid]['required_fields'].get(t['table_id'], [])) <= {x[0] for x in t['columns']}
    sections={name:sum(count(d) for d in c.get(name,[])) for name in ['candidate_tables','knowledge','examples','relations','source_comparisons']}
    extra_docs={};doc_details={}
    for name in ['knowledge','examples']:
        docs=c.get(name,[]);ids=[d['source_id'] for d in docs]
        ds=[index.by_id[sid] for sid in ids]
        extra_docs[name]={'total':len(docs),'no_reference_table_overlap':sum(not (set(d['table_ids'])&expected) for d in ds),'cross_business_database':sum(outside(d['table_ids']) for d in ds),'tokens':sum(count(d) for d in docs),'no_overlap_tokens':sum(count(d) for d,src in zip(docs,ds) if not(set(src['table_ids'])&expected)),'cross_database_tokens':sum(count(d) for d,src in zip(docs,ds) if outside(src['table_ids']))}
        doc_details[name]=[{'source_id':d['source_id'],'table_ids':src['table_ids'],'no_reference_table_overlap':not bool(set(src['table_ids'])&expected),'cross_business_database':outside(src['table_ids'])} for d,src in zip(docs,ds)]
    rows.append({'question_id':qid,'question':q,'expected':sorted(expected),'provided':sorted(provided),'missing':sorted(expected-provided),'complete':expected<=provided,'exact':case['exact_table_match'],'semantic_verdict':reviews[qid]['semantic_verdict'],'table_count':len(tables),'reference_table_count':len(expected&provided),'extra_table_count':len(provided-expected),'cross_database_table_count':sum(outside([k]) for k in provided),'schema_tokens':schema_total,'extra_schema_tokens':schema_extra,'cross_database_schema_tokens':schema_cross,'extra_schema_token_fraction':schema_extra/schema_total,'field_count':field_total,'reference_explicit_field_count':field_needed,'section_tokens':sections,'documents':extra_docs,'document_details':doc_details,'reference_ranks':{k:ranks.get(k) for k in sorted(expected)},'initial_retrieve_ids':sorted(initkeys),'lost_after_case_promotion':sorted((expected&initkeys)-provided),'table_details':[{'table_id':t['table_id'],'is_reference':t['table_id'] in expected,'context_position':n+1,'retrieval':t['retrieval_evidence'],'raw_rank':ranks.get(t['table_id'])} for n,t in enumerate(tables)],'stored_ranking_verified':verified,'omitted_evidence':c['omitted_evidence']})
def agg(rs):
    total=sum(r['table_count'] for r in rs);st=sum(r['schema_tokens'] for r in rs)
    result={'questions':len(rs),'table_count':total,'reference_table_count':sum(r['reference_table_count'] for r in rs),'extra_table_count':sum(r['extra_table_count'] for r in rs),'extra_table_fraction':sum(r['extra_table_count'] for r in rs)/total,'cross_database_table_fraction':sum(r['cross_database_table_count'] for r in rs)/total,'schema_tokens':st,'extra_schema_token_fraction':sum(r['extra_schema_tokens'] for r in rs)/st,'cross_database_schema_token_fraction':sum(r['cross_database_schema_tokens'] for r in rs)/st,'mean_extra_schema_token_fraction':float(np.mean([r['extra_schema_token_fraction'] for r in rs])),'field_count':sum(r['field_count'] for r in rs),'reference_explicit_field_count':sum(r['reference_explicit_field_count'] for r in rs),'section_tokens':{k:sum(r['section_tokens'][k] for r in rs) for k in rs[0]['section_tokens']},'documents':{name:{k:sum(r['documents'][name][k] for r in rs) for k in rs[0]['documents'][name]} for name in ['knowledge','examples']}}
    return result
complete=[r for r in rows if r['complete']]
refs=[(r,rank) for r in rows for rank in r['reference_ranks'].values() if rank]
summaries={name:agg(rs) for name,rs in [('all',rows),('complete',complete),('complete_consistent',[r for r in complete if r['semantic_verdict']=='consistent']),('complete_nonpass',[r for r in complete if r['semantic_verdict']!='consistent']),('exact_tables',[r for r in rows if r['exact']]),('wrong_tables',[r for r in rows if not r['exact']])]}
for exact in (True, False):
    summaries['complete_exact' if exact else 'complete_wrong_tables'] = agg([r for r in complete if r['exact'] == exact])
ranksummary={'reference_occurrences':len(refs),'by_cutoff':{str(n):{'raw_rank_count':sum(rank['fused_rank']<=n for r,rank in refs),'all_reference_raw_top_n_questions':sum(all(rank and rank['fused_rank']<=n for rank in r['reference_ranks'].values()) for r in rows)} for n in [1,3,6,8,12]},'present_due_to_reason':{reason:sum(t['is_reference'] and t['retrieval'].get('reason','direct')==reason for r in rows for t in r['table_details']) for reason in ['direct','one_hop_declared_relation','first_relevant_training_case']},'mean_raw_rank':float(np.mean([rank['fused_rank'] for r,rank in refs]))}
audit={'scope':'Frozen live50 outputs; no model calls; evaluation reference used only locally; raw rank replay uses frozen index+cached embeddings and verifies stored scores','metric_warning':'Reference-unused tables/tokens are distractor proxies, not proven irrelevant. Column count uses explicit SQL column refs and excludes star expansion. Local Qwen tokenizer, not actual DeepSeek tokens. All ranks within predicted engine.','summaries':summaries,'rank_summary':ranksummary,'cases':rows}
(p/'retrieval_noise_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'summaries':summaries,'ranks':ranksummary,'missing':[{k:r[k] for k in ['question_id','missing','reference_ranks','lost_after_case_promotion']} for r in rows if not r['complete']]},ensure_ascii=False,indent=2))
