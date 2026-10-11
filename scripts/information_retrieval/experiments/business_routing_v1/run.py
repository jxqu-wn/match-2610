"""CLI: build-index, retrieve, plan, evaluate."""
import argparse
import json
import os
from pathlib import Path

from index import DEFAULT_INDEX, ROOT, RetrievalIndex, SourceResolver, make_encoder, write_json
from context import ContextBuilder, Budget
from planner import Planner, DeepSeekClient, SYSTEM
from business_routing import BusinessRouter


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['build-index', 'retrieve', 'plan', 'evaluate'])
    p.add_argument('--index', type=Path, default=DEFAULT_INDEX)
    p.add_argument('--keyword-only', action='store_true')
    p.add_argument('--device', default='cpu', choices=['cpu', 'cuda', 'auto'])
    p.add_argument('--dtype', default='auto', choices=['auto', 'float32', 'float16', 'bfloat16'])
    p.add_argument('--batch-size', type=int, default=8)
    p.add_argument('--max-length', type=int, default=512)
    p.add_argument('--model', type=Path)
    p.add_argument('--question')
    p.add_argument('--question-id', type=int)
    p.add_argument('--engines', nargs='+', choices=['SQLite', 'MYSQL', 'POSTGRESQL', 'Elasticsearch'])
    p.add_argument('--business-databases', nargs='+', help='Explicit ENGINE:business database IDs for offline retrieve only')
    p.add_argument('--classification-json', type=Path, help='JSON with databases/engines array, or db/db1/db2 fields')
    p.add_argument('--budget-json', type=Path, help='Budget dataclass overrides as JSON')
    p.add_argument('--output', type=Path)
    p.add_argument('--llm-model', default='deepseek-flash')
    p.add_argument('--validation', type=Path, default=ROOT / 'data/赛题8/splits/validation.json')
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()
    budget = Budget(**json.loads(args.budget_json.read_text())) if args.budget_json else Budget()
    encoder = None if args.keyword_only else make_encoder(args.model, args.device, args.dtype, args.batch_size, args.max_length)
    if args.command == 'build-index':
        index = RetrievalIndex.build(args.index, encoder)
        result = {'index': str(args.index), 'documents': len(index.documents)}
    else:
        index = RetrievalIndex.load(args.index, encoder)
        if args.command == 'evaluate':
            from evaluate import evaluate
            result = evaluate(index, args.validation, args.limit)
        else:
            engines = args.engines
            if args.classification_json:
                row = json.loads(args.classification_json.read_text())
                engines = row.get('databases', row.get('engines'))
                if engines is None:
                    from index import engine_set
                    engines = engine_set(row)
            if not args.question or not engines:
                p.error('--question and --engines/--classification-json are required')
            engines = sorted(set(engines))
            allowed = {t['engine'] for t in index.tables.values()}
            if not set(engines) <= allowed:
                p.error('Unsupported engine in classification')
            if args.command == 'retrieve':
                builder = ContextBuilder(index, budget)
                if args.business_databases:
                    result, _ = builder.fit(builder.assemble(args.question, engines, args.question_id,
                                                           business_databases=args.business_databases), SYSTEM)
                else:
                    router = BusinessRouter(builder, None)
                    result, _, _ = router.fit(router.catalog(args.question, engines, args.question_id))
                    result['status'] = 'business_selection_required'
            else:
                if args.business_databases:
                    p.error('--business-databases is for offline retrieve; plan selects business databases with the LLM')
                client = DeepSeekClient(os.environ.get('DEEPSEEK_API_KEY'), args.llm_model, retries=budget.transport_retries)
                result = Planner(index, client, budget).run(args.question, engines, args.question_id)
    if args.output:
        write_json(args.output, result)
        print(json.dumps({'output': str(args.output), 'status': result.get('result', {}).get('status')}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
