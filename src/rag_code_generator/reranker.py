"""
Reranker模块 - 使用bge-reranker-large进行检索结果精排

实现功能：
1. 加载bge-reranker-large模型
2. 批量推理接口
3. 分数归一化和加权
4. 显存控制（小批量处理）
"""

from typing import List, Tuple, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from .models import RetrievalResult


class Reranker:
    """检索结果重排序器"""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-large",
        device: str = "cuda:0",
        batch_size: int = 8,
        max_length: int = 512
    ):
        """
        初始化Reranker
        
        Args:
            model_name: 模型名称或路径
            device: 设备（cuda:0, cpu等）
            batch_size: 批量推理大小（控制显存）
            max_length: 最大序列长度
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载Reranker模型"""
        try:
            print(f"Loading reranker model: {self.model_name}")
            
            # 加载tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # 加载模型
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if "cuda" in self.device else torch.float32
            )
            
            # 移动到指定设备
            if torch.cuda.is_available() and "cuda" in self.device:
                self.model = self.model.to(self.device)
            else:
                self.model = self.model.to("cpu")
                self.device = "cpu"
            
            self.model.eval()
            print(f"Reranker model loaded on {self.device}")
            
        except Exception as e:
            print(f"Failed to load reranker model: {e}")
            print("Reranker will be disabled")
            self.model = None
            self.tokenizer = None
    
    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        对检索结果进行重排序
        
        Args:
            query: 用户查询
            results: 检索结果列表
            top_k: 返回Top-K结果
        
        Returns:
            重排序后的结果列表
        """
        if not self.model or not self.tokenizer or not results:
            return results[:top_k]
        
        try:
            # 准备输入对
            pairs = [(query, result.snippet.code) for result in results]
            
            # 批量计算相关性分数
            scores = self._compute_scores_batch(pairs)
            
            # 归一化分数到[0, 1]
            if len(scores) > 0:
                scores = self._normalize_scores(scores)
            
            # 更新结果分数（加权融合）
            reranked_results = []
            for result, rerank_score in zip(results, scores):
                # 融合原始分数和rerank分数（权重0.3:0.7）
                new_score = 0.3 * result.score + 0.7 * rerank_score
                
                # 创建新的结果对象
                new_result = RetrievalResult(
                    snippet=result.snippet,
                    score=new_score,
                    source=result.source
                )
                reranked_results.append(new_result)
            
            # 按新分数排序
            reranked_results.sort(key=lambda x: x.score, reverse=True)
            
            return reranked_results[:top_k]
            
        except Exception as e:
            print(f"Reranking failed: {e}")
            return results[:top_k]
    
    def _compute_scores_batch(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """
        批量计算相关性分数
        
        Args:
            pairs: (query, document)对列表
        
        Returns:
            分数列表
        """
        all_scores = []
        
        # 分批处理
        for i in range(0, len(pairs), self.batch_size):
            batch_pairs = pairs[i:i + self.batch_size]
            
            # Tokenize
            inputs = self.tokenizer(
                batch_pairs,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt"
            )
            
            # 移动到设备
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 推理
            with torch.no_grad():
                outputs = self.model(**inputs)
                scores = outputs.logits.squeeze(-1)
                
                # 转换为Python列表
                if scores.dim() == 0:
                    scores = [scores.item()]
                else:
                    scores = scores.cpu().tolist()
                
                all_scores.extend(scores)
        
        return all_scores
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        归一化分数到[0, 1]范围
        
        Args:
            scores: 原始分数列表
        
        Returns:
            归一化后的分数列表
        """
        if not scores:
            return []
        
        scores_array = np.array(scores)
        
        # Min-Max归一化
        min_score = scores_array.min()
        max_score = scores_array.max()
        
        if max_score - min_score < 1e-6:
            # 所有分数相同
            return [0.5] * len(scores)
        
        normalized = (scores_array - min_score) / (max_score - min_score)
        return normalized.tolist()
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "loaded": self.model is not None
        }
