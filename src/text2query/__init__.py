"""统一查询指令生成（赛题 8）。

模块划分：

- ``text2query.data``        数据划分与 schema 目录预处理
- ``text2query.routing``     数据库系统路由（embedding + sklearn）
- ``text2query.retrieval``   库表/知识/案例混合召回
- ``text2query.llm``         有界 LLM 规划
- ``text2query.submission``  查询指令生成与校验
"""

__version__ = "0.1.0"
