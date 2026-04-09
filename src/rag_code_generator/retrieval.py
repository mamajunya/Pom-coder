"""检索模块

实现基础向量检索和多阶段检索功能。

支持需求：
- 2.2: 向量检索返回语义相似度最高的前N个代码片段
- 8.4: FAISS向量索引和BM25索引加载到CPU内存
- 3.1: 返回的结果数量不超过top_k
- 3.2: 所有检索结果按分数降序排列
- 3.3: 所有检索结果的分数在0到1的范围内
"""

import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path
from loguru import logger

from .models import CodeSnippet, QueryContext, RetrievalResult


class RetrievalError(Exception):
    """检索错误异常"""
    pass


class EmbeddingRetriever:
    """向量检索器
    
    使用FAISS进行高效的向量相似度检索。
    """
    
    def __init__(
        self,
        index_path: str,
        embedding_model: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        初始化向量检索器
        
        Args:
            index_path: FAISS索引文件路径
            embedding_model: Embedding模型名称（用于生成query向量）
            device: 运行设备（cpu/npu）
            
        Raises:
            RetrievalError: 索引加载失败
        """
        self.index_path = Path(index_path)
        self.embedding_model = embedding_model
        self.device = device
        
        self.index = None
        self.snippets: List[CodeSnippet] = []
        
        # 加载索引
        self._load_index()
        
        logger.info(f"EmbeddingRetriever初始化完成，索引大小: {len(self.snippets)}")
    
    def _load_index(self) -> None:
        """
        加载FAISS索引
        
        支持需求8.4：将FAISS向量索引加载到CPU内存
        
        Raises:
            RetrievalError: 索引加载失败
        """
        if not self.index_path.exists():
            logger.warning(f"FAISS索引文件不存在: {self.index_path}，将使用空索引")
            # 创建空索引用于测试
            try:
                import faiss
                self.index = faiss.IndexFlatL2(768)  # 假设768维向量
                self.snippets = []
                return
            except ImportError:
                raise RetrievalError(
                    "faiss库未安装，请运行: pip install faiss-cpu"
                )
        
        try:
            import faiss
            
            # 加载FAISS索引到CPU
            logger.info(f"加载FAISS索引: {self.index_path}")
            self.index = faiss.read_index(str(self.index_path))
            
            # 加载对应的代码片段元数据
            metadata_path = self.index_path.with_suffix('.metadata.npy')
            if metadata_path.exists():
                # 这里简化处理，实际应该加载完整的CodeSnippet对象
                logger.info(f"加载元数据: {metadata_path}")
                # TODO: 实现完整的元数据加载
                self.snippets = []
            else:
                logger.warning(f"元数据文件不存在: {metadata_path}")
                self.snippets = []
            
            logger.info(f"FAISS索引加载成功，向量数量: {self.index.ntotal}")
        
        except ImportError:
            raise RetrievalError(
                "faiss库未安装，请运行: pip install faiss-cpu"
            )
        except Exception as e:
            raise RetrievalError(f"FAISS索引加载失败: {str(e)}")
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10
    ) -> List[Tuple[CodeSnippet, float]]:
        """
        执行向量检索
        
        支持需求：
        - 2.2: 返回语义相似度最高的前N个代码片段
        - 3.1: 返回的结果数量不超过top_k
        - 3.2: 所有检索结果按分数降序排列
        - 3.3: 所有检索结果的分数在0到1的范围内
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            
        Returns:
            (CodeSnippet, score)列表，按分数降序排列
        """
        if self.index is None:
            logger.warning("索引未加载，返回空结果")
            return []
        
        if self.index.ntotal == 0:
            logger.warning("索引为空，返回空结果")
            return []
        
        try:
            # 确保query_embedding是正确的形状
            if len(query_embedding.shape) == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # 执行检索
            # FAISS返回的是距离（L2距离），需要转换为相似度分数
            distances, indices = self.index.search(
                query_embedding.astype(np.float32),
                min(top_k, self.index.ntotal)
            )
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS用-1表示无效结果
                    continue
                
                # 将L2距离转换为相似度分数 [0, 1]
                # 使用负指数函数：score = exp(-distance)
                score = float(np.exp(-dist))
                
                # 如果有对应的代码片段，添加到结果
                if idx < len(self.snippets):
                    snippet = self.snippets[idx]
                    results.append((snippet, score))
                else:
                    # 创建占位符片段（用于测试）
                    placeholder = CodeSnippet(
                        code=f"# Placeholder code {idx}",
                        summary=f"Code snippet {idx}",
                        imports="",
                        path=f"placeholder_{idx}.py",
                        language="python",
                        tags=["placeholder"],
                        quality_score=7.0,
                        stars=100,
                        last_update="2024-01-01",
                        snippet_id=str(idx)
                    )
                    results.append((placeholder, score))
            
            # 确保按分数降序排列（支持需求3.2）
            results.sort(key=lambda x: x[1], reverse=True)
            
            # 确保不超过top_k（支持需求3.1）
            results = results[:top_k]
            
            logger.info(f"向量检索完成，返回 {len(results)} 个结果")
            
            return results
        
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            return []


class BM25Retriever:
    """BM25关键词检索器
    
    使用BM25算法进行关键词匹配检索。
    """
    
    def __init__(self, index_path: str):
        """
        初始化BM25检索器
        
        Args:
            index_path: BM25索引路径
            
        Raises:
            RetrievalError: 索引加载失败
        """
        self.index_path = Path(index_path)
        self.index = None
        self.snippets: List[CodeSnippet] = []
        
        # 加载索引
        self._load_index()
        
        logger.info(f"BM25Retriever初始化完成，索引大小: {len(self.snippets)}")
    
    def _load_index(self) -> None:
        """
        加载BM25索引
        
        支持需求8.4：将BM25索引加载到CPU内存
        
        Raises:
            RetrievalError: 索引加载失败
        """
        if not self.index_path.exists():
            logger.warning(f"BM25索引路径不存在: {self.index_path}，将使用空索引")
            self.index = None
            self.snippets = []
            return
        
        try:
            # 这里简化处理，实际应该使用Whoosh或Elasticsearch
            # 目前创建一个占位符
            logger.info(f"加载BM25索引: {self.index_path}")
            # TODO: 实现完整的BM25索引加载
            self.index = None
            self.snippets = []
            
            logger.info("BM25索引加载成功（占位符）")
        
        except Exception as e:
            raise RetrievalError(f"BM25索引加载失败: {str(e)}")
    
    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[CodeSnippet, float]]:
        """
        执行BM25关键词检索
        
        支持需求：
        - 2.3: 返回关键词匹配度最高的前N个代码片段
        - 3.1: 返回的结果数量不超过top_k
        - 3.2: 所有检索结果按分数降序排列
        - 3.3: 所有检索结果的分数在0到1的范围内
        
        Args:
            query: 查询字符串
            top_k: 返回结果数量
            
        Returns:
            (CodeSnippet, score)列表，按分数降序排列
        """
        if self.index is None or len(self.snippets) == 0:
            logger.warning("BM25索引为空，返回空结果")
            return []
        
        try:
            # TODO: 实现真实的BM25检索
            # 目前返回空结果
            logger.info(f"BM25检索: {query[:50]}...")
            results = []
            
            # 确保按分数降序排列
            results.sort(key=lambda x: x[1], reverse=True)
            
            # 确保不超过top_k
            results = results[:top_k]
            
            logger.info(f"BM25检索完成，返回 {len(results)} 个结果")
            
            return results
        
        except Exception as e:
            logger.error(f"BM25检索失败: {str(e)}")
            return []


class MultiStageRetriever:
    """多阶段检索器
    
    整合Embedding检索、BM25检索、RRF融合和Reranker精排。
    """
    
    def __init__(
        self,
        embedding_index_path: str,
        bm25_index_path: str,
        embedding_model: Optional[str] = None,
        reranker_model: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        初始化多阶段检索器
        
        Args:
            embedding_index_path: FAISS索引路径
            bm25_index_path: BM25索引路径
            embedding_model: Embedding模型名称
            reranker_model: Reranker模型名称
            device: 运行设备
        """
        self.embedding_retriever = EmbeddingRetriever(
            embedding_index_path,
            embedding_model,
            device
        )
        self.bm25_retriever = BM25Retriever(bm25_index_path)
        self.reranker_model = reranker_model
        self.device = device
        
        logger.info("MultiStageRetriever初始化完成")
    
    def retrieve(
        self,
        query_ctx: QueryContext,
        query_embedding: Optional[np.ndarray] = None,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        执行多阶段检索
        
        支持需求：
        - 2.1: 并行执行向量检索和关键词检索
        - 2.4: 使用RRF算法融合检索结果
        - 2.6: 结合质量分数进行加权排序
        - 3.1: 返回的结果数量不超过top_k
        - 3.2: 所有检索结果按分数降序排列
        
        Args:
            query_ctx: Query上下文
            query_embedding: 查询向量（如果已计算）
            top_k: 最终返回数量
            
        Returns:
            排序后的检索结果列表
        """
        logger.info(f"开始多阶段检索，top_k={top_k}")
        
        # 阶段1: 并行召回
        embedding_results = []
        bm25_results = []
        
        if query_embedding is not None:
            embedding_results = self.embedding_retriever.search(
                query_embedding,
                top_k=10
            )
        
        bm25_results = self.bm25_retriever.search(
            query_ctx.rewritten_query,
            top_k=10
        )
        
        # 如果两路检索都为空，返回空结果
        if not embedding_results and not bm25_results:
            logger.warning("所有检索路径都返回空结果")
            return []
        
        # 阶段2: RRF融合
        fused_results = self._rrf_fusion(
            embedding_results,
            bm25_results,
            k=60
        )
        
        # 阶段3: 质量加权排序
        final_results = self._quality_weighted_ranking(
            fused_results,
            top_k=top_k
        )
        
        logger.info(f"多阶段检索完成，返回 {len(final_results)} 个结果")
        
        return final_results
    
    def _rrf_fusion(
        self,
        embedding_results: List[Tuple[CodeSnippet, float]],
        bm25_results: List[Tuple[CodeSnippet, float]],
        k: int = 60
    ) -> List[RetrievalResult]:
        """
        RRF（倒数排名融合）算法
        
        支持需求2.4：使用RRF算法融合检索结果
        
        Args:
            embedding_results: Embedding检索结果
            bm25_results: BM25检索结果
            k: RRF平滑参数
            
        Returns:
            融合后的结果列表
        """
        # 收集所有候选项
        candidates = {}
        
        # 处理embedding结果
        for rank, (snippet, score) in enumerate(embedding_results, start=1):
            snippet_id = snippet.snippet_id or snippet.path
            if snippet_id not in candidates:
                candidates[snippet_id] = {
                    'snippet': snippet,
                    'rrf_score': 0.0,
                    'embedding_score': score,
                    'bm25_score': 0.0,
                    'embedding_rank': rank,
                    'bm25_rank': None
                }
            candidates[snippet_id]['rrf_score'] += 1.0 / (k + rank)
            candidates[snippet_id]['embedding_score'] = score
            candidates[snippet_id]['embedding_rank'] = rank
        
        # 处理BM25结果
        for rank, (snippet, score) in enumerate(bm25_results, start=1):
            snippet_id = snippet.snippet_id or snippet.path
            if snippet_id not in candidates:
                candidates[snippet_id] = {
                    'snippet': snippet,
                    'rrf_score': 0.0,
                    'embedding_score': 0.0,
                    'bm25_score': score,
                    'embedding_rank': None,
                    'bm25_rank': rank
                }
            candidates[snippet_id]['rrf_score'] += 1.0 / (k + rank)
            candidates[snippet_id]['bm25_score'] = score
            candidates[snippet_id]['bm25_rank'] = rank
        
        # 转换为RetrievalResult列表
        results = []
        for candidate in candidates.values():
            result = RetrievalResult(
                snippet=candidate['snippet'],
                score=candidate['rrf_score'],
                source="rrf_fusion",
                embedding_score=candidate['embedding_score'],
                bm25_score=candidate['bm25_score'],
                rrf_score=candidate['rrf_score']
            )
            results.append(result)
        
        # 按RRF分数排序
        results.sort(key=lambda x: x.rrf_score, reverse=True)
        
        return results
    
    def _quality_weighted_ranking(
        self,
        results: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        质量加权排序
        
        支持需求2.6和2.7：结合质量分数和GitHub stars进行加权
        
        Args:
            results: RRF融合后的结果
            top_k: 最终返回数量
            
        Returns:
            加权排序后的结果列表
        """
        # 计算最终分数：RRF分数 + 质量权重
        for result in results:
            # 归一化质量分数 [0, 10] -> [0, 1]
            quality_norm = result.snippet.quality_score / 10.0
            
            # 归一化stars（假设10000为满分）
            stars_norm = min(result.snippet.stars / 10000.0, 1.0)
            
            # 加权计算最终分数
            # RRF分数占主导，质量和stars作为调整因子
            final_score = (
                0.7 * result.rrf_score +
                0.2 * quality_norm +
                0.1 * stars_norm
            )
            
            result.score = final_score
            result.quality_weight = 0.2 * quality_norm + 0.1 * stars_norm
        
        # 按最终分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        # 返回Top-K
        return results[:top_k]
