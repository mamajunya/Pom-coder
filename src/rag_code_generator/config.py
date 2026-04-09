"""配置管理模块

支持需求14.1和14.2：
- 通过YAML配置文件设置所有关键参数
- 启动时加载并验证配置文件
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from loguru import logger


class ConfigError(Exception):
    """配置错误异常"""
    pass


class Config:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config.yaml
        """
        if config_path is None:
            config_path = "config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        # 加载并验证配置
        self.load()
        self.validate()
    
    def load(self) -> None:
        """
        加载配置文件
        
        Raises:
            ConfigError: 配置文件不存在或格式错误
        """
        if not self.config_path.exists():
            raise ConfigError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 支持环境变量覆盖
            self._apply_env_overrides()
            
            logger.info(f"配置文件加载成功: {self.config_path}")
        
        except yaml.YAMLError as e:
            raise ConfigError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigError(f"加载配置文件失败: {e}")
    
    def validate(self) -> None:
        """
        验证配置文件的完整性和正确性
        
        Raises:
            ConfigError: 配置验证失败
        """
        required_sections = ["system", "models", "retrieval", "generation"]
        
        for section in required_sections:
            if section not in self.config:
                raise ConfigError(f"缺少必需的配置节: {section}")
        
        # 验证system配置
        self._validate_system()
        
        # 验证models配置
        self._validate_models()
        
        # 验证retrieval配置
        self._validate_retrieval()
        
        # 验证generation配置
        self._validate_generation()
        
        logger.info("配置验证通过")
    
    def _validate_system(self) -> None:
        """验证system配置"""
        system = self.config.get("system", {})
        
        if "device" not in system:
            raise ConfigError("system.device 未配置")
        
        valid_devices = ["cuda:0", "cpu", "npu"]
        if system["device"] not in valid_devices:
            raise ConfigError(f"system.device 必须是以下之一: {valid_devices}")
    
    def _validate_models(self) -> None:
        """验证models配置"""
        models = self.config.get("models", {})
        
        required_models = ["main_model", "embedding_model", "reranker_model"]
        for model in required_models:
            if model not in models:
                raise ConfigError(f"models.{model} 未配置")
    
    def _validate_retrieval(self) -> None:
        """验证retrieval配置"""
        retrieval = self.config.get("retrieval", {})
        
        required_params = ["embedding_top_k", "bm25_top_k", "final_top_k"]
        for param in required_params:
            if param not in retrieval:
                raise ConfigError(f"retrieval.{param} 未配置")
            
            value = retrieval[param]
            if not isinstance(value, int) or value <= 0:
                raise ConfigError(f"retrieval.{param} 必须是正整数")
    
    def _validate_generation(self) -> None:
        """验证generation配置"""
        generation = self.config.get("generation", {})
        
        if "temperature" in generation:
            temp = generation["temperature"]
            if not (0 <= temp <= 1.0):
                raise ConfigError("generation.temperature 必须在 [0, 1] 范围内")
        
        if "max_new_tokens" in generation:
            tokens = generation["max_new_tokens"]
            if not isinstance(tokens, int) or tokens <= 0:
                raise ConfigError("generation.max_new_tokens 必须是正整数")
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        # 支持通过环境变量覆盖配置
        env_mappings = {
            "RAG_DEVICE": ("system", "device"),
            "RAG_MODEL_PATH": ("models", "main_model", "path"),
            "RAG_TEMPERATURE": ("generation", "temperature"),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config_path, value)
                logger.info(f"环境变量覆盖: {env_var} -> {config_path}")
    
    def _set_nested_value(self, path: tuple, value: Any) -> None:
        """设置嵌套配置值"""
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 尝试转换类型
        last_key = path[-1]
        if last_key in current:
            original_type = type(current[last_key])
            try:
                value = original_type(value)
            except (ValueError, TypeError):
                pass
        
        current[last_key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键
        
        Args:
            key: 配置键，如 "system.device"
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.config[key]
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return key in self.config
