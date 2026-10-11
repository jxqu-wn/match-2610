"""Local reference comparison packets. No model judge or reference export."""
import argparse
import json
from pathlib import Path

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from index import ROOT, SourceResolver, RetrievalIndex, DEFAULT_INDEX


def required_fields(query, engine, resolver):
    if engine == 'Elasticsearch':
        return {}
    tree = sqlglot.parse_one(query, read={'MYSQL': 'mysql', 'POSTGRESQL': 'postgres', 'SQLite': 'sqlite'}[engine])
    fields = {}
    for scope in traverse_scope(tree):
        aliases = {alias.lower(): resolver.resolve(engine, table) for alias, table in scope.sources.items() if isinstance(table, exp.Table)}
        keys = {key for key in aliases.values() if key}
        for column in scope.columns:
            if column.is_star:
                continue
            key = aliases.get(column.table.lower()) if column.table else None
            if not column.table:
                candidates = [k for k in keys if any(c['name'].lower() == column.name.lower() for c in resolver.tables[k]['columns'])]
                key = candidates[0] if len(candidates) == 1 else None
            if key:
                names = {c['name'].lower(): c['name'] for c in resolver.tables[key]['columns']}
                if column.name.lower() in names:
                    fields.setdefault(key, set()).add(names[column.name.lower()])
    return {key: sorted(values) for key, values in fields.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    # Read schema only. Reference answers never enter an index or external request.
    tables = {t['table_id']: t for t in json.loads((ROOT / 'data/preprocessed/schema_catalog.json').read_text())['tables']}
    resolver = SourceResolver(tables)
    validation = {r['question_id']: r for r in json.loads((ROOT / 'data/赛题8/splits/validation.json').read_text())}
    selection = json.loads((args.directory / 'selection.json').read_text())
    packets = []
    for item in selection:
        path = args.directory / f"question_{item['question_id']}.json"
        if not path.exists():
            continue
        output = json.loads(path.read_text())
        row = validation[item['question_id']]
        refs, joins, required = [], [], {}
        for db, query in [('db', 'query')] + [(f'db{i}', f'query{i}') for i in range(1, 4)]:
            if db in row:
                refs.append({'engine': row[db], 'query': row[query]})
                parsed = resolver.parse(row[query], row[db])
                joins.extend(parsed['joins'])
                for key, fields in required_fields(row[query], row[db], resolver).items():
                    required.setdefault(key, set()).update(fields)
        actual = {t['table_id']: set(t['required_columns']) for t in output['result'].get('selected_tables', [])}
        missing = {key: sorted(fields - actual.get(key, set())) for key, fields in required.items() if fields - actual.get(key, set())}
        relations = {r['source_id']: r for r in output['context'].get('relations', [])}
        join_plan = [relations.get(j.get('relation_id'), j) for j in output['result'].get('join_plan', [])]
        packets.append({'question_id': row['question_id'], 'question': row['question'], 'reference': refs,
                        'required_fields': {k: sorted(v) for k,v in required.items()}, 'missing_reference_fields': missing,
                        'reference_joins': joins, 'plan': output['result'], 'resolved_join_plan': join_plan})
    (args.directory / 'local_review_packets.json').write_text(json.dumps(packets, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'local_review_packets': len(packets), 'reference_data_sent': False}))


if __name__ == '__main__':
    main()
