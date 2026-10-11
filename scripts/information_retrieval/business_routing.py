"""Select business databases before retrieving complete table schemas."""
import json
from collections import defaultdict

PIPELINE_VERSION = 'system-business-table-v1'


def database_id(table):
    # PostgreSQL sources expose schemas; ES sources expose index namespaces.
    name = table.get('database') or table.get('schema') or table.get('schema_name') or table['name']
    return table['engine'] + ':' + name


BUSINESS_SYSTEM = '''你负责系统类型确定之后的业务库选择，不选择具体字段，不生成SQL。仅输出JSON：
{"status":"ready|ready_with_assumptions|needs_clarification|insufficient_evidence","selected_business_databases":[{"database_id":"候选ID","reason":"选择依据","evidence":["候选source_id"]}],"assumptions":[],"unresolved_gaps":[],"database_change_reason":""}。
根据问题及业务库目录选择必要的一个或多个业务库。目录中的表简介仅说明覆盖范围，描述可能含推断，不能把名称或相似性当成已验证事实。选择业务范围一致的库；不要因为都是球员、公司、电影就混合不同领域。共享字典库只有确实需要解释编码/业务名称时才选，可参考跨库外键目录。跨年度、跨系统问题可选多个库；没有明确年度且多个库同样适用时说明歧义或假设，不能默默选最新年份。无法确定范围时返回needs_clarification或insufficient_evidence，不扩大到所有库。ready需要非空选择且没有假设、未决缺口；有假设用ready_with_assumptions。证据只引用提供的业务库source_id。重选库时根据retrieval_gaps和previous_selection检查原选择，可纠正或补充业务库；改变系统集合必须给database_change_reason。'''


class BusinessRouter:
    def __init__(self, builder, client):
        self.builder, self.client = builder, client

    def catalog(self, question, engines, question_id=None, previous_selection=None, gaps=None):
        groups = defaultdict(list)
        for table in self.builder.index.tables.values():
            if table['engine'] in engines:
                groups[database_id(table)].append(table)
        candidates = []
        for key, tables in sorted(groups.items()):
            relations = []
            for table in tables:
                for fk in table['foreign_keys']:
                    target = self.builder.index.tables.get(fk['references']['table_id'])
                    if target and database_id(target) != key:
                        relations.append({'from_table': table['name'], 'to_database': database_id(target),
                                          'to_table': target['name']})
            candidates.append({'source_id': 'database:' + key, 'database_id': key,
                               'engine': tables[0]['engine'], 'name': key.split(':', 1)[1],
                               'table_count': len(tables),
                               'tables': [{'name': t['name'], 'description': t['description']} for t in tables],
                               'cross_database_foreign_keys': relations})
        return {'stage': 'business_database', 'question_id': question_id, 'question': question,
                'system_types': list(engines), 'candidate_databases': candidates,
                'previous_selection': previous_selection or [], 'retrieval_gaps': gaps or [],
                'catalog_detail': 'table_names_and_descriptions',
                'description_note': 'From schema catalog; includes reviewed and inferred descriptions, not business query answers.'}

    def fit(self, context, extra_messages=()):
        context = json.loads(json.dumps(context))
        budget = self.builder.budget
        reserve = budget.business_repair_calls * budget.repair_reserve if not extra_messages else 0
        limit = budget.context_tokens - budget.output_tokens - reserve
        while True:
            messages = [{'role': 'system', 'content': BUSINESS_SYSTEM},
                        {'role': 'user', 'content': json.dumps(context, ensure_ascii=False, separators=(',', ':'))}] + list(extra_messages)
            estimate = self.builder.estimate(messages)
            if estimate <= limit:
                return context, messages, estimate
            if extra_messages:
                raise ValueError('Business routing repair exceeds budget with frozen catalog')
            if context['catalog_detail'] == 'table_names_only':
                raise ValueError('Business database catalog exceeds context budget')
            # All databases and all table names survive. No silent top-k routing.
            for db in context['candidate_databases']:
                for table in db['tables']:
                    table.pop('description', None)
            context['catalog_detail'] = 'table_names_only'

    @staticmethod
    def validate(result, context):
        if not isinstance(result, dict):
            return ['Business routing output must be an object']
        errors = []
        if result.get('status') not in ('ready', 'ready_with_assumptions', 'needs_clarification', 'insufficient_evidence'):
            errors.append('Invalid business routing status')
        candidates = {d['database_id']: d for d in context['candidate_databases']}
        selected = result.get('selected_business_databases')
        if not isinstance(selected, list):
            return errors + ['selected_business_databases must be an array']
        seen = set()
        for item in selected:
            if not isinstance(item, dict) or not isinstance(item.get('database_id'), str):
                errors.append('Invalid business database selection'); continue
            key = item['database_id']
            if key not in candidates:
                errors.append('Unknown business database: ' + key); continue
            if key in seen:
                errors.append('Duplicate business database: ' + key)
            seen.add(key)
            if not isinstance(item.get('reason'), str) or not item['reason'].strip():
                errors.append('Business database selection needs reason')
            refs = item.get('evidence')
            if not isinstance(refs, list) or not refs or any(r != candidates[key]['source_id'] for r in refs):
                errors.append('Invalid business database evidence: ' + key)
        for name in ('assumptions', 'unresolved_gaps'):
            if not isinstance(result.get(name), list):
                errors.append(name + ' must be an array')
        if errors:
            return errors
        if result['status'] in ('ready', 'ready_with_assumptions') and (not selected or result['unresolved_gaps']):
            errors.append('Ready business routing needs a selection and no unresolved gaps')
        if result['status'] == 'ready' and result['assumptions']:
            errors.append('Use ready_with_assumptions for business assumptions')
        if result['status'] == 'ready_with_assumptions' and not result['assumptions']:
            errors.append('Business assumptions required')
        selected_engines = {candidates[key]['engine'] for key in seen}
        if selected and selected_engines != set(context['system_types']) and not result.get('database_change_reason'):
            errors.append('Business routing system change needs a reason')
        return errors

    def run(self, question, engines, question_id=None, previous_selection=None, gaps=None):
        context, messages, estimate = self.fit(self.catalog(question, engines, question_id, previous_selection, gaps))
        log = {'input_estimate': estimate, 'repair_calls': 0, 'model_outputs': []}
        self.last_run = {'result': None, 'context': context, 'execution': log}
        raw = self.client.complete(messages, self.builder.budget.output_tokens, 'business_routing')
        log['model_outputs'].append({'purpose': 'business_routing', 'raw': raw})
        def parse(value):
            try:
                result = json.loads(value)
                if isinstance(result, dict) and result.get('status') == 'ready' and result.get('assumptions'):
                    result['status'] = 'ready_with_assumptions'
                return result, self.validate(result, context)
            except (ValueError, TypeError):
                return None, ['Invalid business routing JSON']
        result, errors = parse(raw)
        if errors and self.builder.budget.business_repair_calls:
            extra = [{'role': 'assistant', 'content': raw},
                     {'role': 'user', 'content': json.dumps({'repair_errors': errors, 'instruction': '修复结构，只能选择本目录业务库。'}, ensure_ascii=False)}]
            _, repair_messages, estimate = self.fit(context, extra)
            log.update(repair_calls=1, repair_errors=errors, repair_input_estimate=estimate)
            raw = self.client.complete(repair_messages, self.builder.budget.output_tokens, 'business_routing_repair')
            log['model_outputs'].append({'purpose': 'business_routing_repair', 'raw': raw})
            result, errors = parse(raw)
        if errors:
            raise ValueError('; '.join(errors))
        self.last_run['result'] = result
        return self.last_run
