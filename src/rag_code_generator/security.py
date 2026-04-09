"""安全与访问控制模块

实现输入验证、速率限制和审计日志。

支持需求：
- 10.1: 对所有用户输入进行验证和清理
- 10.2: 扫描生成的代码中的危险模式
- 10.3: 实施速率限制
- 10.4: 60秒内超过10个请求时拒绝
- 10.5: 记录所有查询和生成结果的审计日志
"""

import re
import time
import json
from typing import Optional, List, Dict, Any
from collections import deque
from pathlib import Path
from loguru import logger


class SecurityError(Exception):
    """安全错误异常"""
    pass


class RateLimitError(SecurityError):
    """速率限制错误"""
    pass


class SecurityValidator:
    """安全验证器
    
    验证和清理用户输入，检测危险模式。
    """
    
    # 危险字符模式
    DANGEROUS_CHARS = ['<', '>', '"', "'", ';', '&', '|', '`', '$']
    
    # 危险代码模式
    DANGEROUS_PATTERNS = [
        r'__import__',
        r'eval\s*\(',
        r'exec\s*\(',
        r'compile\s*\(',
        r'os\.system',
        r'subprocess\.',
        r'open\s*\(',
        r'file\s*\(',
        r'input\s*\(',
        r'raw_input\s*\(',
    ]
    
    # SQL注入模式
    SQL_INJECTION_PATTERNS = [
        r';\s*DROP\s+TABLE',
        r';\s*DELETE\s+FROM',
        r';\s*UPDATE\s+.*\s+SET',
        r'UNION\s+SELECT',
        r'OR\s+1\s*=\s*1',
        r'OR\s+\'1\'\s*=\s*\'1\'',
    ]
    
    def __init__(self):
        """初始化安全验证器"""
        logger.info("SecurityValidator初始化完成")
    
    def sanitize_query(self, query: str) -> str:
        """
        清理用户查询
        
        支持需求10.1：对所有用户输入进行验证和清理
        
        Args:
            query: 用户输入
            
        Returns:
            清理后的查询
            
        Raises:
            SecurityError: 输入包含危险内容
        """
        if not query or len(query.strip()) == 0:
            raise SecurityError("查询不能为空")
        
        # 检查长度
        if len(query) > 10000:
            raise SecurityError("查询过长（最大10000字符）")
        
        # 移除危险字符
        cleaned = query
        for char in self.DANGEROUS_CHARS:
            if char in cleaned:
                logger.warning(f"移除危险字符: {char}")
                cleaned = cleaned.replace(char, '')
        
        # 检查SQL注入
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                raise SecurityError(f"检测到可能的SQL注入: {pattern}")
        
        return cleaned.strip()
    
    def validate_query(self, query: str) -> bool:
        """
        验证查询是否安全
        
        Args:
            query: 用户查询
            
        Returns:
            是否安全
        """
        try:
            self.sanitize_query(query)
            return True
        except SecurityError:
            return False
    
    def scan_generated_code(self, code: str) -> List[str]:
        """
        扫描生成的代码中的危险模式
        
        支持需求10.2：扫描生成的代码中的危险模式
        
        Args:
            code: 生成的代码
            
        Returns:
            发现的危险模式列表
        """
        warnings = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                warnings.append(f"发现潜在危险模式: {pattern}")
                logger.warning(f"代码中发现危险模式: {pattern}")
        
        return warnings
    
    def add_security_warnings(self, code: str, warnings: List[str]) -> str:
        """
        在代码中添加安全警告注释
        
        Args:
            code: 原始代码
            warnings: 警告列表
            
        Returns:
            添加警告后的代码
        """
        if not warnings:
            return code
        
        warning_comment = "# " + "=" * 60 + "\n"
        warning_comment += "# 安全警告：此代码包含潜在危险操作\n"
        for warning in warnings:
            warning_comment += f"# - {warning}\n"
        warning_comment += "# 请仔细审查后再使用！\n"
        warning_comment += "# " + "=" * 60 + "\n\n"
        
        return warning_comment + code


