# AI对话右键删除功能

## 📋 功能说明

为AI对话助手添加右键菜单功能，支持快速删除和重命名对话。

## ✨ 新增功能

### 1. 右键菜单

**触发方式**：在对话列表中的任意对话项上点击鼠标右键

**菜单选项**：
- 🗑️ **删除对话** - 删除选中的对话（不可恢复）
- ✏️ **重命名** - 重命名对话标题（待实现）

### 2. 删除确认

- 点击"删除对话"后会弹出确认对话框
- 显示对话标题，防止误删
- 确认后立即删除，无法恢复

### 3. 视觉提示

- 鼠标悬停在对话项上时，右侧显示"右键删除"提示
- 右键菜单采用现代化设计，带阴影和圆角
- 删除成功后显示Toast提示

## 🎯 使用方法

### 删除对话

```
1. 在对话列表中找到要删除的对话
2. 右键点击该对话项
3. 在弹出菜单中点击"🗑️ 删除对话"
4. 确认删除
5. 对话被删除，列表自动刷新
```

### 视觉反馈

- **悬停提示**：鼠标悬停时显示"右键删除"
- **右键菜单**：点击右键显示操作菜单
- **确认对话框**：删除前二次确认
- **Toast提示**：删除成功后显示"✓ 对话已删除"

## 🔧 技术实现

### 前端实现

#### 1. 修改对话列表加载（`static/app.js`）

```javascript
async function loadConversations() {
    // ... 加载对话列表 ...
    
    data.conversations.forEach(conv => {
        const item = document.createElement('div');
        item.className = 'conversation-item';
        item.textContent = conv.title;
        item.dataset.conversationId = conv.conversation_id;
        
        // 左键点击：加载对话
        item.onclick = function() {
            loadConversation(conv.conversation_id, this);
        };
        
        // ✅ 右键点击：显示删除菜单
        item.oncontextmenu = function(e) {
            e.preventDefault();
            showConversationContextMenu(e, conv.conversation_id, conv.title);
            return false;
        };
        
        listElement.appendChild(item);
    });
}
```

#### 2. 显示右键菜单

```javascript
function showConversationContextMenu(event, conversationId, conversationTitle) {
    // 移除已存在的菜单
    const existingMenu = document.getElementById('conversation-context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // 创建右键菜单
    const menu = document.createElement('div');
    menu.id = 'conversation-context-menu';
    menu.className = 'context-menu';
    menu.style.position = 'fixed';
    menu.style.left = event.clientX + 'px';
    menu.style.top = event.clientY + 'px';
    
    // 删除选项
    const deleteOption = document.createElement('div');
    deleteOption.className = 'context-menu-item';
    deleteOption.innerHTML = '🗑️ 删除对话';
    deleteOption.onclick = function() {
        deleteConversation(conversationId, conversationTitle);
        menu.remove();
    };
    
    menu.appendChild(deleteOption);
    document.body.appendChild(menu);
    
    // 点击其他地方关闭菜单
    setTimeout(() => {
        document.addEventListener('click', function closeMenu() {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        });
    }, 0);
}
```

#### 3. 删除对话

```javascript
async function deleteConversation(conversationId, conversationTitle) {
    if (!confirm(`确定要删除对话"${conversationTitle}"吗？\n\n此操作不可恢复！`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/conversations/${conversationId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        // 如果删除的是当前对话，清空聊天区域
        if (currentConversationId === conversationId) {
            currentConversationId = null;
            document.getElementById('chat-messages').innerHTML = '';
            document.getElementById('current-conversation-title').textContent = '请选择或创建对话';
        }
        
        // 重新加载对话列表
        await loadConversations();
        
        // 显示成功提示
        showToast('✓ 对话已删除');
        
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}
```

#### 4. Toast提示

```javascript
function showToast(message, duration = 2000) {
    const toast = document.createElement('div');
    toast.id = 'toast-message';
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 自动隐藏
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, duration);
}
```

### CSS样式（`static/styles.css`）

```css
/* 右键菜单样式 */
.context-menu {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 4px 0;
    min-width: 150px;
    z-index: 10000;
}

.context-menu-item {
    padding: 10px 16px;
    cursor: pointer;
    transition: background 0.2s;
    font-size: 14px;
    color: #333;
}

.context-menu-item:hover {
    background: #f5f5f5;
}

/* Toast提示样式 */
.toast {
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: #333;
    color: #fff;
    padding: 12px 24px;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    z-index: 10001;
    opacity: 0;
    transition: all 0.3s ease;
}

.toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}

/* 对话项悬停提示 */
.conversation-item::after {
    content: '右键删除';
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    color: #999;
    opacity: 0;
    transition: opacity 0.2s;
}

.conversation-item:hover::after {
    opacity: 1;
}
```

