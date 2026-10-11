"""Apply recorded Codex review corrections; never call an API."""
import argparse
from collections import Counter
import json
from pathlib import Path

from build_catalog import DEFAULT_OUTPUT, save_json
from enrich_descriptions import documents


def apply_review(catalog, review):
    by_id = {t['table_id']: t for t in catalog['tables']}
    for item in review['checks']:
        table = by_id[item['table_id']]
        table['agent_review'] = {'reviewer': review['reviewer'], 'scope': item['scope'],
                                 'notes': item['notes']}
    for correction in review['corrections']:
        table = by_id[correction['table_id']]
        target = table if correction['field'] is None else next(
            c for c in table['columns'] if c['name'] == correction['field'])
        if target['description'] not in (correction['before'], correction['after']):
            raise ValueError(f'Review stale for {correction["table_id"]}.{correction["field"]}')
        target['description'] = correction['after']
        target['description_origin'] = 'agent_review'
        target['agent_review'] = {'reviewer': review['reviewer'], 'reason': correction['reason'],
                                  'evidence': correction['evidence']}
    catalog['description_summary'] = {
        'tables_with_description': sum(bool(t['description']) for t in catalog['tables']),
        'columns_with_description': sum(bool(c['description']) for t in catalog['tables'] for c in t['columns']),
        'columns_unknown': sum(c['description'] is None for t in catalog['tables'] for c in t['columns']),
        'model_field_statuses': dict(Counter(c['description_review']['status'] for t in catalog['tables'] for c in t['columns'])),
        'agent_corrections': len(review['corrections'])}
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    catalog = json.loads((args.output / 'schema_catalog.json').read_text())
    review = json.loads((args.output / 'manual_review.json').read_text())
    secondary_path = args.output / 'secondary_review.json'
    if secondary_path.exists():
        from secondary_review import restore_previous, apply_secondary
        restore_previous(catalog)
    apply_review(catalog, review)
    if secondary_path.exists():
        apply_secondary(catalog, json.loads(secondary_path.read_text()))
    save_json(args.output / 'schema_catalog.json', catalog)
    (args.output / 'schema_documents.jsonl').write_text(''.join(json.dumps(d, ensure_ascii=False) + '\n' for d in documents(catalog['tables'])))
    print(json.dumps(catalog['description_summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
