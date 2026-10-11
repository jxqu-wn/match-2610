"""Bounded planning protocol. No business query execution."""
import json
import time
import urllib.error
import urllib.request

from context import ContextBuilder, token_upper_bound
from business_routing import BusinessRouter, database_id, PIPELINE_VERSION

SYSTEM = '''你负责选择库表，不生成或执行业务SQL。仅返回JSON对象：
{"status":"ready|ready_with_assumptions|needs_clarification|insufficient_evidence|need_more_evidence","selected_tables":[{"table_id":"已提供ID","required_columns":["真实字段"],"evidence":["已提供source_id"]}],"join_plan":[{"relation_id":"已提供关系source_id","evidence":["已提供source_id"]}],"assumptions":[],"unresolved_gaps":[],"gaps":[],"database_change_reason":""}。
补检索gaps每项格式：{"kind":"missing_attribute","requirement":"缺少什么，字符串","checked_tables":["已提供table_id"],"requested_evidence":"需要的资料，必须是非空字符串而非数组或对象","search_query":"检索词，字符串","allow_engine_expansion":false}。kind也可为unclear_relation/description_conflict/intent_ambiguity/unknown_values。
推断关系可用kind=inferred、left_table/left_columns、right_table/right_columns、evidence和reason，但须明确假设，不声称已验证。使用column_layout解释columns数组。相似排名不证明业务正确；训练标注未经验证；inferred描述不是事实。同名字段不是关联依据；名称推断的必要关联无法确认时返回insufficient_evidence。培养国家与出生国家、国家总数与国家年份联合分组必须区分，遵循案例口径时列明假设。歧义不能靠增加表解决；没有值域工具，不编造取值。按公司、车型等业务实体分组时检查名称/编码口径，优先利用有证据的公司表或字典表提供业务名称；仅用编码时明确假设。逐项覆盖输出、分组、条件、统计和实体名称，对照相关案例检查遗漏关联表；不要机械复制案例。实体名称缺表时提出具体补检索，不能仅因主表有ID就ready。ready必须有表和字段且没有未决缺口；有假设用ready_with_assumptions。数据库改变必须说明依据。remaining_expansion_rounds为0时不得返回need_more_evidence。证据只引用本轮提供的source_id。'''
STATUSES = {'ready', 'ready_with_assumptions', 'needs_clarification', 'insufficient_evidence', 'need_more_evidence'}
GAPS = {'missing_attribute', 'unclear_relation', 'description_conflict', 'intent_ambiguity', 'unknown_values', 'wrong_business_database'}
SYSTEM += ''' 业务库已由上游独立选择，selected_business_databases限定本轮范围。不能直接选择范围外的表；怀疑业务库选错或缺少共享字典库时，提出kind=wrong_business_database或allow_business_expansion=true的具体gap，程序先重选业务库。普通缺字段补检索只在当前业务库执行。business_routing_assumptions是上游假设，必须保留，不得把假设当事实。'''


def sources(context):
    return {d['source_id'] for name in ('candidate_tables', 'knowledge', 'examples', 'relations', 'source_comparisons') for d in context.get(name, [])}


def normalize_result(result):
    """Only canonicalize equivalent containers; never invent missing evidence."""
    if not isinstance(result, dict):
        return result
    if result.get('status') == 'ready' and isinstance(result.get('assumptions'), list) and result['assumptions']:
        result['status'] = 'ready_with_assumptions'
    for gap in result.get('gaps', []) if isinstance(result.get('gaps', []), list) else []:
        if isinstance(gap, dict):
            value = gap.get('requested_evidence')
            if isinstance(value, list) and value and all(isinstance(v, str) and v.strip() for v in value):
                gap['requested_evidence'] = '; '.join(value)
    return result


