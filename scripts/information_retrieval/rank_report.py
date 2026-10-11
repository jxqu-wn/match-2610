"""Rank reference objects by original-question RRF, separately from context positions."""
from collections import Counter
from statistics import mean

from business_routing import database_id
from token_report import distribution


def relevance_ranks(hits, tables):
    # Hits are already in RRF order. Database relevance uses its highest
    # scoring table, avoiding an explicit bonus for having more tables.
    table_ranks = {hit['table_ids'][0]: n for n, hit in enumerate(hits, 1)}
    scores = {}
    for hit in hits:
        key = database_id(tables[hit['table_ids'][0]])
        scores[key] = max(scores.get(key, float('-inf')), hit['score'])
    ordered = sorted(scores, key=lambda key: (-scores[key], key))
    return table_ranks, {key: n for n, key in enumerate(ordered, 1)}


def rank_summary(per_question):
    values = [v for ranks in per_question for v in ranks.values() if v is not None]
    missing = sum(v is None for ranks in per_question for v in ranks.values())
    bins = {'1': 0, '2-3': 0, '4-6': 0, '7-8': 0, '9-12': 0, '13-20': 0, '21+': 0, 'unranked': missing}
    for value in values:
        label = next(label for label, lower, upper in [('1', 1, 1), ('2-3', 2, 3), ('4-6', 4, 6),
                      ('7-8', 7, 8), ('9-12', 9, 12), ('13-20', 13, 20), ('21+', 21, float('inf'))]
                     if lower <= value <= upper)
        bins[label] += 1
    total = len(values) + missing
    return {**distribution(values), 'reference_occurrences': total, 'unranked_occurrences': missing,
            'mean_note': 'Mean/quantiles computed on ranked references; unranked shown separately.',
            'mean_question_average_rank': mean(mean([v for v in ranks.values() if v is not None])
                                               for ranks in per_question if any(v is not None for v in ranks.values())) if values else None,
            'counts_by_rank': dict(sorted(Counter(values).items())), 'bins': bins,
            'top_k': {str(k): {'reference_hits': sum(v <= k for v in values),
                               'reference_rate': sum(v <= k for v in values) / total if total else None,
                               'complete_questions': sum(all(v is not None and v <= k for v in ranks.values()) for ranks in per_question),
                               'complete_question_rate': sum(all(v is not None and v <= k for v in ranks.values()) for ranks in per_question) / len(per_question) if per_question else None}
                      for k in (1, 3, 6, 8, 12, 20)}}
