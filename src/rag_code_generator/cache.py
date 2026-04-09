"""缓存系统模块

实现查询结果缓存，提升响应速度。

支持需求：
- 6.1: 缓存功能启用且查询在缓存中存在时直接返回缓存结果
- 6.2: 查询结果生成完成后存入缓存
- 6.3: 缓存条目超过有效期时自动失效
- 6.4: 缓存大小超过最大值时使用LRU策略淘汰
"""

import time
import hashlib
from typing import Optional, Dict, Any, List
from collections import OrderedDict
from loguru import logger


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, value: Any, ttl: int):
        """
        初始化缓存条目
        
        Args:
            value: 缓存的值
            ttl: 生存时间（秒）
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_access = self.created_at
    
    def is_expired(self) -> bool:
        """
        检查是否过期
        
        支持需求6.3：缓存条目超过有效期时自动失效
        
        Returns:
            是否过期
        """
        if self.ttl <= 0:  # ttl=0表示永不过期
            return False
        return (time.time() - self.created_at) > self.ttl
    
    def access(self) -> Any:
        """
        访问缓存条目
        
        Returns:
            缓存的值
        """
        self.access_count += 1
        self.last_access = time.time()
        return self.value


class QueryCache:
    """查询缓存系统
    
    使用LRU（最近最少使用）策略管理缓存。
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl: int = 3600,
        backend: str = "memory"
    ):
        """
        初始化缓存系统
        
        Args:
            max_size: 最大缓存条目数
            ttl: 默认生存时间（秒），0表示永不过期
            backend: 缓存后端（memory/redis）
        """
        self.max_size = max_size
        self.default_ttl = ttl
        self.backend = backend
        
        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # 统计信息
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        logger.info(
            f"QueryCache初始化: max_size={max_size}, "
            f"ttl={ttl}s, backend={backend}"
        )
    
    def _generate_key(self, query: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            query: 查询字符串
            **kwargs: 其他参数（如temperature, top_k等）
            
        Returns:
            缓存键
        """
        # 将查询和参数组合成字符串
        key_parts = [query]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        
        key_str = "|".join(key_parts)
        
        # 使用MD5生成固定长度的键
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(
        self,
        query: str,
        **kwargs
    ) -> Optional[Any]:
        """
        获取缓存结果
        
        支持需求6.1：缓存功能启用且查询在缓存中存在时直接返回缓存结果
        
        Args:
            query: 查询字符串
            **kwargs: 其他参数
            
        Returns:
            缓存的值，如果不存在或已过期则返回None
        """
        key = self._generate_key(query, **kwargs)
        
        if key not in self._cache:
            self.misses += 1
            logger.debug(f"缓存未命中: {query[:50]}...")
            return None
        
        entry = self._cache[key]
        
        # 检查是否过期
        if entry.is_expired():
            logger.debug(f"缓存已过期: {query[:50]}...")
            del self._cache[key]
            self.misses += 1
            return None
        
        # 移动到末尾（LRU）
        self._cache.move_to_end(key)
        
        self.hits += 1
        logger.debug(
            f"缓存命中: {query[:50]}... "
            f"(访问次数: {entry.access_count + 1})"
        )
        
        return entry.access()
    
    def set(
        self,
        query: str,
        value: Any,
        ttl: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        设置缓存
        
        支持需求：
        - 6.2: 查询结果生成完成后存入缓存
        - 6.4: 缓存大小超过最大值时使用LRU策略淘汰
        
        Args:
            query: 查询字符串
            value: 要缓存的值
            ttl: 生存时间（秒），None表示使用默认值
            **kwargs: 其他参数
            
        Returns:
            是否成功
        """
        key = self._generate_key(query, **kwargs)
        
        # 使用默认TTL
        if ttl is None:
            ttl = self.default_ttl
        
        # 检查是否需要淘汰（支持需求6.4）
        if len(self._cache) >= self.max_size and key not in self._cache:
            # 淘汰最旧的条目（LRU）
            evicted_key, evicted_entry = self._cache.popitem(last=False)
            self.evictions += 1
            logger.debug(
                f"LRU淘汰: 访问次数={evicted_entry.access_count}, "
                f"存活时间={time.time() - evicted_entry.created_at:.1f}s"
            )
        
        # 添加或更新缓存
        entry = CacheEntry(value, ttl)
        self._cache[key] = entry
        self._cache.move_to_end(key)
        
        logger.debug(
            f"缓存已设置: {query[:50]}... "
            f"(TTL={ttl}s, 缓存大小={len(self._cache)})"
        )
        
        return True
    
    def invalidate(self, query: str, **kwargs) -> bool:
        """
        失效指定缓存
        
        Args:
            query: 查询字符串
            **kwargs: 其他参数
            
        Returns:
            是否成功
        """
        key = self._generate_key(query, **kwargs)
        
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"缓存已失效: {query[:50]}...")
            return True
        
        return False
    
    def clear(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            是否成功
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"缓存已清空: {count} 个条目")
        return True
    
    def cleanup_expired(self) -> int:
        """
        清理所有过期的缓存条目
        
        Returns:
            清理的条目数量
        """
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"清理过期缓存: {len(expired_keys)} 个条目")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'evictions': self.evictions,
            'total_requests': total_requests
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取详细的缓存信息
        
        Returns:
            详细信息字典
        """
        stats = self.get_stats()
        
        # 计算平均访问次数
        if self._cache:
            avg_access = sum(e.access_count for e in self._cache.values()) / len(self._cache)
        else:
            avg_access = 0
        
        # 计算平均存活时间
        if self._cache:
            current_time = time.time()
            avg_age = sum(current_time - e.created_at for e in self._cache.values()) / len(self._cache)
        else:
            avg_age = 0
        
        stats.update({
            'avg_access_count': avg_access,
            'avg_age_seconds': avg_age,
            'backend': self.backend,
            'default_ttl': self.default_ttl
        })
        
        return stats
    
    def __len__(self) -> int:
        """返回缓存大小"""
        return len(self._cache)
    
    def __contains__(self, query: str) -> bool:
        """检查查询是否在缓存中"""
        key = self._generate_key(query)
        return key in self._cache


class MultiLevelCache:
    """多层缓存系统
    
    支持三层缓存：
    - L1: Query结果缓存
    - L2: Embedding缓存
    - L3: 检索结果缓存
    """
    
    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_ttl: int = 3600,
        l2_max_size: int = 5000,
        l2_ttl: int = 7200,
        l3_max_size: int = 2000,
        l3_ttl: int = 3600
    ):
        """
        初始化多层缓存
        
        Args:
            l1_max_size: L1缓存最大大小
            l1_ttl: L1缓存TTL
            l2_max_size: L2缓存最大大小
            l2_ttl: L2缓存TTL
            l3_max_size: L3缓存最大大小
            l3_ttl: L3缓存TTL
        """
        self.l1_cache = QueryCache(l1_max_size, l1_ttl)  # Query结果
        self.l2_cache = QueryCache(l2_max_size, l2_ttl)  # Embedding
        self.l3_cache = QueryCache(l3_max_size, l3_ttl)  # 检索结果
        
        logger.info("MultiLevelCache初始化完成")
    
    def get_query_result(self, query: str, **kwargs) -> Optional[Any]:
        """获取L1缓存（Query结果）"""
        return self.l1_cache.get(query, **kwargs)
    
    def set_query_result(self, query: str, value: Any, **kwargs) -> bool:
        """设置L1缓存（Query结果）"""
        return self.l1_cache.set(query, value, **kwargs)
    
    def get_embedding(self, text: str) -> Optional[Any]:
        """获取L2缓存（Embedding）"""
        return self.l2_cache.get(text)
    
    def set_embedding(self, text: str, embedding: Any) -> bool:
        """设置L2缓存（Embedding）"""
        return self.l2_cache.set(text, embedding)
    
    def get_retrieval_result(self, query: str, **kwargs) -> Optional[Any]:
        """获取L3缓存（检索结果）"""
        return self.l3_cache.get(query, **kwargs)
    
    def set_retrieval_result(self, query: str, results: Any, **kwargs) -> bool:
        """设置L3缓存（检索结果）"""
        return self.l3_cache.set(query, results, **kwargs)
    
    def clear_all(self) -> None:
        """清空所有缓存"""
        self.l1_cache.clear()
        self.l2_cache.clear()
        self.l3_cache.clear()
        logger.info("所有缓存已清空")
    
    def cleanup_all_expired(self) -> int:
        """清理所有层的过期缓存"""
        total = 0
        total += self.l1_cache.cleanup_expired()
        total += self.l2_cache.cleanup_expired()
        total += self.l3_cache.cleanup_expired()
        return total
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有层的统计信息"""
        return {
            'l1_query_results': self.l1_cache.get_stats(),
            'l2_embeddings': self.l2_cache.get_stats(),
            'l3_retrieval_results': self.l3_cache.get_stats()
        }
