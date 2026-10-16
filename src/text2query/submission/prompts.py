"""所有查询生成入口共用的统一口径原文。"""

from pathlib import Path

from ..config import settings

QUERY_RULES_PATH = settings.path("data/赛题8/问题描述与查询指令口径规则.txt")
QUERY_RULES_HEADER = "\n本次问题的统一口径如下，优先于训练案例及不明确的知识描述：\n"


def with_query_rules(system: str, rules_path: Path | None = None) -> str:
    """保留各入口原有输出协议，追加同一版本的完整规则。"""
    return system + QUERY_RULES_HEADER + (rules_path or QUERY_RULES_PATH).read_text(encoding="utf-8")
