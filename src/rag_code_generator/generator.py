"""代码生成器模块

实现DeepSeekCoder模型的加载、初始化和代码生成功能。

支持需求：
- 8.1: 将DeepSeekCoder模型以4bit量化方式加载到GPU显存
- 8.2: 确保主模型常驻GPU显存以避免重复加载
- 9.1: 模型文件不存在时抛出明确的错误信息并拒绝启动
- 9.2: GPU显存不足时提示用户并建议使用更激进的量化方式
- 5.1: 使用DeepSeekCoder模型生成代码
- 5.4: 生成过程超过30秒时终止生成并返回超时错误
"""

import os
from pathlib import Path
from typing import Optional, Any
import torch
from loguru import logger
import signal
from contextlib import contextmanager


class ModelLoadError(Exception):
    """模型加载错误异常"""
    pass


class GenerationTimeoutError(Exception):
    """生成超时错误异常"""
    pass


class CodeGenerator:
    """代码生成器
    
    负责DeepSeekCoder模型的加载、管理和代码生成。
    模型常驻GPU显存，避免重复加载。
    """
    
    def __init__(
        self,
        model_path: str,
        device: str = "cuda:0",
        quantization: str = "4bit",
        load_in_4bit: bool = True,
        timeout: int = 30
    ):
        """
        初始化代码生成器
        
        Args:
            model_path: 模型路径或HuggingFace模型名称
            device: 运行设备 (cuda:0, cpu)
            quantization: 量化方式 (4bit, 8bit, none)
            load_in_4bit: 是否使用4bit量化加载
            timeout: 生成超时时间（秒），默认30秒
            
        Raises:
            ModelLoadError: 模型加载失败
        """
        self.model_path = model_path
        self.device = device
        self.quantization = quantization
        self.load_in_4bit = load_in_4bit
        self.timeout = timeout
        
        # 模型和tokenizer实例（常驻显存）
        self.model: Optional[Any] = None
        self.tokenizer: Optional[Any] = None
        
        # 加载模型
        self._load_model()
        
        logger.info(f"CodeGenerator初始化完成，模型常驻{device}")
    
    def _validate_model_path(self) -> None:
        """
        验证模型路径是否存在
        
        支持需求9.1：模型文件不存在时抛出明确的错误信息
        
        Raises:
            ModelLoadError: 模型路径不存在
        """
        # 检查是否是本地路径
        if os.path.exists(self.model_path):
            return
        
        # 检查是否是HuggingFace模型名称（包含/）
        if "/" in self.model_path:
            # 假设是HuggingFace模型，将在下载时验证
            logger.info(f"将从HuggingFace下载模型: {self.model_path}")
            return
        
        # 路径不存在且不是HuggingFace格式
        raise ModelLoadError(
            f"模型文件不存在: {self.model_path}\n"
            f"请确保模型路径正确，或提供HuggingFace模型名称（如 'deepseek-ai/deepseek-coder-6.7b-instruct'）"
        )
    
    def _check_device_availability(self) -> None:
        """
        检查设备可用性
        
        支持需求9.2：GPU显存不足时提示用户
        
        Raises:
            ModelLoadError: 设备不可用
        """
        if self.device.startswith("cuda"):
            if not torch.cuda.is_available():
                raise ModelLoadError(
                    "CUDA不可用，但指定了GPU设备。\n"
                    "建议：\n"
                    "1. 检查CUDA安装\n"
                    "2. 使用CPU设备（device='cpu'）"
                )
            
            # 检查指定的GPU是否存在
            device_id = int(self.device.split(":")[-1]) if ":" in self.device else 0
            if device_id >= torch.cuda.device_count():
                raise ModelLoadError(
                    f"GPU设备 {self.device} 不存在，系统有 {torch.cuda.device_count()} 个GPU"
                )
            
            # 获取GPU显存信息
            gpu_memory = torch.cuda.get_device_properties(device_id).total_memory / (1024**3)
            logger.info(f"GPU {device_id} 总显存: {gpu_memory:.2f} GB")
            
            # 如果显存小于6GB，给出警告
            if gpu_memory < 6.0:
                logger.warning(
                    f"GPU显存较小 ({gpu_memory:.2f} GB < 6 GB)，"
                    f"建议使用4bit量化以减少显存占用"
                )
    
    def _load_model(self) -> None:
        """
        加载模型和tokenizer
        
        支持需求：
        - 8.1: 以4bit量化方式加载到GPU显存
        - 8.2: 模型常驻GPU显存
        - 9.1: 模型文件不存在时抛出错误
        - 9.2: GPU显存不足时提示用户
        
        Raises:
            ModelLoadError: 模型加载失败
        """
        try:
            # 验证模型路径
            self._validate_model_path()
            
            # 检查设备可用性
            self._check_device_availability()
            
            logger.info(f"开始加载模型: {self.model_path}")
            logger.info(f"设备: {self.device}, 量化: {self.quantization}")
            
            # 导入transformers库
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError:
                raise ModelLoadError(
                    "transformers库未安装，请运行: pip install transformers"
                )
            
            # 加载tokenizer
            logger.info("加载tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            # 配置量化参数
            model_kwargs = {
                "trust_remote_code": True,
                "device_map": "auto" if self.device.startswith("cuda") else None,
            }
            
            # 4bit量化配置
            if self.load_in_4bit and self.quantization == "4bit":
                try:
                    from transformers import BitsAndBytesConfig
                    
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                    model_kwargs["quantization_config"] = quantization_config
                    logger.info("使用4bit量化配置")
                    
                except ImportError:
                    raise ModelLoadError(
                        "bitsandbytes库未安装，无法使用4bit量化。\n"
                        "请运行: pip install bitsandbytes"
                    )
            
            # 加载模型
            logger.info("加载模型（这可能需要几分钟）...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **model_kwargs
            )
            
            # 如果没有使用device_map，手动移动到设备
            if not self.device.startswith("cuda") or model_kwargs.get("device_map") is None:
                self.model = self.model.to(self.device)
            
            # 设置为评估模式
            self.model.eval()
            
            logger.info("模型加载成功，已常驻显存")
            
            # 显示显存使用情况
            if self.device.startswith("cuda"):
                device_id = int(self.device.split(":")[-1]) if ":" in self.device else 0
                allocated = torch.cuda.memory_allocated(device_id) / (1024**3)
                reserved = torch.cuda.memory_reserved(device_id) / (1024**3)
                logger.info(f"GPU显存使用: 已分配 {allocated:.2f} GB, 已保留 {reserved:.2f} GB")
        
        except torch.cuda.OutOfMemoryError as e:
            # 支持需求9.2：GPU显存不足时的处理
            raise ModelLoadError(
                f"GPU显存不足，无法加载模型。\n"
                f"当前配置: {self.quantization} 量化\n"
                f"建议：\n"
                f"1. 使用4bit量化（quantization='4bit', load_in_4bit=True）\n"
                f"2. 使用更小的模型\n"
                f"3. 使用CPU设备（device='cpu'，但速度会较慢）\n"
                f"原始错误: {str(e)}"
            )
        
        except Exception as e:
            raise ModelLoadError(f"模型加载失败: {str(e)}")
    
    @contextmanager
    def _timeout_context(self, seconds: int):
        """
        超时上下文管理器
        
        支持需求5.4：生成过程超过指定时间时终止
        
        Args:
            seconds: 超时时间（秒）
            
        Raises:
            GenerationTimeoutError: 超时
        """
        def timeout_handler(signum, frame):
            raise GenerationTimeoutError(f"代码生成超时（>{seconds}秒）")
        
        # 设置信号处理器（仅在Unix系统上可用）
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        else:
            # Windows系统不支持SIGALRM，直接执行
            logger.warning("当前系统不支持超时控制（Windows）")
            yield
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_new_tokens: int = 512,
        top_p: float = 0.95,
        top_k: int = 50,
        do_sample: bool = True,
        repetition_penalty: float = 1.1,
        num_return_sequences: int = 1
    ) -> str:
        """
        生成代码
        
        支持需求：
        - 5.1: 使用DeepSeekCoder模型生成代码
        - 5.4: 生成过程超过30秒时终止
        
        Args:
            prompt: 输入Prompt
            temperature: 生成温度 [0, 1]，0表示确定性生成
            max_new_tokens: 最大生成token数
            top_p: nucleus sampling参数
            top_k: top-k sampling参数
            do_sample: 是否采样（temperature=0时自动设为False）
            repetition_penalty: 重复惩罚系数
            num_return_sequences: 返回序列数量
            
        Returns:
            生成的代码字符串
            
        Raises:
            ValueError: 输入无效
            GenerationTimeoutError: 生成超时
            RuntimeError: 生成过程出错
        """
        if not prompt or len(prompt.strip()) == 0:
            raise ValueError("Prompt不能为空")
        
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("模型未加载，请先初始化CodeGenerator")
        
        # 温度为0时，使用确定性生成
        if temperature == 0:
            do_sample = False
        
        try:
            logger.info(f"开始生成代码，max_tokens={max_new_tokens}, temperature={temperature}")
            
            # 使用超时控制
            with self._timeout_context(self.timeout):
                # Tokenize输入
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=2048  # 限制输入长度
                ).to(self.device)
                
                # 生成
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature if do_sample else 1.0,
                        top_p=top_p,
                        top_k=top_k,
                        do_sample=do_sample,
                        repetition_penalty=repetition_penalty,
                        num_return_sequences=num_return_sequences,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                # 解码输出
                generated_text = self.tokenizer.decode(
                    outputs[0],
                    skip_special_tokens=True
                )
                
                # 移除输入部分，只保留生成的内容
                input_text = self.tokenizer.decode(
                    inputs["input_ids"][0],
                    skip_special_tokens=True
                )
                
                if generated_text.startswith(input_text):
                    generated_code = generated_text[len(input_text):].strip()
                else:
                    generated_code = generated_text.strip()
                
                logger.info(f"代码生成完成，生成长度: {len(generated_code)} 字符")
                
                return generated_code
        
        except GenerationTimeoutError:
            # 重新抛出超时错误
            raise
        
        except Exception as e:
            logger.error(f"代码生成失败: {str(e)}")
            raise RuntimeError(f"代码生成失败: {str(e)}")
    
    def unload_model(self) -> None:
        """
        卸载模型，释放显存
        
        注意：通常不需要调用此方法，因为模型应该常驻显存。
        仅在需要释放资源时使用。
        """
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        # 清理GPU缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("模型已卸载，显存已释放")
    
    def __del__(self):
        """析构函数，确保资源释放"""
        if hasattr(self, 'model') and self.model is not None:
            logger.debug("CodeGenerator析构，清理资源")
            self.unload_model()
