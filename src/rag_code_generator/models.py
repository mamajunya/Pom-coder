"""核心数据模型"""

from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class CodeSnippet:
    """代码片段数据结构"""
    # 核心内容
    code: str
    summary: str
    
    # 上下文信息
    imports: str
    path: str
    language: str
    
    # 元数据
    tags: List[str]
    quality_score: float
    stars: int
    last_update: str
    
    # 检索相关
    embedding: Optional[List[float]] = None
    snippet_id: Optional[str] = None
    
    # 统计信息
    lines_of_code: int = 0
    complexity: float = 0.0


@dataclass
class QueryContext:
    """Query处理上下文"""
    original_query: str
    rewritten_query: str
    expanded_keywords: List[str]
    language_hint: Optional[str] = None
    intent: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class RetrievalResult:
    """单个检索结果"""
    snippet: CodeSnippet
    score: float
    source: str  # "embedding", "bm25", "multi_stage"
    
    # 详细分数
    embedding_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0
    quality_weight: float = 0.0


@dataclass
class GenerationConfig:
    """代码生成配置"""
    temperature: float = 0.2
    max_new_tokens: int = 512
    top_p: float = 0.95
    top_k: int = 50
    do_sample: bool = True
    repetition_penalty: float = 1.1
    num_return_sequences: int = 1
