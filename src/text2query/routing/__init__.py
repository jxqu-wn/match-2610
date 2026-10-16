"""数据库系统路由：语义向量 + scikit-learn 分类器。"""

from .classifier import CharacterTfidfBaseline, RoutingClassifier, label
from .embedding import EmbeddingService
from .multilabel import SemanticMultiLabelRouter

__all__ = ["EmbeddingService", "RoutingClassifier", "CharacterTfidfBaseline", "SemanticMultiLabelRouter", "label"]
