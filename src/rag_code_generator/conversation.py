"""
对话管理模块 - 支持多轮对话和持久化存储
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger


class Message:
    """对话消息"""
    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.role = role  # user, assistant, system
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {})
        )


class Conversation:
    """对话会话"""
    def __init__(
        self,
        conversation_id: Optional[str] = None,
        title: str = "新对话",
        system_prompt: Optional[str] = None
    ):
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.title = title
        self.system_prompt = system_prompt or "You are a professional AI programmer who will carefully think, thoroughly analyze, and diligently fulfill all user requirements."
        self.messages: List[Message] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.metadata: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加消息"""
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
        
        # 自动更新标题（使用第一条用户消息）
        if role == "user" and self.title == "新对话" and len(self.messages) <= 2:
            self.title = content[:50] + ("..." if len(content) > 50 else "")
    
    def get_messages(self, include_system: bool = True) -> List[Dict]:
        """获取消息列表"""
        messages = []
        
        if include_system and self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        for msg in self.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def get_context_window(self, max_messages: int = 10) -> List[Dict]:
        """获取最近的N条消息作为上下文"""
        messages = []
        
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # 获取最近的消息
        recent_messages = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def clear_messages(self):
        """清空消息历史"""
        self.messages = []
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "system_prompt": self.system_prompt,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Conversation":
        """从字典创建"""
        conv = cls(
            conversation_id=data["conversation_id"],
            title=data.get("title", "新对话"),
            system_prompt=data.get("system_prompt")
        )
        conv.created_at = data.get("created_at", conv.created_at)
        conv.updated_at = data.get("updated_at", conv.updated_at)
        conv.metadata = data.get("metadata", {})
        
        for msg_data in data.get("messages", []):
            conv.messages.append(Message.from_dict(msg_data))
        
        return conv


class ConversationManager:
    """对话管理器 - 负责持久化存储"""
    def __init__(self, storage_dir: str = "./conversations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.conversations: Dict[str, Conversation] = {}
        
        logger.info(f"对话管理器初始化: {storage_dir}")
        self._load_all_conversations()
    
    def _get_conversation_path(self, conversation_id: str) -> Path:
        """获取对话文件路径"""
        return self.storage_dir / f"{conversation_id}.json"
    
    def _load_all_conversations(self):
        """加载所有对话"""
        count = 0
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conv = Conversation.from_dict(data)
                self.conversations[conv.conversation_id] = conv
                count += 1
            except Exception as e:
                logger.error(f"加载对话失败 {file_path}: {e}")
        
        logger.info(f"加载了 {count} 个历史对话")
    
    def create_conversation(
        self,
        title: str = "新对话",
        system_prompt: Optional[str] = None
    ) -> Conversation:
        """创建新对话"""
        conv = Conversation(title=title, system_prompt=system_prompt)
        self.conversations[conv.conversation_id] = conv
        self._save_conversation(conv)
        
        logger.info(f"创建新对话: {conv.conversation_id}")
        return conv
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        return self.conversations.get(conversation_id)
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """列出所有对话（按更新时间排序）"""
        conversations = sorted(
            self.conversations.values(),
            key=lambda x: x.updated_at,
            reverse=True
        )
        
        return [
            {
                "conversation_id": conv.conversation_id,
                "title": conv.title,
                "message_count": len(conv.messages),
                "created_at": conv.created_at,
                "updated_at": conv.updated_at
            }
            for conv in conversations[:limit]
        ]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id not in self.conversations:
            return False
        
        # 删除文件
        file_path = self._get_conversation_path(conversation_id)
        if file_path.exists():
            file_path.unlink()
        
        # 从内存中删除
        del self.conversations[conversation_id]
        
        logger.info(f"删除对话: {conversation_id}")
        return True
    
    def _save_conversation(self, conversation: Conversation):
        """保存对话到文件"""
        file_path = self._get_conversation_path(conversation.conversation_id)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存对话失败: {e}")
    
    def save_all(self):
        """保存所有对话"""
        for conv in self.conversations.values():
            self._save_conversation(conv)
        
        logger.info(f"保存了 {len(self.conversations)} 个对话")
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        auto_save: bool = True
    ):
        """向对话添加消息"""
        conv = self.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"对话不存在: {conversation_id}")
        
        conv.add_message(role, content, metadata)
        
        if auto_save:
            self._save_conversation(conv)
    
    def get_conversation_history(
        self,
        conversation_id: str,
        max_messages: Optional[int] = None
    ) -> List[Dict]:
        """获取对话历史"""
        conv = self.get_conversation(conversation_id)
        if not conv:
            return []
        
        if max_messages:
            return conv.get_context_window(max_messages)
        else:
            return conv.get_messages()