class RateLimiter:
    """速率限制器
    
    限制用户请求频率，防止滥用。
    """
    
    def __init__(
        self,
        max_requests: int = 10,
        time_window: int = 60,
        enabled: bool = True
    ):
        """
        初始化速率限制器
        
        支持需求10.3和10.4：实施速率限制
        
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
            enabled: 是否启用
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.enabled = enabled
        
        # 用户请求记录 {user_id: deque of timestamps}
        self._requests: Dict[str, deque] = {}
        
        logger.info(
            f"RateLimiter初始化: {max_requests}次/{time_window}秒, "
            f"启用={enabled}"
        )
    
    def check_rate_limit(self, user_id: str = "default") -> bool:
        """
        检查是否超过速率限制
        
        Args:
            user_id: 用户标识
            
        Returns:
            是否允许请求
            
        Raises:
            RateLimitError: 超过速率限制
        """
        if not self.enabled:
            return True
        
        current_time = time.time()
        
        # 初始化用户记录
        if user_id not in self._requests:
            self._requests[user_id] = deque()
        
        user_requests = self._requests[user_id]
        
        # 清理过期的请求记录
        while user_requests and current_time - user_requests[0] > self.time_window:
            user_requests.popleft()
        
        # 检查是否超限
        if len(user_requests) >= self.max_requests:
            logger.warning(
                f"用户 {user_id} 超过速率限制: "
                f"{len(user_requests)}/{self.max_requests} 在 {self.time_window}秒内"
            )
            raise RateLimitError(
                f"请求过于频繁，请在{self.time_window}秒后重试"
            )
        
        # 记录本次请求
        user_requests.append(current_time)
        
        return True
    
    def get_remaining_requests(self, user_id: str = "default") -> int:
        """
        获取剩余可用请求数
        
        Args:
            user_id: 用户标识
            
        Returns:
            剩余请求数
        """
        if not self.enabled:
            return self.max_requests
        
        if user_id not in self._requests:
            return self.max_requests
        
        current_time = time.time()
        user_requests = self._requests[user_id]
        
        # 清理过期记录
        while user_requests and current_time - user_requests[0] > self.time_window:
            user_requests.popleft()
        
        return max(0, self.max_requests - len(user_requests))
    
    def reset_user(self, user_id: str) -> None:
        """
        重置用户的速率限制
        
        Args:
            user_id: 用户标识
        """
        if user_id in self._requests:
            self._requests[user_id].clear()
            logger.info(f"用户 {user_id} 的速率限制已重置")


class AuditLogger:
    """审计日志记录器
    
    记录所有查询和生成结果。
    """
    
    def __init__(
        self,
        log_dir: str = "./logs/audit",
        enabled: bool = True,
        max_log_size_mb: int = 100
    ):
        """
        初始化审计日志记录器
        
        支持需求10.5：记录所有查询和生成结果的审计日志
        
        Args:
            log_dir: 日志目录
            enabled: 是否启用
            max_log_size_mb: 单个日志文件最大大小（MB）
        """
        self.log_dir = Path(log_dir)
        self.enabled = enabled
        self.max_log_size = max_log_size_mb * 1024 * 1024
        
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"AuditLogger初始化: {self.log_dir}")
    
    def log_query(
        self,
        user_id: str,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录查询
        
        Args:
            user_id: 用户标识
            query: 查询内容
            metadata: 额外元数据
        """
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': time.time(),
            'type': 'query',
            'user_id': user_id,
            'query': query[:500],  # 限制长度
            'metadata': metadata or {}
        }
        
        self._write_log(log_entry)
    
    def log_generation(
        self,
        user_id: str,
        query: str,
        generated_code: str,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录生成结果
        
        Args:
            user_id: 用户标识
            query: 查询内容
            generated_code: 生成的代码
            success: 是否成功
            error: 错误信息
            metadata: 额外元数据
        """
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': time.time(),
            'type': 'generation',
            'user_id': user_id,
            'query': query[:500],
            'code_length': len(generated_code),
            'success': success,
            'error': error,
            'metadata': metadata or {}
        }
        
        self._write_log(log_entry)
    
    def _write_log(self, log_entry: Dict[str, Any]) -> None:
        """
        写入日志文件
        
        Args:
            log_entry: 日志条目
        """
        try:
            # 生成日志文件名（按日期）
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"audit_{date_str}.jsonl"
            
            # 检查文件大小，如果超过限制则轮转
            if log_file.exists() and log_file.stat().st_size > self.max_log_size:
                # 重命名旧文件
                timestamp = int(time.time())
                old_file = self.log_dir / f"audit_{date_str}_{timestamp}.jsonl"
                log_file.rename(old_file)
                logger.info(f"日志文件轮转: {old_file}")
            
            # 写入日志
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        except Exception as e:
            logger.error(f"写入审计日志失败: {str(e)}")
    
    def get_user_logs(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户的审计日志
        
        Args:
            user_id: 用户标识
            limit: 返回数量限制
            
        Returns:
            日志条目列表
        """
        if not self.enabled:
            return []
        
        logs = []
        
        try:
            # 读取所有日志文件
            for log_file in sorted(self.log_dir.glob("audit_*.jsonl"), reverse=True):
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get('user_id') == user_id:
                                logs.append(entry)
                                if len(logs) >= limit:
                                    return logs
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            logger.error(f"读取审计日志失败: {str(e)}")
        
        return logs


class SecurityManager:
    """安全管理器
    
    整合所有安全功能。
    """
    
    def __init__(
        self,
        enable_rate_limit: bool = True,
        enable_audit_log: bool = True,
        max_requests: int = 10,
        time_window: int = 60
    ):
        """
        初始化安全管理器
        
        Args:
            enable_rate_limit: 是否启用速率限制
            enable_audit_log: 是否启用审计日志
            max_requests: 最大请求数
            time_window: 时间窗口
        """
        self.validator = SecurityValidator()
        self.rate_limiter = RateLimiter(
            max_requests=max_requests,
            time_window=time_window,
            enabled=enable_rate_limit
        )
        self.audit_logger = AuditLogger(enabled=enable_audit_log)
        
        logger.info("SecurityManager初始化完成")
    
    def validate_and_log_query(
        self,
        query: str,
        user_id: str = "default"
    ) -> str:
        """
        验证查询并记录日志
        
        Args:
            query: 用户查询
            user_id: 用户标识
            
        Returns:
            清理后的查询
            
        Raises:
            SecurityError: 验证失败
            RateLimitError: 超过速率限制
        """
        # 检查速率限制
        self.rate_limiter.check_rate_limit(user_id)
        
        # 验证和清理输入
        cleaned_query = self.validator.sanitize_query(query)
        
        # 记录审计日志
        self.audit_logger.log_query(user_id, cleaned_query)
        
        return cleaned_query
    
    def scan_and_log_generation(
        self,
        query: str,
        generated_code: str,
        user_id: str = "default",
        success: bool = True,
        error: Optional[str] = None
    ) -> tuple[str, List[str]]:
        """
        扫描生成的代码并记录日志
        
        Args:
            query: 用户查询
            generated_code: 生成的代码
            user_id: 用户标识
            success: 是否成功
            error: 错误信息
            
        Returns:
            (处理后的代码, 警告列表)
        """
        # 扫描危险模式
        warnings = self.validator.scan_generated_code(generated_code)
        
        # 添加安全警告
        if warnings:
            generated_code = self.validator.add_security_warnings(
                generated_code,
                warnings
            )
        
        # 记录审计日志
        self.audit_logger.log_generation(
            user_id=user_id,
            query=query,
            generated_code=generated_code,
            success=success,
            error=error,
            metadata={'warnings': warnings}
        )
        
        return generated_code, warnings
