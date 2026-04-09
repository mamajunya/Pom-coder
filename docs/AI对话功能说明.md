# AI对话功能说明

## 功能概述

pomCoder现在集成了完整的AI对话功能，支持：

1. **多轮对话** - 保持上下文，连续对话
2. **永久存储** - 所有对话自动保存到本地
3. **会话管理** - 创建、切换、删除多个对话
4. **RAG增强** - 可选择是否使用知识库增强回复
5. **美观界面** - 类似ChatGPT的对话界面

## 使用方法

### Web界面

1. 启动服务器：`python start_full.py`
2. 打开浏览器：http://localhost:58761
3. 点击"AI对话"标签页
4. 点击"新建"创建对话
5. 输入消息，按Enter或点击"发送"

### 功能说明

#### 对话列表（左侧）
- 显示所有历史对话
- 点击对话可切换
- 显示消息数量
- 按更新时间排序

#### 对话区域（右侧）
- 显示完整对话历史
- 用户消息显示在右侧（深色）
- AI回复显示在左侧（浅色）
- 自动滚动到最新消息

#### 设置选项
- **使用RAG**：启用后会从知识库检索相关代码
- **温度**：控制生成的随机性（0-2，推荐0.2）

#### 操作按钮
- **新建**：创建新对话
- **清空**：清空当前对话历史
- **删除**：删除当前对话

## API接口

### 创建对话
```bash
POST /api/conversations/create
Content-Type: application/json

{
  "title": "新对话",
  "system_prompt": "你是一个专业的代码生成助手。"
}
```

### 列出对话
```bash
GET /api/conversations/list?limit=50
```

### 获取对话详情
```bash
GET /api/conversations/{conversation_id}
```

### 发送消息
```bash
POST /api/conversations/chat
Content-Type: application/json

{
  "conversation_id": "xxx",
  "message": "写一个快速排序",
  "temperature": 0.2,
  "max_tokens": 512,
  "use_rag": true
}
```

### 清空对话
```bash
POST /api/conversations/{conversation_id}/clear
```

### 删除对话
```bash
DELETE /api/conversations/{conversation_id}
```

## 数据存储

### 存储位置
- 对话数据保存在：`./conversations/`
- 每个对话一个JSON文件：`{conversation_id}.json`

### 数据格式
```json
{
  "conversation_id": "uuid",
  "title": "对话标题",
  "system_prompt": "系统提示词",
  "messages": [
    {
      "role": "user",
      "content": "消息内容",
      "timestamp": "2026-04-04T21:00:00",
      "metadata": {}
    }
  ],
  "created_at": "2026-04-04T21:00:00",
  "updated_at": "2026-04-04T21:05:00",
  "metadata": {}
}
```

## 技术实现

### 核心模块
- `src/rag_code_generator/conversation.py` - 对话管理核心
- `app_full.py` - API端点和Web界面

### 关键类
- **Message** - 单条消息
- **Conversation** - 对话会话
- **ConversationManager** - 对话管理器

### 特性
1. **自动保存** - 每次添加消息自动保存
2. **去重机制** - 基于UUID避免重复
3. **上下文窗口** - 支持限制历史消息数量
4. **元数据支持** - 可附加额外信息

## 使用场景

### 1. 代码学习
- 连续提问学习某个技术
- AI会记住之前的对话内容
- 可以深入探讨某个主题

### 2. 项目开发
- 为每个项目创建独立对话
- 持续讨论设计和实现
- 历史记录永久保存

### 3. 代码调试
- 描述问题，获取解决方案
- 根据反馈继续优化
- 保留完整调试过程

## 注意事项

1. **存储空间** - 对话会持续累积，定期清理不需要的对话
2. **上下文长度** - 过长的对话可能影响性能
3. **RAG开关** - 简单问题可关闭RAG提高速度
4. **温度设置** - 代码生成建议使用较低温度（0.1-0.3）

## 快捷键

- **Enter** - 发送消息
- **Shift+Enter** - 换行

## 未来计划

- [ ] 导出对话为Markdown
- [ ] 对话搜索功能
- [ ] 对话标签分类
- [ ] 多模态支持（图片、文件）
- [ ] 对话分享功能
