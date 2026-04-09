"""Query重写模块

实现基于规则的Query重写和关键词扩展。

支持需求：
- 1.1: 标准化查询并扩展相关关键词
- 1.4: 返回包含原始查询、重写后查询和扩展关键词的上下文对象
"""

import re
from typing import List, Dict, Set
from loguru import logger

from .models import QueryContext


class QueryRewriter:
    """Query重写器
    
    使用基于规则的方法进行Query标准化和关键词扩展。
    """
    
    # 关键词映射表：中文 -> 英文及同义词
    KEYWORD_MAP: Dict[str, List[str]] = {
        # 数据库相关
        "数据库": ["database", "db", "sql", "connection", "pool"],
        "连接池": ["connection pool", "pool", "database connection"],
        "事务": ["transaction", "commit", "rollback"],
        "查询": ["query", "select", "search"],
        
        # 缓存相关
        "缓存": ["cache", "redis", "memcached", "caching"],
        "redis": ["redis", "cache", "key-value store"],
        "内存": ["memory", "ram", "in-memory"],
        
        # 并发相关
        "并发": ["concurrent", "concurrency", "parallel", "async"],
        "异步": ["async", "asynchronous", "await", "coroutine"],
        "线程": ["thread", "threading", "multithread"],
        "进程": ["process", "multiprocess", "subprocess"],
        "协程": ["coroutine", "async", "await"],
        
        # API相关
        "api": ["api", "rest", "restful", "endpoint", "route"],
        "接口": ["api", "interface", "endpoint"],
        "路由": ["route", "routing", "router"],
        "中间件": ["middleware", "interceptor"],
        
        # Web相关
        "web": ["web", "http", "https", "server"],
        "服务器": ["server", "web server", "http server"],
        "客户端": ["client", "http client", "request"],
        
        # 认证授权
        "认证": ["authentication", "auth", "login"],
        "授权": ["authorization", "permission", "access control"],
        "jwt": ["jwt", "json web token", "token"],
        "token": ["token", "access token", "auth token"],
        
        # 消息队列
        "消息队列": ["message queue", "mq", "queue"],
        "队列": ["queue", "message queue"],
        "kafka": ["kafka", "message broker"],
        "rabbitmq": ["rabbitmq", "amqp", "message queue"],
        
        # 文件操作
        "文件": ["file", "filesystem", "io"],
        "读取": ["read", "load", "parse"],
        "写入": ["write", "save", "dump"],
        
        # 网络
        "网络": ["network", "socket", "tcp", "udp"],
        "请求": ["request", "http request"],
        "响应": ["response", "http response"],
        
        # 数据处理
        "解析": ["parse", "parsing", "decode"],
        "序列化": ["serialize", "serialization", "encode"],
        "json": ["json", "parse", "serialize"],
        "xml": ["xml", "parse", "etree"],
        
        # 测试
        "测试": ["test", "testing", "unittest"],
        "单元测试": ["unit test", "unittest", "pytest"],
        "mock": ["mock", "mocking", "stub"],
        
        # 日志
        "日志": ["log", "logging", "logger"],
        "监控": ["monitor", "monitoring", "metrics"],
        
        # 配置
        "配置": ["config", "configuration", "settings"],
        "环境变量": ["environment variable", "env", "environ"],
    }
    
    # 编程语言关键词
    LANGUAGE_KEYWORDS: Dict[str, str] = {
        "python": "python",
        "java": "java",
        "javascript": "javascript",
        "js": "javascript",
        "typescript": "typescript",
        "ts": "typescript",
        "go": "go",
        "golang": "go",
        "rust": "rust",
        "c++": "cpp",
        "cpp": "cpp",
        "c#": "csharp",
        "csharp": "csharp",
    }
    
    def __init__(self, use_model: bool = False):
        """
        初始化Query重写器
        
        Args:
            use_model: 是否使用模型（当前仅支持规则）
        """
        self.use_model = use_model
        
        if use_model:
            logger.warning("模型模式暂未实现，将使用规则模式")
        
        logger.info("QueryRewriter初始化完成（规则模式）")
    
    def rewrite(self, query: str) -> QueryContext:
        """
        重写Query
        
        支持需求：
        - 1.1: 标准化查询并扩展相关关键词
        - 1.4: 返回包含原始查询、重写后查询和扩展关键词的上下文对象
        
        Args:
            query: 原始用户输入
            
        Returns:
            QueryContext对象
            
        Raises:
            ValueError: 输入无效
        """
        if not query or len(query.strip()) == 0:
            raise ValueError("Query不能为空")
        
        logger.info(f"开始重写Query: {query[:100]}...")
        
        # 步骤1: 标准化
        normalized = self._normalize(query)
        
        # 步骤2: 检测语言
        language_hint = self._detect_language(normalized)
        
        # 步骤3: 扩展关键词
        expanded_keywords = self._expand_keywords(normalized)
        
        # 步骤4: 构造重写后的query
        rewritten = self._construct_rewritten_query(
            normalized,
            expanded_keywords,
            language_hint
        )
        
        # 构造上下文
        query_ctx = QueryContext(
            original_query=query,
            rewritten_query=rewritten,
            expanded_keywords=list(expanded_keywords),
            language_hint=language_hint
        )
        
        logger.info(
            f"Query重写完成: 扩展了 {len(expanded_keywords)} 个关键词, "
            f"语言提示: {language_hint or 'None'}"
        )
        
        return query_ctx
    
    def _normalize(self, query: str) -> str:
        """
        标准化Query
        
        - 去除多余空白
        - 转换为小写
        - 去除特殊字符
        
        Args:
            query: 原始查询
            
        Returns:
            标准化后的查询
        """
        # 去除多余空白
        normalized = " ".join(query.split())
        
        # 转换为小写（用于关键词匹配）
        normalized_lower = normalized.lower()
        
        return normalized_lower
    
    def _detect_language(self, query: str) -> str:
        """
        检测编程语言
        
        Args:
            query: 标准化后的查询
            
        Returns:
            检测到的语言，如果未检测到则返回None
        """
        query_lower = query.lower()
        
        for keyword, language in self.LANGUAGE_KEYWORDS.items():
            if keyword in query_lower:
                logger.debug(f"检测到语言: {language}")
                return language
        
        return None
    
    def _expand_keywords(self, query: str) -> Set[str]:
        """
        扩展关键词
        
        根据关键词映射表扩展同义词和相关词。
        
        Args:
            query: 标准化后的查询
            
        Returns:
            扩展的关键词集合
        """
        expanded = set()
        query_lower = query.lower()
        
        # 遍历关键词映射表
        for key, synonyms in self.KEYWORD_MAP.items():
            # 检查关键词是否在查询中
            if key in query_lower:
                expanded.update(synonyms)
                logger.debug(f"匹配关键词 '{key}', 扩展: {synonyms}")
        
        # 如果没有匹配到任何关键词，提取查询中的英文单词
        if not expanded:
            # 提取英文单词
            words = re.findall(r'\b[a-z]+\b', query_lower)
            expanded.update(words)
            logger.debug(f"未匹配预定义关键词，提取单词: {words}")
        
        return expanded
    
    def _construct_rewritten_query(
        self,
        normalized: str,
        expanded_keywords: Set[str],
        language_hint: str
    ) -> str:
        """
        构造重写后的query
        
        Args:
            normalized: 标准化后的查询
            expanded_keywords: 扩展的关键词
            language_hint: 语言提示
            
        Returns:
            重写后的查询字符串
        """
        # 基础查询
        rewritten = normalized
        
        # 添加语言提示
        if language_hint:
            rewritten = f"{language_hint} {rewritten}"
        
        # 添加扩展关键词（作为OR条件）
        if expanded_keywords:
            # 限制关键词数量，避免过长
            keywords_list = list(expanded_keywords)[:10]
            keywords_str = " OR ".join(keywords_list)
            rewritten = f"{rewritten} ({keywords_str})"
        
        return rewritten
    
    def add_keyword_mapping(self, key: str, synonyms: List[str]) -> None:
        """
        添加自定义关键词映射
        
        Args:
            key: 关键词
            synonyms: 同义词列表
        """
        self.KEYWORD_MAP[key.lower()] = synonyms
        logger.info(f"添加关键词映射: {key} -> {synonyms}")
    
    def get_keyword_mappings(self) -> Dict[str, List[str]]:
        """
        获取所有关键词映射
        
        Returns:
            关键词映射字典
        """
        return self.KEYWORD_MAP.copy()