def validate(result, context):
    errors = []
    if not isinstance(result, dict):
        return ['Output must be an object']
    status = result.get('status')
    if status not in STATUSES:
        errors.append('Invalid status')
    tables = {t['table_id']: t for t in context['candidate_tables']}
    evidence = sources(context)
    selected = result.get('selected_tables', [])
    if not isinstance(selected, list):
        return errors + ['selected_tables must be an array']
    ids = []
    for t in selected:
        if not isinstance(t, dict):
            errors.append('Selected table must be an object'); continue
        key = t.get('table_id'); ids.append(key)
        if key not in tables:
            errors.append(f'Unknown table: {key}'); continue
        if context.get('selected_business_databases') is not None and database_id(tables[key]) not in context['selected_business_databases']:
            errors.append(f'Table outside business database scope: {key}')
        fields = {c[0] for c in tables[key]['columns']}
        columns = t.get('required_columns')
        if not isinstance(columns, list) or not columns or any(c not in fields for c in columns):
            errors.append(f'Invalid required_columns: {key}')
        refs = t.get('evidence')
        if not isinstance(refs, list) or not refs or any(r not in evidence for r in refs):
            errors.append(f'Invalid evidence: {key}')
    if len(ids) != len(set(ids)):
        errors.append('Duplicate selected tables')
    for name in ('join_plan', 'assumptions', 'unresolved_gaps', 'gaps'):
        if not isinstance(result.get(name, []), list):
            errors.append(f'{name} must be an array')
    if errors:
        return errors
    relations = {r['source_id']: r for r in context['relations']}
    for join in result.get('join_plan', []):
        if not isinstance(join, dict):
            errors.append('Join must be an object'); continue
        if join.get('relation_id') in relations:
            relation = relations[join['relation_id']]
        elif join.get('kind') == 'inferred':
            relation = join
            if not result.get('assumptions') or not join.get('reason'):
                errors.append('Inferred relation needs reason and assumption')
            for side in ('left', 'right'):
                key = join.get(side + '_table')
                fields = {c[0] for c in tables.get(key, {}).get('columns', [])}
                columns = join.get(side + '_columns')
                if not isinstance(columns, list) or not columns or any(c not in fields for c in columns):
                    errors.append('Invalid inferred relation columns')
            if not join.get('left_columns') or not join.get('right_columns') or len(join['left_columns']) != len(join['right_columns']):
                errors.append('Join column count mismatch')
            if 'left_table' not in join or 'right_table' not in join:
                errors.append('Missing join endpoints'); continue
        else:
            errors.append('Unknown relation'); continue
        if relation['left_table'] not in ids or relation['right_table'] not in ids:
            errors.append('Relation endpoints must be selected')
        refs = join.get('evidence', [])
        if not refs or any(r not in evidence for r in refs):
            errors.append('Invalid join evidence')
        if 'unverified' in relation['kind'] and not result.get('assumptions'):
            errors.append('Unverified case relation needs an explicit assumption')
    for gap in result.get('gaps', []):
        if not isinstance(gap, dict):
            errors.append('Gap must be an object'); continue
        if gap.get('kind') not in GAPS:
            errors.append('Invalid gap kind')
        for field in ('requirement', 'requested_evidence', 'search_query'):
            if not isinstance(gap.get(field), str) or not gap[field].strip():
                errors.append(f'Gap requires {field}')
        checked = gap.get('checked_tables')
        if not isinstance(checked, list) or any(t not in tables for t in checked):
            errors.append('Invalid checked_tables')
        if not isinstance(gap.get('allow_engine_expansion'), bool):
            errors.append('allow_engine_expansion must be boolean')
        if 'allow_business_expansion' in gap and not isinstance(gap['allow_business_expansion'], bool):
            errors.append('allow_business_expansion must be boolean')
    if status in ('ready', 'ready_with_assumptions') and (not selected or result.get('unresolved_gaps') or result.get('gaps')):
        errors.append('Ready needs selected tables and no unresolved gaps')
    if status == 'ready' and result.get('assumptions'):
        errors.append('Use ready_with_assumptions for assumptions')
    if status == 'ready_with_assumptions' and not result.get('assumptions'):
        errors.append('Assumptions required')
    if status == 'need_more_evidence' and not result.get('gaps'):
        errors.append('Concrete gaps required')
    engines = sorted({tables[k]['engine'] for k in ids if k in tables})
    if engines != sorted(context['initial_databases']) and selected and not result.get('database_change_reason'):
        errors.append('Database change needs a reason')
    return errors


