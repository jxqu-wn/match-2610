"""Extract source schemas without network access; preserve evidence and DDL."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / 'data/preprocessed'
ATOM = r'(?:"[^"]+"|`[^`]+`|\w+)'
IDENT = ATOM + r'(?:\.' + ATOM + r')?'


def read_source(path):
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError(f'Unknown encoding: {path}')


def clean_identifier(name):
    return name.replace('"', '').replace('`', '')


def balanced_end(text, start, opening='(', closing=')'):
    depth, quote, i = 0, None, start
    while i < len(text):
        char = text[i]
        if quote:
            if char == '\\':
                i += 2
                continue
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 2
                    continue
                quote = None
        elif char in "'\"`":
            quote = char
        elif text.startswith('--', i) or text.startswith('//', i):
            i = text.find('\n', i)
            if i == -1:
                break
            continue
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError('Unbalanced source definition')


def split_columns(body):
    # SQL punctuation inside type arguments or quoted comments is not a separator.
    body = re.sub(r'--[^\n]*', '', body)
    result, start, depth, quote, i = [], 0, 0, None, 0
    while i < len(body):
        char = body[i]
        if quote:
            if char == '\\':
                i += 2
                continue
            if char == quote:
                if i + 1 < len(body) and body[i + 1] == quote:
                    i += 2
                    continue
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            result.append(body[start:i].strip())
            start = i + 1
        i += 1
    result.append(body[start:].strip())
    return result


def comment(text):
    match = re.search(r"\bCOMMENT\s*=?\s*'((?:''|\\.|[^'])*)'", text, re.I)
    return match[1].replace("''", "'") if match else None


def names(text):
    return [clean_identifier(x.strip()) for x in text.split(',')]


def parse_sql(text, filename, encoding):
    records = []
    starts = list(re.finditer(r'CREATE\s+TABLE\s+(?:IF NOT EXISTS\s+)?(' + IDENT + r')\s*\(', text, re.I))
    for number, match in enumerate(starts):
        prefix = text[:match.start()]
        dbs = re.findall(r'数据库:\s*(\w+)|\bUSE\s+(\w+)\s*;', prefix)
        database = next((a or b for a, b in reversed(dbs)), None)
        table_name = clean_identifier(match[1])
        schema = None
        engine = 'SQLite' if filename.endswith('bird_schemas.txt') else 'MYSQL'
        if table_name.startswith('public.'):
            engine, database, schema = 'POSTGRESQL', None, 'public'
        table = table_name.split('.')[-1]
        table_id = f'{engine}:{database or schema}.{table}'
        end = balanced_end(text, match.end() - 1)
        if number + 1 < len(starts) and end >= starts[number + 1].start():
            raise ValueError(f'Definition overlaps next table: {table_id}')
        next_start = starts[number + 1].start() if number + 1 < len(starts) else len(text)
        suffix = text[end + 1:next_start]
        # SQLite definitions have no semicolon; MySQL options end at semicolon.
        options = suffix[:suffix.find(';') + 1] if engine == 'MYSQL' and ';' in suffix else ''
        record = {'table_id': table_id, 'engine': engine, 'database': database,
                  'schema': schema, 'object_type': 'table', 'name': table,
                  'description': comment(options), 'description_origin': 'schema_comment' if comment(options) else None,
                  'columns': [], 'primary_key': [], 'foreign_keys': [], 'constraints': [],
                  'knowledge': [], 'training_examples': [],
                  'source': {'file': filename, 'encoding': encoding,
                             'start_line': text.count('\n', 0, match.start()) + 1},
                  'raw_definition': text[match.start():end + 1] + options}
        for part in split_columns(text[match.end():end]):
            constraint = re.match(r'(?:CONSTRAINT\s+' + IDENT + r'\s+)?(?:PRIMARY|FOREIGN|UNIQUE|CHECK|KEY|INDEX)\b', part, re.I)
            if constraint:
                record['constraints'].append(part)
            else:
                col = re.match(r'(' + IDENT + r')\s+(.+)', part, re.S)
                if not col:
                    raise ValueError(f'Unparsed column in {table_id}: {part}')
                field, rest = clean_identifier(col[1]), col[2]
                dtype = re.split(r'\s+(?:CONSTRAINT|PRIMARY|NOT|NULL|DEFAULT|COMMENT|REFERENCES|UNIQUE|CHECK|AUTO_INCREMENT)\b', rest, maxsplit=1, flags=re.I)[0].strip()
                declared_not_null = bool(re.search(r'\bNOT NULL\b', rest, re.I))
                primary = bool(re.search(r'\bPRIMARY KEY\b', rest, re.I))
                record['columns'].append({'name': field, 'data_type': dtype,
                                         'nullable': not (declared_not_null or (primary and (engine != 'SQLite' or dtype.upper() == 'INTEGER'))),
                                         'description': comment(rest),
                                         'description_origin': 'schema_comment' if comment(rest) else None,
                                         'knowledge_ids': [], 'raw_definition': part})
                if re.search(r'\bPRIMARY KEY\b', rest, re.I):
                    record['primary_key'].append(field)
            pk = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', part, re.I)
            if pk:
                record['primary_key'] = names(pk[1])
            fk = re.search(r'FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+(' + IDENT + r')\s*\(([^)]+)\)', part, re.I)
            inline = re.search(r'REFERENCES\s+(' + IDENT + r')(?:\s*\(([^)]+)\))?', part, re.I)
            if fk or (inline and not constraint):
                target = clean_identifier(fk[2] if fk else inline[1])
                if '.' not in target:
                    target = f'{database or schema}.{target}'
                record['foreign_keys'].append({'columns': names(fk[1]) if fk else [field],
                                               'references': {'table_id': f'{engine}:{target}',
                                                              'columns': names(fk[3] if fk else inline[2]) if (fk or inline[2]) else []},
                                               'raw_definition': part})
        if engine == 'POSTGRESQL':
            for target, value in re.findall(r"COMMENT ON (?:TABLE|COLUMN)\s+([^\s]+)\s+IS\s+'((?:''|[^'])*)'", suffix, re.I):
                target = clean_identifier(target)
                if target == table_name:
                    record.update(description=value, description_origin='schema_comment')
                elif target.startswith(table_name + '.'):
                    for column in record['columns']:
                        if column['name'] == target.split('.')[-1]:
                            column.update(description=value, description_origin='schema_comment')
        records.append(record)
    return records


def parse_es(text, filename, encoding):
    records = []
    for match in re.finditer(r'^PUT\s+/(\w+)\s*\n\s*\{', text, re.M):
        start = match.end() - 1
        end = balanced_end(text, start, '{', '}')
        raw = text[start:end + 1]
        mapping = json.loads(re.sub(r'//[^\n]*', '', raw))
        columns = []
        def visit(properties, prefix=''):
            for name, definition in properties.items():
                full = prefix + name
                columns.append({'name': full, 'data_type': definition.get('type', 'object'),
                                'nullable': None, 'description': None, 'description_origin': None,
                                'knowledge_ids': [], 'mapping': definition})
                visit(definition.get('properties', {}), full + '.')
                visit(definition.get('fields', {}), full + '.')
        visit(mapping['mappings']['properties'])
        records.append({'table_id': f'Elasticsearch:{match[1]}', 'engine': 'Elasticsearch',
                        'database': None, 'schema': None, 'object_type': 'index', 'name': match[1],
                        'description': None, 'description_origin': None, 'columns': columns,
                        'primary_key': [], 'foreign_keys': [], 'constraints': [], 'knowledge': [],
                        'training_examples': [], 'raw_definition': text[match.start():end + 1],
                        'source': {'file': filename, 'encoding': encoding,
                                   'start_line': text.count('\n', 0, match.start()) + 1}})
    return records


def build(data=ROOT / 'data'):
    tables, sources = [], []
    for filename in ('bird_schemas.txt', 'commom_schema.txt', 'core_schema.txt'):
        path = data / '赛题8/Schema' / filename
        text, encoding = read_source(path)
        source = str(path.relative_to(ROOT))
        tables.extend(parse_sql(text, source, encoding))
        tables.extend(parse_es(text, source, encoding))
        sources.append({'file': source, 'encoding': encoding,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    index = {(t['database'], t['name']): t for t in tables}
    knowledge = json.loads((data / '赛题8/knowledge.json').read_text())
    for item in knowledge:
        match = re.search(r'数据库([A-Za-z0-9_]+)的表([A-Za-z0-9_]+)', item['knowledge_text'])
        table = index.get((match[1], match[2])) if match else None
        if table:
            table['knowledge'].append(item)
            for column in table['columns']:
                field = re.search(r'字段' + re.escape(column['name']) + r'，.*?表示(.+?)(?:，取值为|。|$)', item['knowledge_text'])
                if field:
                    column['knowledge_ids'].append(item['knowledge_id'])
                    if not column['description']:
                        column.update(description=field[1], description_origin='knowledge')
    rows = json.loads((data / '赛题8/splits/train.json').read_text())
    for table in tables:
        # Some knowledge records describe several fields in one sentence,
        # rather than using the standardized “字段..., 表示...” template.
        for column in table['columns']:
            if column['description']:
                continue
            for item in table['knowledge']:
                match = re.search(r'(?<![A-Za-z0-9_])' + re.escape(column['name']) +
                                  r'(?:字段)?表示([^，；。：]+)', item['knowledge_text'])
                if match:
                    # Keep the short definition, not a partial parenthesized
                    # value example cut off by the sentence separator.
                    description = re.split(r'[（(]', match[1], maxsplit=1)[0].strip()
                    column.update(description=description, description_origin='knowledge')
                    column['knowledge_ids'].append(item['knowledge_id'])
                    break
        qualified = f"{table['database'] or table['schema']}.{table['name']}" if table['engine'] != 'Elasticsearch' else table['name']
        for row in rows:
            for db_key, query_key in [('db', 'query')] + [(f'db{i}', f'query{i}') for i in range(1, 4)]:
                if row.get(db_key) != table['engine']:
                    continue
                target = table['name'] if table['engine'] == 'POSTGRESQL' else qualified
                if re.search(r'(?<!\w)' + re.escape(target) + r'(?!\w)', row.get(query_key, ''), re.I):
                    table['training_examples'].append({'question_id': row['question_id'], 'question': row['question'],
                                                       'query': row[query_key], 'step': query_key})
        table['training_examples'] = table['training_examples'][:4]
    ids = [t['table_id'] for t in tables]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate table identifiers')
    for table in tables:
        fields = [c['name'] for c in table['columns']]
        if len(fields) != len(set(fields)):
            raise ValueError(f'Duplicate columns: {table["table_id"]}')
    by_id = {t['table_id']: t for t in tables}
    for table in tables:
        for column in table['columns']:
            if column['name'] in table['primary_key'] and table['engine'] != 'SQLite':
                column['nullable'] = False
        for fk in table['foreign_keys']:
            if not fk['references']['columns']:
                target = by_id.get(fk['references']['table_id'])
                if not target or not target['primary_key']:
                    raise ValueError(f'Cannot resolve implicit referenced primary key: {fk}')
                fk['references']['columns'] = target['primary_key'][:]
                fk['references']['implicit_primary_key'] = True
    return {'format_version': 1, 'sources': sources, 'tables': tables,
            'summary': {'tables': len(tables), 'by_engine': dict(Counter(t['engine'] for t in tables)),
                        'columns': sum(len(t['columns']) for t in tables),
                        'described_columns': sum(bool(c['description']) for t in tables for c in t['columns'])}}


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    catalog = build()
    save_json(args.output / 'schema_extracted.json', catalog)
    print(json.dumps(catalog['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
