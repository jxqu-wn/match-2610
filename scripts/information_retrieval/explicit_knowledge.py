"""Literal knowledge-to-table references; no field-only or business inference."""
import re
from collections import Counter

IDENTIFIER = r'[A-Za-z_][A-Za-z0-9_]*'


def literal_references(text, tables):
    links = {}
    counts = Counter(((t.get('database') or t.get('schema') or '').casefold(), t['name'].casefold()) for t in tables.values())
    def add(key, kind, mention):
        item = {'kind': kind, 'mention': mention}
        if item not in links.setdefault(key, []):
            links[key].append(item)

    for key, table in tables.items():
        namespace = table.get('database') or table.get('schema')
        if namespace:
            pattern = r'(?<![A-Za-z0-9_])' + re.escape(namespace + '.' + table['name']) + r'(?![A-Za-z0-9_])'
            if counts[(namespace.casefold(), table['name'].casefold())] == 1:
                for match in re.finditer(pattern, text, re.I):
                    add(key, 'qualified_table', match.group())

    scopes = list(re.finditer(r'数据库(' + IDENTIFIER + r')', text))
    for n, match in enumerate(scopes):
        region = text[match.end():scopes[n+1].start() if n+1 < len(scopes) else len(text)]
        for key, table in tables.items():
            namespace = table.get('database') or table.get('schema')
            if namespace and namespace.casefold() == match[1].casefold():
                pattern = r'(?<![A-Za-z0-9_.])' + re.escape(table['name']) + r'(?![A-Za-z0-9_])'
                name = re.escape(table['name'])
                lists = re.findall(r'表\s*([A-Za-z_][A-Za-z0-9_-]*(?:\s*[和及与、,]\s*[A-Za-z_][A-Za-z0-9_-]*)*)', region)
                listed = any(re.search(pattern, value, re.I) for value in lists)
                suffix = re.search(r'(?<![A-Za-z0-9_.])' + name + r'\s*表', region, re.I)
                reference = re.search(r'(?:关联到?|映射到)\s*' + name + r'(?![A-Za-z0-9_])', region, re.I)
                fields = re.findall(r'(?<![A-Za-z0-9_.])' + name + r'\.(' + IDENTIFIER + r')(?![A-Za-z0-9_])', region, re.I)
                field_reference = any(field.casefold() in {c['name'].casefold() for c in table['columns']} for field in fields)
                if counts[(namespace.casefold(), table['name'].casefold())] == 1 and (listed or suffix or reference or field_reference):
                    add(key, 'database_scoped_table_name', match.group() + ' … ' + table['name'])

    # Table.field is explicit only when both identifiers exist in the catalog
    # and the pair resolves uniquely. A shared field name alone never links.
    for match in re.finditer(r'(?<![A-Za-z0-9_])(' + IDENTIFIER + r')\.(' + IDENTIFIER + r')(?![A-Za-z0-9_])', text):
        candidates = [key for key, table in tables.items() if table['name'].casefold() == match[1].casefold()
                      and any(c['name'].casefold() == match[2].casefold() for c in table['columns'])]
        if len(candidates) == 1:
            add(candidates[0], 'unique_table_field', match.group())
    return links