### 后端API（已存在）

使用现有的删除对话API：

```
DELETE /api/conversations/{conversation_id}
```

**响应**：
```json
{
    "message": "对话已删除"
}
```

## 🎨 用户体验

### 交互流程

```
悬停对话项
    ↓
显示"右键删除"提示
    ↓
右键点击
    ↓
显示菜单
    ↓
点击"删除对话"
    ↓
确认对话框
    ↓
删除成功
    ↓
Toast提示
    ↓
列表刷新
```

### 视觉反馈

1. **悬停状态**
   - 背景变色
   - 显示"右键删除"提示

2. **右键菜单**
   - 跟随鼠标位置
   - 现代化设计
   - 平滑动画

3. **删除确认**
   - 显示对话标题
   - 明确提示不可恢复

4. **成功提示**
   - Toast消息
   - 自动消失
   - 平滑动画

## 📊 功能对比

| 操作 | 旧方式 | 新方式 |
|------|--------|--------|
| 删除对话 | 无法删除 | 右键菜单删除 |
| 操作步骤 | - | 2步（右键+确认） |
| 视觉反馈 | - | 悬停提示+Toast |
| 安全性 | - | 二次确认 |

## ⚠️ 注意事项

### 1. 删除不可恢复

- 删除操作会永久删除对话及其所有消息
- 删除前会显示确认对话框
- 建议重要对话定期导出备份

### 2. 当前对话处理

- 如果删除的是当前正在查看的对话
- 聊天区域会自动清空
- 标题显示"请选择或创建对话"

### 3. 菜单自动关闭

- 点击菜单外的任意位置，菜单自动关闭
- 点击菜单项后，菜单自动关闭

### 4. 浏览器兼容性

- 支持所有现代浏览器
- 使用标准的`oncontextmenu`事件
- CSS使用标准属性

## 🔮 未来扩展

### 1. 重命名功能

**当前状态**：菜单中已添加"✏️ 重命名"选项，但功能待实现

**实现计划**：
```javascript
async function renameConversation(conversationId, oldTitle) {
    const newTitle = prompt('请输入新的对话标题：', oldTitle);
    
    if (!newTitle || newTitle === oldTitle) {
        return;
    }
    
    try {
        // 需要后端支持 PATCH /api/conversations/{id}
        const response = await fetch(`/api/conversations/${conversationId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        await loadConversations();
        showToast('✓ 对话已重命名');
        
    } catch (error) {
        alert('重命名失败: ' + error.message);
    }
}
```

### 2. 更多菜单选项

- 📋 **复制对话** - 复制对话内容
- 📤 **导出对话** - 导出为JSON/Markdown
- 📌 **置顶对话** - 固定在列表顶部
- 🏷️ **添加标签** - 对话分类管理

### 3. 批量操作

- 多选对话
- 批量删除
- 批量导出

### 4. 拖拽排序

- 拖拽对话项调整顺序
- 保存自定义排序

## 🧪 测试建议

### 功能测试

```
1. 创建多个测试对话
2. 右键点击对话项，验证菜单显示
3. 点击"删除对话"，验证确认对话框
4. 确认删除，验证对话被删除
5. 验证Toast提示显示
6. 验证列表自动刷新
7. 删除当前对话，验证聊天区域清空
```

### 边界测试

```
1. 只有一个对话时删除
2. 删除后立即创建新对话
3. 快速连续删除多个对话
4. 在菜单外点击，验证菜单关闭
5. 取消删除确认
```

### 兼容性测试

```
1. Chrome浏览器
2. Firefox浏览器
3. Safari浏览器
4. Edge浏览器
5. 移动端浏览器
```

## 📝 版本信息

- **版本**：V3.6.1
- **发布日期**：2026-04-10
- **影响文件**：
  - `static/app.js` - 添加右键菜单和删除功能
  - `static/styles.css` - 添加菜单和Toast样式

## 🔗 相关文档

- [AI对话功能说明](./AI对话功能说明.md)
- [V3.6 知识库自动重载功能](./V3.6_知识库自动重载功能.md)

## 📞 常见问题

**Q: 删除的对话可以恢复吗？**  
A: 不可以，删除操作是永久的，建议删除前确认

**Q: 为什么没有批量删除？**  
A: 当前版本暂不支持，未来版本会添加

**Q: 重命名功能什么时候实现？**  
A: 需要后端API支持，计划在下个版本实现

**Q: 右键菜单可以自定义吗？**  
A: 当前不支持，但代码结构支持扩展

**Q: 移动端如何删除对话？**  
A: 移动端可以长按对话项触发菜单（需要测试）
