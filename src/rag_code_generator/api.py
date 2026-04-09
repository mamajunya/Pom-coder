"""
RESTful API接口模块

实现功能：
1. FastAPI应用
2. /api/v1/generate端点
3. /api/v1/health健康检查
4. /api/v1/metrics性能指标
5. 请求验证和错误处理
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
import time
import traceback

from .rag_generator import RAGCodeGenerator
from .monitoring import PerformanceMonitor, HealthChecker, get_prometheus_metrics
from .models import GenerationConfig


# 请求模型
class GenerateRequest(BaseModel):
    """代码生成请求"""
    query: str = Field(..., min_length=1, max_length=500, description="用户查询")
    temperature: Optional[float] = Field(0.2, ge=0.0, le=2.0, description="生成温度")
    max_new_tokens: Optional[int] = Field(512, ge=1, le=2048, description="最大生成token数")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="检索Top-K")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


# 响应模型
class GenerateResponse(BaseModel):
    """代码生成响应"""
    code: str = Field(..., description="生成的代码")
    query: str = Field(..., description="处理后的查询")
    duration: float = Field(..., description="生成耗时（秒）")
    retrieved_count: int = Field(..., description="检索到的代码片段数量")
    cached: bool = Field(False, description="是否来自缓存")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="健康状态: healthy, degraded, unhealthy")
    checks: Dict = Field(..., description="各项检查结果")
    timestamp: float = Field(..., description="检查时间戳")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    timestamp: float = Field(..., description="错误时间戳")


# 创建FastAPI应用
app = FastAPI(
    title="RAG Code Generator API",
    description="基于RAG的智能代码生成系统API",
    version="1.0.0"
)


# 全局变量
generator: Optional[RAGCodeGenerator] = None
monitor: Optional[PerformanceMonitor] = None
health_checker: Optional[HealthChecker] = None


def initialize_app(
    model_path: str,
    index_path: str,
    device: str = "cuda:0",
    enable_cache: bool = True
):
    """
    初始化应用
    
    Args:
        model_path: 模型路径
        index_path: 索引路径
        device: 设备
        enable_cache: 是否启用缓存
    """
    global generator, monitor, health_checker
    
    # 创建监控器
    monitor = PerformanceMonitor()
    
    # 创建生成器
    generator = RAGCodeGenerator(
        model_path=model_path,
        index_path=index_path,
        device=device,
        enable_cache=enable_cache,
        monitor=monitor
    )
    
    # 创建健康检查器
    health_checker = HealthChecker(generator)


@app.post("/api/v1/generate", response_model=GenerateResponse)
async def generate_code(request: GenerateRequest):
    """
    生成代码端点
    
    Args:
        request: 生成请求
    
    Returns:
        生成响应
    """
    if generator is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized"
        )
    
    start_time = time.time()
    
    try:
        # 创建配置
        config = GenerationConfig(
            temperature=request.temperature,
            max_new_tokens=request.max_new_tokens,
            top_k=request.top_k
        )
        
        # 生成代码
        result = generator.generate(request.query, config)
        
        duration = time.time() - start_time
        
        # 构造响应
        response = GenerateResponse(
            code=result.get("code", ""),
            query=result.get("query", request.query),
            duration=duration,
            retrieved_count=result.get("retrieved_count", 0),
            cached=result.get("cached", False)
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查端点
    
    Returns:
        健康状态
    """
    if health_checker is None:
        return HealthResponse(
            status="unhealthy",
            checks={"service": {"status": "unhealthy", "message": "Not initialized"}},
            timestamp=time.time()
        )
    
    health = health_checker.check_health()
    return HealthResponse(**health)


@app.get("/api/v1/metrics")
async def get_metrics():
    """
    获取性能指标端点
    
    Returns:
        性能指标（JSON格式）
    """
    if monitor is None:
        raise HTTPException(
            status_code=503,
            detail="Monitoring not initialized"
        )
    
    return {
        "statistics": monitor.get_statistics(),
        "recent_metrics": monitor.get_recent_metrics(limit=20),
        "timestamp": time.time()
    }


@app.get("/api/v1/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics_endpoint():
    """
    获取Prometheus格式的指标
    
    Returns:
        Prometheus格式的指标文本
    """
    if monitor is None:
        raise HTTPException(
            status_code=503,
            detail="Monitoring not initialized"
        )
    
    return get_prometheus_metrics(monitor)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=type(exc).__name__,
            message=str(exc),
            timestamp=time.time()
        ).dict()
    )


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "RAG Code Generator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "generate": "/api/v1/generate",
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics",
            "prometheus": "/api/v1/metrics/prometheus"
        }
    }


# 启动脚本
if __name__ == "__main__":
    import uvicorn
    
    # 初始化应用
    initialize_app(
        model_path="deepseek-ai/deepseek-coder-6.7b-instruct",
        index_path="./indexes",
        device="cuda:0",
        enable_cache=True
    )
    
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