class DeepSeekClient:
    def __init__(self, api_key, model='deepseek-flash', endpoint='https://api.deepseek.com/chat/completions', retries=2):
        if not api_key:
            raise ValueError('Set DEEPSEEK_API_KEY')
        self.api_key, self.model, self.endpoint, self.retries = api_key, model, endpoint, retries
        self.calls = []

    def complete(self, messages, max_tokens, purpose):
        payload = {'model': self.model, 'messages': messages, 'max_tokens': max_tokens,
                   'temperature': 0, 'response_format': {'type': 'json_object'}, 'thinking': {'type': 'disabled'}}
        for attempt in range(self.retries + 1):
            started = time.monotonic()
            record = {'purpose': purpose, 'attempt': attempt + 1}
            self.calls.append(record)
            try:
                req = urllib.request.Request(self.endpoint, json.dumps(payload).encode(),
                                             {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.api_key})
                with urllib.request.urlopen(req, timeout=60) as response:
                    value = json.load(response)
                record.update(latency_seconds=time.monotonic() - started, usage=value.get('usage', {}), success=True,
                              finish_reason=value['choices'][0].get('finish_reason'), output_token_limit=max_tokens,
                              input_token_upper_bound=token_upper_bound(messages))
                return value['choices'][0]['message']['content']
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                record.update(latency_seconds=time.monotonic() - started, success=False, error_type=type(error).__name__)
                retryable = not isinstance(error, urllib.error.HTTPError) or error.code in (408, 429) or error.code >= 500
                if not retryable or attempt == self.retries:
                    raise RuntimeError(f'API transport failed: {type(error).__name__}') from error
                time.sleep(min(2 ** attempt, 4))


