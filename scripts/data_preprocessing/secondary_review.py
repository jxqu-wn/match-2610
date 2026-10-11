"""Apply evidence-backed secondary review without changing schema facts."""
from collections import Counter


def restore_previous(catalog):
    for table in catalog['tables']:
        for target in [table] + table['columns']:
            previous = target.pop('secondary_review', None)
            if previous:
                target['description'] = previous['before']
                target['description_origin'] = previous['before_origin']
        table.pop('secondary_issues', None)


def apply_secondary(catalog, report):
    by_id = {t['table_id']: t for t in catalog['tables']}
    for entry in report['field_reviews']:
        table = by_id[entry['table_id']]
        target = table if entry['field'] is None else next(c for c in table['columns'] if c['name'] == entry['field'])
        if target['description'] != entry['before']:
            raise ValueError(f'Secondary review stale: {entry["table_id"]}.{entry["field"]}')
        target['secondary_review'] = {**entry, 'before_origin': target['description_origin'],
                                      'reviewer': report['reviewer']}
        if entry['after'] != entry['before']:
            target['description'] = entry['after']
            target['description_origin'] = 'agent_secondary_review'
    for issue in report['special_cases']:
        by_id[issue['table_id']].setdefault('secondary_issues', []).append(issue)
    catalog['description_summary'].update(
        columns_with_description=sum(bool(c['description']) for t in catalog['tables'] for c in t['columns']),
        columns_unknown=sum(c['description'] is None for t in catalog['tables'] for c in t['columns']),
        secondary_review_statuses=dict(Counter(e['status'] for e in report['field_reviews'])),
        previous_unknown_outcomes=dict(Counter(e['status'] for e in report['field_reviews'] if e['before'] is None)),
        secondary_description_changes=sum(e['before'] != e['after'] for e in report['field_reviews']),
        secondary_special_cases=len(report['special_cases']))
