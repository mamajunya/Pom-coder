"""
Ollama代码生成器模块

使用Ollama API进行代码生成，支持RTX 5060 (Blackwell架构)
"""

import requests
import json
from typing import Optional, Dict, Any, List
from loguru import logger
import time


class OllamaGeneratorError(Exception):
    """Ollama生成器错误"""
    pass


class OllamaGenerator:
    """Ollama代码生成器
    
    使用Ollama API进行代码生成，自动处理4bit量化
    """
    
    def __init__(
        self,
        model_name: str = "deepseek-coder:6.7b",
        base_url: str = "http://localhost:11434",
        timeout: int = 60
    ):
        """
        初始化Ollama生成器
        
        Args:
            model_name: Ollama模型名称
            base_url: Ollama API地址
            timeout: 请求超时时间（秒）
        """
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        logger.info(f"初始化OllamaGenerator: {model_name}")
        
        # 检查Ollama服务
        self._check_ollama_service()
        
        # 检查模型是否存在
        self._check_model_exists()
    
    def _check_ollama_service(self) -> None:
        """检查Ollama服务是否运行"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✓ Ollama服务运行正常")
            else:
                raise OllamaGeneratorError(
                    f"Ollama服务响应异常: {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            raise OllamaGeneratorError(
                "无法连接到Ollama服务\n"
                "请确保Ollama已安装并运行\n"
                "安装: https://ollama.ai/download\n"
                "启动: ollama serve"
            )
        except Exception as e:
            raise OllamaGeneratorError(f"检查Ollama服务失败: {str(e)}")
    
    def _check_model_exists(self) -> None:
        """检查模型是否已下载"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                
                if self.model_name in models:
                    logger.info(f"✓ 模型已存在: {self.model_name}")
                else:
                    logger.warning(
                        f"模型 {self.model_name} 未下载\n"
                        f"首次使用时会自动下载\n"
                        f"或手动下载: ollama pull {self.model_name}"
                    )
        except Exception as e:
            logger.warning(f"检查模型失败: {str(e)}")
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        stream: bool = False,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        生成代码
        
        Args:
            prompt: 输入提示
            temperature: 生成温度
            max_tokens: 最大生成token数
            stream: 是否流式输出（此方法不支持，使用generate_stream）
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的代码
            
        Raises:
            OllamaGeneratorError: 生成失败
        """
        if not prompt or len(prompt.strip()) == 0:
            raise ValueError("Prompt不能为空")
        
        logger.info(f"开始生成代码，model={self.model_name}, temp={temperature}")
        
        # 构造请求
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,  # 非流式
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise OllamaGeneratorError(
                    f"Ollama API错误: {response.status_code}\n{response.text}"
                )
            
            # 解析响应
            result = response.json()
            generated_text = result.get('response', '')
            
            duration = time.time() - start_time
            
            logger.info(
                f"代码生成完成，耗时: {duration:.2f}秒, "
                f"长度: {len(generated_text)} 字符"
            )
            
            return generated_text
        
        except requests.exceptions.Timeout:
            raise OllamaGeneratorError(f"生成超时（>{self.timeout}秒）")
        except requests.exceptions.RequestException as e:
            raise OllamaGeneratorError(f"请求失败: {str(e)}")
    
    def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        system_prompt: Optional[str] = None
    ):
        """
        流式生成代码
        
        Args:
            prompt: 输入提示
            temperature: 生成温度
            max_tokens: 最大生成token数
            system_prompt: 系统提示（可选）
            
        Yields:
            生成的文本片段
            
        Raises:
            OllamaGeneratorError: 生成失败
        """
        if not prompt or len(prompt.strip()) == 0:
            raise ValueError("Prompt不能为空")
        
        logger.info(f"开始流式生成代码，model={self.model_name}, temp={temperature}")
        
        # 构造请求
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,  # 流式
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise OllamaGeneratorError(
                    f"Ollama API错误: {response.status_code}\n{response.text}"
                )
            
            # 流式读取响应
            import json
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            yield chunk['response']
                    except json.JSONDecodeError:
                        continue
        
        except requests.exceptions.Timeout:
            raise OllamaGeneratorError(f"生成超时（>{self.timeout}秒）")
        except requests.exceptions.RequestException as e:
            raise OllamaGeneratorError(f"请求失败: {str(e)}")
        except Exception as e:
            raise OllamaGeneratorError(f"生成失败: {str(e)}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 512
    ) -> str:
        """
        聊天模式生成
        
        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "..."}]
            temperature: 生成温度
            max_tokens: 最大生成token数
            
        Returns:
            生成的回复
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise OllamaGeneratorError(
                    f"Ollama API错误: {response.status_code}\n{response.text}"
                )
            
            result = response.json()
            return result.get('message', {}).get('content', '')
        
        except Exception as e:
            raise OllamaGeneratorError(f"聊天失败: {str(e)}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        列出可用模型
        
        Returns:
            模型列表
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
            else:
                return []
        except Exception as e:
            logger.error(f"获取模型列表失败: {str(e)}")
            return []
    
    def pull_model(self, model_name: Optional[str] = None) -> bool:
        """
        下载模型
        
        Args:
            model_name: 模型名称，默认使用当前模型
            
        Returns:
            是否成功
        """
        model = model_name or self.model_name
        
        logger.info(f"开始下载模型: {model}")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                stream=True,
                timeout=600  # 10分钟超时
            )
            
            if response.status_code == 200:
                # 流式读取下载进度
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        status = data.get('status', '')
                        if status:
                            logger.info(f"  {status}")
                
                logger.info(f"✓ 模型下载完成: {model}")
                return True
            else:
                logger.error(f"下载失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"下载模型失败: {str(e)}")
            return False
