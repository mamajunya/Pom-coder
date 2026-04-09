"""RAG代码生成系统

基于检索增强生成（RAG）的高质量代码生成系统
"""

__version__ = "0.4.0"

# 基础模型总是可用（不依赖外部库）
from .models import CodeSnippet, QueryContext, RetrievalResult, GenerationConfig

# 其他模块使用延迟导入，避免在导入时就需要所有依赖
__all__ = [
    "CodeSnippet",
    "QueryContext",
    "RetrievalResult",
    "GenerationConfig",
    "RAGCodeGenerator",
    "CodeGenerator",
    "QueryRewriter",
    "MultiStageRetriever",
    "EmbeddingRetriever",
    "BM25Retriever",
    "PromptConstructor",
    "Config",
    "QueryCache",
    "MultiLevelCache",
    "CodeKnowledgeBase",
    "QualityScorer",
    "SecurityManager",
    "RateLimiter",
    "AuditLogger",
    "Reranker",
    "CodeSummarizer",
    "PerformanceMonitor",
    "HealthChecker",
]


def __getattr__(name):
    """延迟导入，只在实际使用时才导入模块"""
    if name == "RAGCodeGenerator":
        from .rag_generator import RAGCodeGenerator
        return RAGCodeGenerator
    elif name == "CodeGenerator":
        from .generator import CodeGenerator
        return CodeGenerator
    elif name == "QueryRewriter":
        from .query_rewriter import QueryRewriter
        return QueryRewriter
    elif name == "MultiStageRetriever":
        from .retrieval import MultiStageRetriever
        return MultiStageRetriever
    elif name == "EmbeddingRetriever":
        from .retrieval import EmbeddingRetriever
        return EmbeddingRetriever
    elif name == "BM25Retriever":
        from .retrieval import BM25Retriever
        return BM25Retriever
    elif name == "PromptConstructor":
        from .prompt import PromptConstructor
        return PromptConstructor
    elif name == "Config":
        from .config import Config
        return Config
    elif name == "QueryCache":
        from .cache import QueryCache
        return QueryCache
    elif name == "MultiLevelCache":
        from .cache import MultiLevelCache
        return MultiLevelCache
    elif name == "CodeKnowledgeBase":
        from .knowledge_base import CodeKnowledgeBase
        return CodeKnowledgeBase
    elif name == "QualityScorer":
        from .quality_scorer import QualityScorer
        return QualityScorer
    elif name == "SecurityManager":
        from .security import SecurityManager
        return SecurityManager
    elif name == "RateLimiter":
        from .security import RateLimiter
        return RateLimiter
    elif name == "AuditLogger":
        from .security import AuditLogger
        return AuditLogger
    elif name == "Reranker":
        from .reranker import Reranker
        return Reranker
    elif name == "CodeSummarizer":
        from .summarizer import CodeSummarizer
        return CodeSummarizer
    elif name == "PerformanceMonitor":
        from .monitoring import PerformanceMonitor
        return PerformanceMonitor
    elif name == "HealthChecker":
        from .monitoring import HealthChecker
        return HealthChecker
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
