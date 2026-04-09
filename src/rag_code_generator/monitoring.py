"""
监控与可观测性模块

实现功能：
1. 性能监控（各阶段耗时统计）
2. 资源使用监控（GPU显存、系统内存）
3. 健康检查接口
4. 性能指标查询
"""

import time
import psutil
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import threading


@dataclass
class PerformanceMetrics:
    """性能指标"""
    stage: str
    duration: float
    timestamp: float
    memory_mb: float = 0.0
    gpu_memory_mb: float = 0.0


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        """初始化性能监控器"""
        self.metrics: List[PerformanceMetrics] = []
        self.stage_times: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        self._start_time = None
        self._current_stage = None
    
    def start_stage(self, stage: str):
        """开始监控一个阶段"""
        self._current_stage = stage
        self._start_time = time.time()
    
    def end_stage(self, stage: str):
        """结束监控一个阶段"""
        if self._start_time is None:
            return
        
        duration = time.time() - self._start_time
        
        # 获取资源使用情况
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        gpu_memory_mb = self._get_gpu_memory()
        
        # 记录指标
        metric = PerformanceMetrics(
            stage=stage,
            duration=duration,
            timestamp=time.time(),
            memory_mb=memory_mb,
            gpu_memory_mb=gpu_memory_mb
        )
        
        with self.lock:
            self.metrics.append(metric)
            self.stage_times[stage].append(duration)
        
        self._start_time = None
        self._current_stage = None

    def _get_gpu_memory(self) -> float:
        """获取GPU显存使用（MB）"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / 1024 / 1024
        except:
            pass
        return 0.0
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self.lock:
            stats = {}
            for stage, times in self.stage_times.items():
                if times:
                    stats[stage] = {
                        "count": len(times),
                        "avg_duration": sum(times) / len(times),
                        "min_duration": min(times),
                        "max_duration": max(times),
                        "total_duration": sum(times)
                    }
            return stats
    
    def get_recent_metrics(self, limit: int = 10) -> List[Dict]:
        """获取最近的指标"""
        with self.lock:
            recent = self.metrics[-limit:]
            return [
                {
                    "stage": m.stage,
                    "duration": m.duration,
                    "timestamp": m.timestamp,
                    "memory_mb": m.memory_mb,
                    "gpu_memory_mb": m.gpu_memory_mb
                }
                for m in recent
            ]
    
    def clear(self):
        """清除所有指标"""
        with self.lock:
            self.metrics.clear()
            self.stage_times.clear()


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, generator=None):
        """
        初始化健康检查器
        
        Args:
            generator: RAGCodeGenerator实例
        """
        self.generator = generator
    
    def check_health(self) -> Dict:
        """
        执行健康检查
        
        Returns:
            健康状态字典
        """
        health = {
            "status": "healthy",
            "checks": {},
            "timestamp": time.time()
        }
        
        # 检查系统资源
        health["checks"]["system"] = self._check_system()
        
        # 检查GPU
        health["checks"]["gpu"] = self._check_gpu()
        
        # 检查模型
        if self.generator:
            health["checks"]["model"] = self._check_model()
        
        # 判断整体状态
        if any(check["status"] == "unhealthy" for check in health["checks"].values()):
            health["status"] = "unhealthy"
        elif any(check["status"] == "degraded" for check in health["checks"].values()):
            health["status"] = "degraded"
        
        return health
    
    def _check_system(self) -> Dict:
        """检查系统资源"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        status = "healthy"
        if memory.percent > 90 or cpu_percent > 90:
            status = "unhealthy"
        elif memory.percent > 80 or cpu_percent > 80:
            status = "degraded"
        
        return {
            "status": status,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / 1024 / 1024,
            "cpu_percent": cpu_percent
        }
    
    def _check_gpu(self) -> Dict:
        """检查GPU状态"""
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024 / 1024
                reserved = torch.cuda.memory_reserved() / 1024 / 1024
                total = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024
                
                percent = (allocated / total) * 100
                status = "healthy"
                if percent > 90:
                    status = "unhealthy"
                elif percent > 80:
                    status = "degraded"
                
                return {
                    "status": status,
                    "available": True,
                    "allocated_mb": allocated,
                    "reserved_mb": reserved,
                    "total_mb": total,
                    "percent": percent
                }
        except:
            pass
        
        return {
            "status": "healthy",
            "available": False
        }
    
    def _check_model(self) -> Dict:
        """检查模型状态"""
        try:
            if hasattr(self.generator, 'generator') and self.generator.generator:
                return {
                    "status": "healthy",
                    "loaded": True,
                    "device": str(self.generator.generator.device)
                }
        except:
            pass
        
        return {
            "status": "unhealthy",
            "loaded": False
        }


def get_prometheus_metrics(monitor: PerformanceMonitor) -> str:
    """
    生成Prometheus格式的指标
    
    Args:
        monitor: 性能监控器实例
    
    Returns:
        Prometheus格式的指标文本
    """
    lines = []
    
    # 添加指标说明
    lines.append("# HELP rag_stage_duration_seconds Duration of each stage in seconds")
    lines.append("# TYPE rag_stage_duration_seconds summary")
    
    # 获取统计信息
    stats = monitor.get_statistics()
    
    for stage, data in stats.items():
        lines.append(f'rag_stage_duration_seconds{{stage="{stage}",quantile="0.5"}} {data["avg_duration"]}')
        lines.append(f'rag_stage_duration_seconds{{stage="{stage}",quantile="0.9"}} {data["max_duration"]}')
        lines.append(f'rag_stage_duration_seconds_count{{stage="{stage}"}} {data["count"]}')
        lines.append(f'rag_stage_duration_seconds_sum{{stage="{stage}"}} {data["total_duration"]}')
    
    return "\n".join(lines)
