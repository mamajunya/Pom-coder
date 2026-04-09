"""
pomCoder - 智能代码生成助手

功能：
1. 代码生成（Ollama）
2. 知识库管理（Embedding训练）
3. OpenAI兼容API
4. 美观的Web GUI
"""

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
import time
import uvicorn
from loguru import logger
import json
from pathlib import Path
import asyncio
import signal
import sys
import subprocess
import requests

from src.rag_code_generator.ollama_rag_generator import OllamaRAGGenerator
from src.rag_code_generator.ollama_generator import OllamaGeneratorError
from src.rag_code_generator.conversation import ConversationManager
from build_knowledge_base_npu import NPUKnowledgeBaseBuilder
from code_slicer import CodeSlicerTool


# 创建FastAPI应用
app = FastAPI(
    title="pomCoder",
    description="智能代码生成助手 - 集成Ollama、知识库管理和OpenAI兼容API",
    version="3.0.0"
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求的详细信息"""
    # 记录请求信息
    logger.info("=" * 60)
    logger.info(f"收到请求: {request.method} {request.url.path}")
    logger.info(f"  - 客户端: {request.client.host if request.client else 'unknown'}")
    logger.info(f"  - Headers: {dict(request.headers)}")
    
    # 对于POST请求，记录body
    if request.method == "POST":
        try:
            body = await request.body()
            if body:
                try:
                    body_json = json.loads(body)
                    logger.info(f"  - Body: {json.dumps(body_json, indent=2, ensure_ascii=False)}")
                except:
                    logger.info(f"  - Body (raw): {body[:500]}")
                
                # 重新构造request以便后续处理
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
        except Exception as e:
            logger.error(f"  - 读取Body失败: {e}")
    
    # 处理请求
    try:
        response = await call_next(request)
        logger.info(f"  - 响应状态: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"  - 请求处理异常: {e}", exc_info=True)
        raise

# 全局异常处理器
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """处理422验证错误"""
    logger.error("=" * 60)
    logger.error("422 验证错误")
    logger.error(f"请求路径: {request.url.path}")
    logger.error(f"请求方法: {request.method}")
    
    # 尝试读取请求body
    try:
        body = await request.body()
        if body:
            logger.error(f"请求Body: {body.decode('utf-8')}")
    except:
        pass
    
    logger.error(f"异常详情: {exc}")
    logger.error("=" * 60)
    
    # 返回详细错误信息
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "error": "Validation Error",
            "message": "请求数据验证失败，请检查请求格式"
        }
    )

# 全局变量
generator: Optional[OllamaRAGGenerator] = None
conversation_manager: Optional[ConversationManager] = None
kb_builder: Optional[NPUKnowledgeBaseBuilder] = None
kb_build_status = {"status": "idle", "progress": 0, "message": ""}
slicer_status = {"status": "idle", "progress": 0, "message": "", "slices": 0}
current_model_name: Optional[str] = None  # 记录当前加载的模型名称

# OpenAI API密钥配置
OPENAI_API_KEY = "pom-0721"  # 默认API密钥


# ==================== API密钥验证 ====================

def verify_api_key(authorization: Optional[str] = Header(None)) -> bool:
    """验证OpenAI API密钥"""
    if authorization is None:
        return False
    
    # 支持两种格式：
    # 1. Bearer pom-0721
    # 2. pom-0721
    if authorization.startswith("Bearer "):
        api_key = authorization[7:]  # 去掉 "Bearer " 前缀
    else:
        api_key = authorization
    
    return api_key == OPENAI_API_KEY


# ==================== 数据模型 ====================

# 代码生成请求
class GenerateRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    temperature: Optional[float] = Field(0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(512, ge=50, le=2048)


# OpenAI兼容请求
class OpenAICompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    model: str = "pomcoder"
    prompt: Union[str, List[str]]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None


class OpenAIChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    role: str  # 支持 system, user, assistant 等
    content: str


class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    model: str = "pomcoder"
    messages: List[OpenAIChatMessage]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    stream_options: Optional[Dict[str, Any]] = None  # Cline发送的额外字段


# 知识库构建请求
class BuildKBRequest(BaseModel):
    source_type: str = Field(..., description="json or directory")
    source_path: str
    use_npu: bool = False
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"


# ==================== 初始化 ====================

def initialize_generator(
    model_name: str = "deepseek-coder:6.7b",
    ollama_url: str = "http://localhost:11434",
    knowledge_base_path: Optional[str] = "./knowledge_base"
):
    """初始化生成器"""
    global generator, current_model_name, conversation_manager
    
    try:
        logger.info("初始化Ollama RAG生成器...")
        generator = OllamaRAGGenerator(
            model_name=model_name,
            ollama_url=ollama_url,
            knowledge_base_path=knowledge_base_path,
            enable_cache=True
        )
        current_model_name = model_name  # 记录模型名称
        logger.info("✓ 生成器初始化成功")
        
        # 初始化对话管理器
        logger.info("初始化对话管理器...")
        conversation_manager = ConversationManager(storage_dir="./conversations")
        logger.info("✓ 对话管理器初始化成功")
        
        # 预加载模型到GPU
        logger.info("正在预加载模型到GPU...")
        try:
            # 发送一个简单的测试请求，触发模型加载
            test_result = generator.generate(
                query="print('hello')",
                temperature=0.1,
                max_new_tokens=10,
                use_cache=False,
                use_rag=False  # 预加载时不使用RAG
            )
            logger.info("✓ 模型预加载完成，已就绪")
        except Exception as e:
            logger.warning(f"模型预加载失败: {str(e)}")
            logger.warning("首次请求时将自动加载模型")
        
        return True
    except Exception as e:
        logger.error(f"✗ 生成器初始化失败: {str(e)}")
        return False


def unload_ollama_model():
    """卸载Ollama模型，释放显存"""
    global current_model_name
    
    if current_model_name is None:
        logger.info("没有加载的模型需要卸载")
        return
    
    try:
        logger.info(f"正在卸载Ollama模型: {current_model_name}")
        
        # 方法1: 使用ollama stop命令（更彻底）
        try:
            result = subprocess.run(
                ["ollama", "stop", current_model_name],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                logger.info(f"✓ 模型 {current_model_name} 已停止")
            else:
                logger.warning(f"stop命令返回: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning("stop命令超时")
        except FileNotFoundError:
            logger.warning("ollama命令未找到")
        
        # 方法2: 发送DELETE请求到Ollama API（强制卸载）
        try:
            import requests
            ollama_url = "http://localhost:11434"
            
            # 删除模型实例
            response = requests.delete(
                f"{ollama_url}/api/generate",
                json={"model": current_model_name},
                timeout=10
            )
            logger.info("已发送卸载请求到Ollama API")
        except Exception as e:
            logger.debug(f"API卸载失败: {str(e)}")
        
        # 方法3: 强制垃圾回收
        try:
            import gc
            gc.collect()
            logger.info("已执行垃圾回收")
        except Exception as e:
            logger.debug(f"垃圾回收失败: {str(e)}")
        
        current_model_name = None
        logger.info("✓ 模型卸载流程完成")
        logger.info("提示: 如果显存未释放，请手动运行: ollama stop " + (current_model_name or ""))
        
    except Exception as e:
        logger.error(f"卸载模型时出错: {str(e)}")
        logger.info("建议手动卸载: ollama stop " + (current_model_name or ""))


def signal_handler(signum, frame):
    """信号处理函数"""
    logger.info("\n收到关闭信号，正在清理资源...")
    unload_ollama_model()
    logger.info("资源清理完成，退出程序")
    sys.exit(0)


# ==================== 主页 ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """主页 - 返回静态HTML（禁用缓存）"""
    from fastapi.responses import FileResponse
    return FileResponse(
        'static/index.html',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )


# ==================== 代码生成API ====================

@app.post("/api/generate")
async def generate_code(request: GenerateRequest):
    """代码生成API"""
    if generator is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        result = generator.generate(
            query=request.query,
            temperature=request.temperature,
            max_new_tokens=request.max_tokens
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== OpenAI兼容API ====================

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: Optional[str] = Header(None)):
    """OpenAI Chat Completions API - 使用原始Request避免Pydantic验证问题"""
    logger.info("处理chat completions请求")
    
    # 验证API密钥
    if not verify_api_key(authorization):
        logger.warning(f"API密钥验证失败: {authorization}")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.info("API密钥验证通过")
    
    if generator is None:
        logger.error("生成器未初始化")
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        # 手动解析请求body，避免Pydantic验证
        body = await request.body()
        request_data = json.loads(body)
        
        logger.info(f"解析请求数据成功")
        logger.info(f"请求字段: {list(request_data.keys())}")
        
        # 提取参数（使用默认值）
        model = request_data.get("model", "pomcoder")
        messages = request_data.get("messages", [])
        temperature = request_data.get("temperature", 0.2)
        max_tokens = request_data.get("max_tokens", 512)
        stream = request_data.get("stream", False)
        
        logger.info(f"请求参数: model={model}, stream={stream}, temp={temperature}, max_tokens={max_tokens}")
        logger.info(f"消息数量: {len(messages)}")
        
        # 提取system消息和用户消息
        system_message = None
        user_message = ""
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            # 处理content可能是列表的情况（多模态消息）
            if isinstance(content, list):
                # 提取文本内容
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = " ".join(text_parts)
            elif not isinstance(content, str):
                content = str(content)
            
            if role == "system":
                system_message = content
                logger.info(f"System消息: {system_message[:100] if system_message else ''}...")
            elif role == "user":
                user_message = content
        
        if not user_message:
            logger.error("未找到用户消息")
            raise ValueError("没有找到用户消息")
        
        logger.info(f"用户消息: {user_message[:100] if user_message else ''}...")
        
        # 流式响应
        if stream:
            logger.info("使用流式响应")
            from fastapi.responses import StreamingResponse
            
            async def generate_stream():
                """生成流式响应"""
                try:
                    # 使用system消息或默认提示
                    if system_message:
                        system_prompt = system_message
                    else:
                        system_prompt = (
                            "你是一个专业的代码生成助手。"
                            "请根据用户的需求生成高质量、可运行的代码。"
                            "代码应该包含必要的注释和错误处理。"
                        )
                    
                    # 流式生成
                    for chunk_text in generator.ollama_generator.generate_stream(
                        prompt=user_message,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        system_prompt=system_prompt
                    ):
                        # OpenAI流式格式
                        chunk = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": chunk_text
                                },
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                    
                    # 发送结束标记
                    final_chunk = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    logger.error(f"流式生成错误: {e}", exc_info=True)
                    error_chunk = {
                        "error": {
                            "message": str(e),
                            "type": "generation_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        # 非流式响应
        else:
            logger.info("使用非流式响应")
            # 生成代码
            result = generator.generate(
                query=user_message,
                temperature=temperature,
                max_new_tokens=max_tokens
            )
            
            logger.info(f"生成完成，代码长度: {len(result['code'])} 字符")
            
            # 返回OpenAI格式
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result['code']
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(user_message.split()),
                    "completion_tokens": len(result['code'].split()),
                    "total_tokens": len(user_message.split()) + len(result['code'].split())
                }
            }
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        logger.error(f"chat_completions错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/completions")
async def completions(request: OpenAICompletionRequest, authorization: Optional[str] = Header(None)):
    """OpenAI Completions API"""
    # 验证API密钥
    if not verify_api_key(authorization):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if generator is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        prompt = request.prompt if isinstance(request.prompt, str) else request.prompt[0]
        
        result = generator.generate(
            query=prompt,
            temperature=request.temperature,
            max_new_tokens=request.max_tokens
        )
        
        return {
            "id": f"cmpl-{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "text": result['code'],
                "index": 0,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(result['code'].split()),
                "total_tokens": len(prompt.split()) + len(result['code'].split())
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 代码切片API ====================

class SliceRequest(BaseModel):
    directory: str
    extensions: List[str] = [".py", ".js"]
    max_files: int = 1000
    min_length: int = 50
    max_length: int = 5000


@app.post("/api/code-slicer/slice")
async def slice_code(request: SliceRequest, background_tasks: BackgroundTasks):
    """代码切片API - 目录模式"""
    try:
        # 后台任务执行切片
        background_tasks.add_task(
            slice_code_task,
            request.directory,
            request.extensions,
            request.max_files,
            request.min_length,
            request.max_length
        )
        
        return {"message": "代码切片已开始", "status": "slicing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code-slicer/slice-files")
async def slice_uploaded_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    min_length: int = 50,
    max_length: int = 5000
):
    """代码切片API - 文件上传模式"""
    try:
        # 保存上传的文件
        upload_dir = Path("./uploads/code_files")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        for file in files:
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append(str(file_path))
        
        # 后台任务执行切片
        background_tasks.add_task(
            slice_files_task,
            saved_files,
            min_length,
            max_length
        )
        
        return {"message": "代码切片已开始", "status": "slicing", "files": len(saved_files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def slice_code_task(
    directory: str,
    extensions: List[str],
    max_files: int,
    min_length: int,
    max_length: int
):
    """后台切片任务 - 目录模式"""
    global slicer_status
    
    try:
        slicer_status = {"status": "slicing", "progress": 10, "message": "初始化切片器...", "slices": 0}
        
        slicer = CodeSlicerTool()
        
        slicer_status["progress"] = 30
        slicer_status["message"] = f"扫描目录: {directory}"
        
        slices = slicer.slice_directory(
            directory=directory,
            extensions=extensions,
            max_files=max_files,
            min_code_length=min_length,
            max_code_length=max_length
        )
        
        slicer_status["progress"] = 70
        slicer_status["message"] = "保存结果..."
        
        output_file = "code_slices.json"
        slicer.save_to_json(output_file)
        
        slicer_status["progress"] = 90
        slicer_status["message"] = "生成统计信息..."
        
        stats = slicer.generate_statistics()
        
        slicer_status = {
            "status": "completed",
            "progress": 100,
            "message": "切片完成",
            "slices": len(slices),
            "output_file": output_file,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"切片失败: {str(e)}")
        slicer_status = {"status": "error", "progress": 0, "message": str(e), "slices": 0}


def slice_files_task(
    file_paths: List[str],
    min_length: int,
    max_length: int
):
    """后台切片任务 - 文件上传模式"""
    global slicer_status
    
    try:
        slicer_status = {"status": "slicing", "progress": 10, "message": "初始化切片器...", "slices": 0}
        
        slicer = CodeSlicerTool()
        all_slices = []
        
        slicer_status["progress"] = 30
        slicer_status["message"] = f"处理 {len(file_paths)} 个文件..."
        
        for i, file_path in enumerate(file_paths):
            file_path_obj = Path(file_path)
            
            # 根据文件扩展名选择切片器
            if file_path_obj.suffix == '.py':
                slices = slicer.python_slicer.slice_file(file_path_obj)
            elif file_path_obj.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                slices = slicer.js_slicer.slice_file(file_path_obj)
            else:
                logger.warning(f"不支持的文件类型: {file_path_obj.suffix}")
                continue
            
            # 过滤切片
            for slice_obj in slices:
                if min_length <= len(slice_obj.code) <= max_length:
                    all_slices.append(slice_obj)
            
            # 更新进度
            progress = 30 + int((i + 1) / len(file_paths) * 40)
            slicer_status["progress"] = progress
            slicer_status["message"] = f"已处理 {i + 1}/{len(file_paths)} 个文件"
        
        slicer.slices = all_slices
        
        slicer_status["progress"] = 70
        slicer_status["message"] = "保存结果..."
        
        output_file = "code_slices.json"
        slicer.save_to_json(output_file)
        
        slicer_status["progress"] = 90
        slicer_status["message"] = "生成统计信息..."
        
        stats = slicer.generate_statistics()
        
        slicer_status = {
            "status": "completed",
            "progress": 100,
            "message": "切片完成",
            "slices": len(all_slices),
            "output_file": output_file,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"切片失败: {str(e)}")
        slicer_status = {"status": "error", "progress": 0, "message": str(e), "slices": 0}


@app.get("/api/code-slicer/status")
async def get_slicer_status():
    """获取切片状态"""
    return slicer_status


# ==================== 知识库管理API ====================

@app.post("/api/knowledge-base/build")
async def build_knowledge_base(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    use_npu: bool = True,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    append_mode: bool = True
):
    """构建知识库"""
    try:
        # 保存上传的文件
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 后台任务构建知识库
        background_tasks.add_task(
            build_kb_task,
            str(file_path),
            use_npu,
            embedding_model,
            append_mode
        )
        
        mode_text = "叠加" if append_mode else "覆盖"
        return {"message": f"知识库构建已开始（{mode_text}模式）", "status": "building"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def build_kb_task(source_path: str, use_npu: bool, embedding_model: str, append_mode: bool = True):
    """后台构建知识库任务"""
    global kb_build_status
    
    try:
        kb_build_status = {"status": "building", "progress": 0, "message": "初始化..."}
        
        builder = NPUKnowledgeBaseBuilder(
            embedding_model=embedding_model,
            output_dir="./knowledge_base",
            use_npu=use_npu,
            append_mode=append_mode
        )
        
        kb_build_status["progress"] = 20
        kb_build_status["message"] = "加载代码片段..."
        
        builder.collect_from_json(source_path)
        
        kb_build_status["progress"] = 50
        kb_build_status["message"] = "生成Embedding..."
        
        builder.build()
        
        mode_text = "叠加" if append_mode else "覆盖"
        kb_build_status = {"status": "completed", "progress": 100, "message": f"构建完成（{mode_text}模式）"}
        
    except Exception as e:
        kb_build_status = {"status": "error", "progress": 0, "message": str(e)}


@app.get("/api/knowledge-base/status")
async def get_kb_status():
    """获取知识库构建状态"""
    return kb_build_status


# ==================== 对话管理API ====================

@app.post("/api/conversations/create")
async def create_conversation(title: str = "新对话", system_prompt: Optional[str] = None):
    """创建新对话"""
    if conversation_manager is None:
        raise HTTPException(status_code=503, detail="对话管理器未初始化")
    
    try:
        conv = conversation_manager.create_conversation(title=title, system_prompt=system_prompt)
        return {
            "conversation_id": conv.conversation_id,
            "title": conv.title,
            "created_at": conv.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/list")
async def list_conversations(limit: int = 50):
    """列出所有对话"""
    if conversation_manager is None:
        raise HTTPException(status_code=503, detail="对话管理器未初始化")
    
    try:
        conversations = conversation_manager.list_conversations(limit=limit)
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    if conversation_manager is None:
        raise HTTPException(status_code=503, detail="对话管理器未初始化")
    
    try:
        conv = conversation_manager.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return conv.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    if conversation_manager is None:
        raise HTTPException(status_code=503, detail="对话管理器未初始化")
    
    try:
        success = conversation_manager.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return {"message": "对话已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 512
    use_rag: Optional[bool] = True
    stream: Optional[bool] = False


@app.post("/api/conversations/chat")
async def chat_with_conversation(request: ChatRequest):
    """在对话中发送消息"""
    if conversation_manager is None or generator is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        # 获取对话
        conv = conversation_manager.get_conversation(request.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 添加用户消息
        conversation_manager.add_message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message
        )
        
        # 流式响应
        if request.stream:
            from fastapi.responses import StreamingResponse
            
            async def generate_stream():
                full_response = ""
                try:
                    if request.use_rag:
                        # RAG模式暂不支持流式，返回完整结果
                        result = generator.generate(
                            query=request.message,
                            temperature=request.temperature,
                            max_new_tokens=request.max_tokens,
                            use_rag=True
                        )
                        full_response = result['code']
                        yield f"data: {json.dumps({'content': full_response, 'done': False})}\n\n"
                    else:
                        # 非RAG模式，使用流式生成
                        ollama_response = requests.post(
                            f"{generator.ollama_generator.base_url}/api/generate",
                            json={
                                "model": generator.ollama_generator.model_name,
                                "prompt": request.message,
                                "system": conv.system_prompt,
                                "stream": True,
                                "options": {
                                    "temperature": request.temperature,
                                    "num_predict": request.max_tokens
                                }
                            },
                            stream=True,
                            timeout=120
                        )
                        
                        for line in ollama_response.iter_lines():
                            if line:
                                chunk = json.loads(line)
                                if 'response' in chunk:
                                    content = chunk['response']
                                    full_response += content
                                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                    
                    # 发送完成标记
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    
                    # 保存完整回复
                    conversation_manager.add_message(
                        conversation_id=request.conversation_id,
                        role="assistant",
                        content=full_response,
                        metadata={
                            "use_rag": request.use_rag,
                            "temperature": request.temperature
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"流式生成错误: {e}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        # 非流式响应
        else:
            if request.use_rag:
                result = generator.generate(
                    query=request.message,
                    temperature=request.temperature,
                    max_new_tokens=request.max_tokens,
                    use_rag=True
                )
                response_text = result['code']
            else:
                # 不使用RAG，直接调用Ollama进行对话
                ollama_response = requests.post(
                    f"{generator.ollama_generator.base_url}/api/generate",
                    json={
                        "model": generator.ollama_generator.model_name,
                        "prompt": request.message,
                        "system": conv.system_prompt,
                        "stream": False,
                        "options": {
                            "temperature": request.temperature,
                            "num_predict": request.max_tokens
                        }
                    },
                    timeout=120
                )
                
                if ollama_response.status_code == 200:
                    response_text = ollama_response.json().get('response', '')
                else:
                    raise Exception(f"Ollama请求失败: {ollama_response.status_code}")
            
            # 添加助手回复
            conversation_manager.add_message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=response_text,
                metadata={
                    "use_rag": request.use_rag,
                    "temperature": request.temperature
                }
            )
            
            return {
                "response": response_text,
                "metadata": {
                    "use_rag": request.use_rag,
                    "temperature": request.temperature
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对话错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversations/{conversation_id}/clear")
async def clear_conversation(conversation_id: str):
    """清空对话历史"""
    if conversation_manager is None:
        raise HTTPException(status_code=503, detail="对话管理器未初始化")
    
    try:
        conv = conversation_manager.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        conv.clear_messages()
        conversation_manager._save_conversation(conv)
        
        return {"message": "对话历史已清空"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统API ====================

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/api/system/info")
async def get_system_info():
    """获取系统信息（包括知识库状态）"""
    if generator is None:
        return {
            "status": "not_initialized",
            "knowledge_base_loaded": False,
            "knowledge_base_size": 0,
            "model_name": current_model_name,
            "version": "3.0.0"
        }
    
    try:
        info = generator.get_system_info()
        info["model_name"] = current_model_name
        info["version"] = "3.0.0"
        return info
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "knowledge_base_loaded": False,
            "knowledge_base_size": 0,
            "model_name": current_model_name,
            "version": "3.0.0"
        }


# ==================== 设置API ====================

class SettingsUpdateRequest(BaseModel):
    model_name: str
    ollama_url: str = "http://localhost:11434"


@app.post("/api/settings/update")
async def update_settings(request: SettingsUpdateRequest):
    """更新设置并重新初始化生成器"""
    global generator, current_model_name
    
    try:
        logger.info(f"更新设置: 模型={request.model_name}, URL={request.ollama_url}")
        
        # 卸载旧模型
        if current_model_name:
            unload_ollama_model()
        
        # 重新初始化生成器
        success = initialize_generator(
            model_name=request.model_name,
            ollama_url=request.ollama_url,
            knowledge_base_path="./knowledge_base"
        )
        
        if success:
            return {
                "success": True,
                "message": "设置已更新",
                "model_name": current_model_name
            }
        else:
            raise Exception("生成器初始化失败")
            
    except Exception as e:
        logger.error(f"更新设置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class TestModelRequest(BaseModel):
    model_name: str


@app.post("/api/settings/test-model")
async def test_model_endpoint(request: TestModelRequest):
    """测试模型是否可用"""
    try:
        logger.info(f"测试模型: {request.model_name}")
        
        # 发送测试请求到Ollama
        ollama_url = generator.ollama_generator.base_url if generator else "http://localhost:11434"
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": request.model_name,
                "prompt": "Hello",
                "stream": False,
                "options": {
                    "num_predict": 10
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "response": result.get('response', ''),
                "message": "模型测试成功"
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "message": "模型测试失败"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时，请检查Ollama服务是否运行",
            "message": "模型测试失败"
        }
    except Exception as e:
        logger.error(f"测试模型失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "模型测试失败"
        }


@app.get("/api/models")
@app.get("/v1/models")
async def list_models():
    """列出可用模型（OpenAI兼容）"""
    return {
        "object": "list",
        "data": [
            {
                "id": "pomcoder",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "pomcoder"
            }
        ]
    }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="pomCoder - 智能代码生成助手")
    parser.add_argument("--model", default="deepseek-coder:6.7b", help="Ollama模型")
    parser.add_argument("--port", type=int, default=58761, help="端口")
    parser.add_argument("--host", default="0.0.0.0", help="主机")
    
    args = parser.parse_args()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill命令
    
    logger.info("=" * 60)
    logger.info("pomCoder - 智能代码生成助手")
    logger.info("=" * 60)
    
    # 初始化
    success = initialize_generator(model_name=args.model)
    
    if not success:
        logger.error("初始化失败")
        return
    
    logger.info(f"启动Web服务: http://{args.host}:{args.port}")
    logger.info(f"OpenAI API: http://{args.host}:{args.port}/v1")
    logger.info(f"使用模型: {args.model}")
    logger.info("提示: 按 Ctrl+C 停止服务并自动卸载模型")
    logger.info("=" * 60)
    
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except KeyboardInterrupt:
        logger.info("\n收到中断信号")
    finally:
        # 确保退出时卸载模型
        unload_ollama_model()
        logger.info("服务已停止")


if __name__ == "__main__":
    main()
