"""Original training output conventions, separate from filters and formulas."""

from __future__ import annotations

import sqlglot
from sqlglot import exp

from ..retrieval.sql_parser import DIALECTS


def projection_usage(steps: list[dict]) -> list[dict]:
    output = []
    for step in steps:
        dialect = DIALECTS.get(step["engine"])
        if dialect is None:
            continue
        try:
            root = sqlglot.parse_one(step["query"], read=dialect)
        except sqlglot.errors.SqlglotError:
            continue
        if not isinstance(root, exp.Select):
            continue
        dimensions = []
        for expression in root.expressions:
            value = expression.this if isinstance(expression, exp.Alias) else expression
            if any(value.find_all(exp.AggFunc, exp.Window, exp.Subquery, exp.Add, exp.Sub, exp.Mul, exp.Div)):
                continue
            if isinstance(value, (exp.Column, exp.Star)) or value.find(exp.Column):
                dimensions.append(expression.sql(dialect=dialect))
        grouping = root.args.get("group")
        ordering = root.args.get("order")
        output.append({"engine": step["engine"], "nonaggregate_output_dimensions": dimensions,
                       "group_by": [value.sql(dialect=dialect) for value in grouping.expressions] if grouping else [],
                       "order_by": [value.sql(dialect=dialect) for value in ordering.expressions
                                    if isinstance(value.this, (exp.Column, exp.Literal))] if ordering else [],
                       "status": "original_training_projection_unverified; no copied_filters_or_metric_formulas"})
    return output