class Planner:
    def __init__(self, index, client, budget=None):
        self.builder = ContextBuilder(index, budget)
        self.client = client
        self.business_router = BusinessRouter(self.builder, client)

    def run(self, question, engines, question_id=None):
        start = time.monotonic()
        budget = self.builder.budget
        encoder = self.builder.index.encoder
        stats_initial = dict(self.builder.index.stats)
        cache_initial = len(encoder.cache) if encoder else 0
        log = {'judgment_calls': 0, 'repair_calls': 0, 'expansion_rounds': 0, 'rounds': [],
               'business_routing': [], 'stages': {'system_type': {'status': 'provided', 'selected': engines},
                                                'business_database': {'status': 'pending'},
                                                'table_selection': {'status': 'not_run'}}}
        context = {'question': question, 'question_id': question_id, 'candidate_tables': []}
        result = None
        business_keys, route_assumptions = [], []
        current_stage = 'business_database'
        call_start = len(getattr(self.client, 'calls', []))

        def finish():
            tables = {t['table_id']: t for t in context.get('candidate_tables', [])}
            chosen = [tables[t['table_id']] for t in result.get('selected_tables', []) if t['table_id'] in tables]
            result.update(question_id=question_id, initial_databases=engines,
                          selected_business_databases=business_keys,
                          final_business_databases=sorted({database_id(t) for t in chosen}),
                          final_databases=sorted({t['engine'] for t in chosen}),
                          retrieval_class=('single' if len({t['engine'] for t in chosen}) == 1 else 'multi') if chosen else None)
            log['retrieval_stats'] = {k: v - stats_initial[k] for k, v in self.builder.index.stats.items()}
            stats = log['retrieval_stats']
            stats['embedding_cache_hit_rate'] = stats['embedding_cache_hits'] / stats['semantic_queries'] if stats['semantic_queries'] else None
            log['embedding_cache'] = {'entries_before': cache_initial, 'entries_after': len(encoder.cache) if encoder else 0}
            log.update(latency_seconds=time.monotonic() - start,
                       transport_calls=getattr(self.client, 'calls', [])[call_start:],
                       business_routing_calls=len(log['business_routing']))
            return {'pipeline_version': PIPELINE_VERSION, 'result': result, 'execution': log, 'context': context}

        def route(route_engines, gaps=None):
            self.business_router.last_run = None
            try:
                output = self.business_router.run(question, route_engines, question_id, business_keys, gaps)
            finally:
                if self.business_router.last_run is not None:
                    log['business_routing'].append(self.business_router.last_run)
            log['stages']['business_database'] = {'status': output['result']['status'],
                'selected': [d['database_id'] for d in output['result']['selected_business_databases']]}
            return output['result']

        def parse_plan(raw):
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and isinstance(parsed.get('assumptions', []), list):
                parsed.setdefault('assumptions', [])
                for assumption in route_assumptions:
                    if assumption not in parsed['assumptions']:
                        parsed['assumptions'].append(assumption)
                parsed = normalize_result(parsed)
            return parsed

        try:
            routed = route(engines)
            business_keys = [d['database_id'] for d in routed['selected_business_databases']]
            route_assumptions = routed['assumptions']
            if routed['status'] not in ('ready', 'ready_with_assumptions'):
                result = {**routed, 'selected_tables': [], 'failed_stage': 'business_database'}
                return finish()
            active_engines = sorted({key.split(':', 1)[0] for key in business_keys})
            current_stage = 'table_selection'
            context = self.builder.assemble(question, active_engines, question_id, business_databases=business_keys)
            context.update(initial_databases=engines, business_routing_assumptions=route_assumptions,
                           business_database_change_reason=routed.get('database_change_reason', ''))
            for round_number in range(budget.judgment_calls):
                log['stages']['table_selection']['status'] = 'running'
                raw_context = context
                context, messages = self.builder.fit(context, SYSTEM)
                if self.builder.tokenizer and round_number == 0:
                    from token_report import context_profile
                    log['table_context_profiles'] = {'raw': context_profile(raw_context, SYSTEM, self.builder.tokenizer),
                                                     'fitted': context_profile(context, SYSTEM, self.builder.tokenizer)}
                log['rounds'].append({'source_ids': sorted(sources(context)), 'omitted_evidence': context['omitted_evidence'],
                                      'business_databases': list(business_keys), 'system_types': active_engines,
                                      'input_token_upper_bound': token_upper_bound(messages), 'estimated_input_tokens': self.builder.estimate(messages)})
                log['judgment_calls'] += 1
                raw = self.client.complete(messages, budget.output_tokens, 'judgment')
                log.setdefault('model_outputs', []).append({'purpose': 'judgment', 'raw': raw})
                try:
                    result = parse_plan(raw)
                    errors = validate(result, context)
                except (ValueError, TypeError):
                    errors = ['Invalid JSON']; result = None
                if errors and log['repair_calls'] < budget.repair_calls:
                    # The malformed response also counts towards the input budget.
                    repair_messages = [{'role': 'assistant', 'content': raw},
                                       {'role': 'user', 'content': json.dumps({'repair_errors': errors, 'instruction': '修复JSON结构，不扩大资料范围。'}, ensure_ascii=False)}]
                    context, repair_input = self.builder.fit(context, SYSTEM, repair_messages, allow_pruning=False)
                    log.setdefault('repairs', []).append({'input_token_upper_bound': token_upper_bound(repair_input), 'errors': errors, 'source_ids': sorted(sources(context)), 'estimated_input_tokens': self.builder.estimate(repair_input)})
                    log['repair_calls'] += 1
                    raw = self.client.complete(repair_input, budget.output_tokens, 'repair')
                    log.setdefault('model_outputs', []).append({'purpose': 'repair', 'raw': raw})
                    try:
                        result = parse_plan(raw); errors = validate(result, context)
                    except (ValueError, TypeError):
                        errors = ['Invalid JSON after repair']
                if errors:
                    raise ValueError('; '.join(errors))
                # Status describes the judgment, not whether retrieval can help.
                # A valid insufficient_evidence response may still request schema.
                if result['status'] in ('ready', 'ready_with_assumptions'):
                    break
                gaps = result.get('gaps', [])
                actionable = [g for g in gaps if g['kind'] not in ('intent_ambiguity', 'unknown_values')]
                if not actionable or log['expansion_rounds'] >= budget.expansion_rounds or round_number + 1 >= budget.judgment_calls:
                    result['status'] = 'needs_clarification' if result['status'] == 'needs_clarification' or any(g['kind'] == 'intent_ambiguity' for g in gaps) else 'insufficient_evidence'
                    result['unresolved_gaps'] = result.get('unresolved_gaps', []) + [g for g in gaps if g not in result.get('unresolved_gaps', [])]
                    result['stop_reason'] = 'no_actionable_gaps' if not actionable else 'budget_exhausted'
                    break
                before = sources(context)
                before_business = list(business_keys)
                reroute = any(g['kind'] == 'wrong_business_database' or g.get('allow_business_expansion') or g.get('allow_engine_expansion') for g in actionable)
                if reroute:
                    current_stage = 'business_database'
                    route_engines = sorted({t['engine'] for t in self.builder.index.tables.values()}) if any(g.get('allow_engine_expansion') for g in actionable) else active_engines
                    routed = route(route_engines, actionable)
                    if routed['status'] not in ('ready', 'ready_with_assumptions'):
                        result.update(status=routed['status'], unresolved_gaps=routed['unresolved_gaps'] or actionable,
                                      failed_stage='business_database', stop_reason='business_routing_unresolved')
                        break
                    business_keys = [d['database_id'] for d in routed['selected_business_databases']]
                    route_assumptions = routed['assumptions']
                    active_engines = sorted({key.split(':', 1)[0] for key in business_keys})
                    current_stage = 'table_selection'
                    # Rebuild after a scope change: do not retain out-of-scope evidence.
                    expanded = self.builder.assemble(question, active_engines, question_id, business_databases=business_keys)
                    expanded.update(initial_databases=engines, business_routing_assumptions=route_assumptions,
                                    business_database_change_reason=routed.get('database_change_reason', ''))
                    expanded['retrieval_budget']['remaining_expansion_rounds'] = 0
                    log.setdefault('business_scope_changes', []).append({'selected': business_keys,
                        'removed_sources': sorted(before - sources(expanded)), 'gaps': actionable})
                else:
                    expanded = self.builder.assemble(question, active_engines, question_id, context, actionable,
                                                     business_databases=business_keys)
                    expanded['business_routing_assumptions'] = route_assumptions
                    expanded['business_database_change_reason'] = context.get('business_database_change_reason', '')
                expanded['previous_judgment'] = {'status': result['status'], 'gaps': actionable,
                                                 'business_scope_changed': True} if reroute else result
                expanded, _ = self.builder.fit(expanded, SYSTEM)
                log['expansion_rounds'] += 1
                if not sources(expanded) - before and business_keys == before_business:
                    result.update(status='insufficient_evidence', unresolved_gaps=gaps, stop_reason='no_new_evidence')
                    break
                context = expanded
            if result['status'] == 'need_more_evidence':
                result.update(status='insufficient_evidence', unresolved_gaps=result.get('gaps', []), stop_reason='budget_exhausted')
            log['stages']['table_selection']['status'] = result['status'] if current_stage == 'table_selection' else 'interrupted_for_business_routing'
            if result['status'] not in ('ready', 'ready_with_assumptions'):
                result.setdefault('failed_stage', current_stage)
        except Exception as error:
            result = {'question_id': question_id, 'status': 'error', 'initial_databases': engines,
                      'failed_stage': current_stage,
                      'error': f'{type(error).__name__}: {error}'}
            log['stages'][current_stage]['status'] = 'error'
        return finish()
