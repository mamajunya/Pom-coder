// 全局变量
let currentConversationId = null;
let conversationsLoaded = false;

// 多语言翻译
const translations = {
    zh: {
        tab_generate: '代码生成',
        tab_agent: 'AI对话',
        tab_slicer: '代码切片',
        tab_knowledge: '知识库管理',
        tab_api: 'API文档',
        tab_settings: '设置',
        settings_title: '设置',
        settings_language: '语言设置',
        settings_select_language: '选择语言：',
        settings_model: '模型设置',
        settings_current_model: '当前模型：',
        settings_model_hint: '输入Ollama模型名称，确保已通过 ollama pull 下载',
        settings_ollama_url: 'Ollama服务地址：',
        settings_save: '保存设置',
        settings_test_model: '测试模型',
        settings_system: '系统信息',
        settings_loading: '加载中...',
        settings_support: '支持项目',
        settings_support_text: '如果你喜欢这个项目，请给',
        settings_support_star: '点一颗 Star ⭐',
        api_title: 'API文档',
        api_generate_title: '代码生成API',
        api_conversation_title: '对话管理API'
    },
    en: {
        tab_generate: 'Code Generation',
        tab_agent: 'AI Chat',
        tab_slicer: 'Code Slicer',
        tab_knowledge: 'Knowledge Base',
        tab_api: 'API Docs',
        tab_settings: 'Settings',
        settings_title: 'Settings',
        settings_language: 'Language Settings',
        settings_select_language: 'Select Language:',
        settings_model: 'Model Settings',
        settings_current_model: 'Current Model:',
        settings_model_hint: 'Enter Ollama model name, ensure it is downloaded via ollama pull',
        settings_ollama_url: 'Ollama Service URL:',
        settings_save: 'Save Settings',
        settings_test_model: 'Test Model',
        settings_system: 'System Information',
        settings_loading: 'Loading...',
        settings_support: 'Support Project',
        settings_support_text: 'If you like this project, please give',
        settings_support_star: 'a Star ⭐',
        api_title: 'API Documentation',
        api_generate_title: 'Code Generation API',
        api_conversation_title: 'Conversation Management API'
    },
    ja: {
        tab_generate: 'コード生成',
        tab_agent: 'AIチャット',
        tab_slicer: 'コードスライサー',
        tab_knowledge: 'ナレッジベース',
        tab_api: 'APIドキュメント',
        tab_settings: '設定',
        settings_title: '設定',
        settings_language: '言語設定',
        settings_select_language: '言語を選択：',
        settings_model: 'モデル設定',
        settings_current_model: '現在のモデル：',
        settings_model_hint: 'Ollamaモデル名を入力してください（ollama pullでダウンロード済みであること）',
        settings_ollama_url: 'Ollamaサービスアドレス：',
        settings_save: '設定を保存',
        settings_test_model: 'モデルをテスト',
        settings_system: 'システム情報',
        settings_loading: '読み込み中...',
        settings_support: 'プロジェクトをサポート',
        settings_support_text: 'このプロジェクトが気に入ったら、',
        settings_support_star: 'にスターを付けてください ⭐',
        api_title: 'APIドキュメント',
        api_generate_title: 'コード生成API',
        api_conversation_title: '会話管理API'
    },
    ko: {
        tab_generate: '코드 생성',
        tab_agent: 'AI 채팅',
        tab_slicer: '코드 슬라이서',
        tab_knowledge: '지식 베이스',
        tab_api: 'API 문서',
        tab_settings: '설정',
        settings_title: '설정',
        settings_language: '언어 설정',
        settings_select_language: '언어 선택：',
        settings_model: '모델 설정',
        settings_current_model: '현재 모델：',
        settings_model_hint: 'Ollama 모델 이름을 입력하세요 (ollama pull로 다운로드 완료)',
        settings_ollama_url: 'Ollama 서비스 주소：',
        settings_save: '설정 저장',
        settings_test_model: '모델 테스트',
        settings_system: '시스템 정보',
        settings_loading: '로딩 중...',
        settings_support: '프로젝트 지원',
        settings_support_text: '이 프로젝트가 마음에 드신다면',
        settings_support_star: '에 스타를 눌러주세요 ⭐',
        api_title: 'API 문서',
        api_generate_title: '코드 생성 API',
        api_conversation_title: '대화 관리 API'
    },
    fr: {
        tab_generate: 'Génération de Code',
        tab_agent: 'Chat IA',
        tab_slicer: 'Découpeur de Code',
        tab_knowledge: 'Base de Connaissances',
        tab_api: 'Documentation API',
        tab_settings: 'Paramètres',
        settings_title: 'Paramètres',
        settings_language: 'Paramètres de Langue',
        settings_select_language: 'Sélectionner la langue：',
        settings_model: 'Paramètres du Modèle',
        settings_current_model: 'Modèle actuel：',
        settings_model_hint: 'Entrez le nom du modèle Ollama (assurez-vous qu\'il est téléchargé via ollama pull)',
        settings_ollama_url: 'URL du service Ollama：',
        settings_save: 'Enregistrer',
        settings_test_model: 'Tester le Modèle',
        settings_system: 'Informations Système',
        settings_loading: 'Chargement...',
        settings_support: 'Soutenir le Projet',
        settings_support_text: 'Si vous aimez ce projet, donnez une étoile à',
        settings_support_star: '⭐',
        api_title: 'Documentation API',
        api_generate_title: 'API de Génération de Code',
        api_conversation_title: 'API de Gestion des Conversations'
    },
    de: {
        tab_generate: 'Code-Generierung',
        tab_agent: 'KI-Chat',
        tab_slicer: 'Code-Slicer',
        tab_knowledge: 'Wissensdatenbank',
        tab_api: 'API-Dokumentation',
        tab_settings: 'Einstellungen',
        settings_title: 'Einstellungen',
        settings_language: 'Spracheinstellungen',
        settings_select_language: 'Sprache wählen：',
        settings_model: 'Modelleinstellungen',
        settings_current_model: 'Aktuelles Modell：',
        settings_model_hint: 'Geben Sie den Ollama-Modellnamen ein (stellen Sie sicher, dass er über ollama pull heruntergeladen wurde)',
        settings_ollama_url: 'Ollama-Dienst-URL：',
        settings_save: 'Einstellungen speichern',
        settings_test_model: 'Modell testen',
        settings_system: 'Systeminformationen',
        settings_loading: 'Wird geladen...',
        settings_support: 'Projekt unterstützen',
        settings_support_text: 'Wenn Ihnen dieses Projekt gefällt, geben Sie',
        settings_support_star: 'einen Stern ⭐',
        api_title: 'API-Dokumentation',
        api_generate_title: 'Code-Generierungs-API',
        api_conversation_title: 'Konversationsverwaltungs-API'
    },
    es: {
        tab_generate: 'Generación de Código',
        tab_agent: 'Chat IA',
        tab_slicer: 'Cortador de Código',
        tab_knowledge: 'Base de Conocimientos',
        tab_api: 'Documentación API',
        tab_settings: 'Configuración',
        settings_title: 'Configuración',
        settings_language: 'Configuración de Idioma',
        settings_select_language: 'Seleccionar idioma：',
        settings_model: 'Configuración del Modelo',
        settings_current_model: 'Modelo actual：',
        settings_model_hint: 'Ingrese el nombre del modelo Ollama (asegúrese de que esté descargado con ollama pull)',
        settings_ollama_url: 'URL del servicio Ollama：',
        settings_save: 'Guardar Configuración',
        settings_test_model: 'Probar Modelo',
        settings_system: 'Información del Sistema',
        settings_loading: 'Cargando...',
        settings_support: 'Apoyar el Proyecto',
        settings_support_text: 'Si te gusta este proyecto, dale una estrella a',
        settings_support_star: '⭐',
        api_title: 'Documentación API',
        api_generate_title: 'API de Generación de Código',
        api_conversation_title: 'API de Gestión de Conversaciones'
    },
    ru: {
        tab_generate: 'Генерация Кода',
        tab_agent: 'ИИ Чат',
        tab_slicer: 'Нарезка Кода',
        tab_knowledge: 'База Знаний',
        tab_api: 'Документация API',
        tab_settings: 'Настройки',
        settings_title: 'Настройки',
        settings_language: 'Настройки Языка',
        settings_select_language: 'Выберите язык：',
        settings_model: 'Настройки Модели',
        settings_current_model: 'Текущая модель：',
        settings_model_hint: 'Введите имя модели Ollama (убедитесь, что она загружена через ollama pull)',
        settings_ollama_url: 'URL сервиса Ollama：',
        settings_save: 'Сохранить Настройки',
        settings_test_model: 'Тестировать Модель',
        settings_system: 'Системная Информация',
        settings_loading: 'Загрузка...',
        settings_support: 'Поддержать Проект',
        settings_support_text: 'Если вам нравится этот проект, поставьте звезду',
        settings_support_star: '⭐',
        api_title: 'Документация API',
        api_generate_title: 'API Генерации Кода',
        api_conversation_title: 'API Управления Беседами'
    }
};

// 当前语言
let currentLanguage = localStorage.getItem('language') || 'zh';

// 切换语言
function changeLanguage() {
    const select = document.getElementById('language-select');
    currentLanguage = select.value;
    localStorage.setItem('language', currentLanguage);
    applyTranslations();
}

// 应用翻译
function applyTranslations() {
    const trans = translations[currentLanguage];
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (trans[key]) {
            element.textContent = trans[key];
        }
    });
}

// 标签切换
function switchTab(tabName) {
    const clickedTab = event ? event.target : null;
    
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    if (clickedTab) {
        clickedTab.classList.add('active');
    }
    
    if (tabName === 'agent' && !conversationsLoaded) {
        loadConversations();
        conversationsLoaded = true;
    }
    if (tabName === 'knowledge') {
        loadKnowledgeBaseInfo();
    }
    if (tabName === 'settings') {
        loadSettings();
        loadSystemInfo();
    }
}

// 代码生成
async function generateCode() {
    const query = document.getElementById('query').value.trim();
    if (!query) {
        alert('请输入需求描述');
        return;
    }
    
    const temperature = parseFloat(document.getElementById('temperature').value);
    const maxTokens = parseInt(document.getElementById('max_tokens').value);
    const resultBox = document.getElementById('generate-result');
    const codeElement = document.getElementById('generated-code');
    
    try {
        resultBox.style.display = 'block';
        codeElement.textContent = '生成中...';
        
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, temperature, max_tokens: maxTokens })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        codeElement.textContent = data.code;
        hljs.highlightElement(codeElement);
    } catch (error) {
        codeElement.textContent = `错误: ${error.message}`;
    }
}

// 加载对话列表
async function loadConversations() {
    try {
        const response = await fetch('/api/conversations/list?limit=50');
        const data = await response.json();
        const listElement = document.getElementById('conversation-list');
        listElement.innerHTML = '';
        
        if (data.conversations && data.conversations.length > 0) {
            data.conversations.forEach(conv => {
                const item = document.createElement('div');
                item.className = 'conversation-item';
                item.textContent = conv.title;
                item.dataset.conversationId = conv.conversation_id; // 保存ID
                
                // 左键点击：加载对话
                item.onclick = function() {
                    loadConversation(conv.conversation_id, this);
                };
                
                // ✅ 右键点击：显示删除菜单
                item.oncontextmenu = function(e) {
                    e.preventDefault(); // 阻止默认右键菜单
                    showConversationContextMenu(e, conv.conversation_id, conv.title);
                    return false;
                };
                
                listElement.appendChild(item);
            });
            
            if (!currentConversationId) {
                const firstItem = listElement.firstChild;
                loadConversation(data.conversations[0].conversation_id, firstItem);
            }
        }
    } catch (error) {
        console.error('加载对话列表失败:', error);
    }
}

// 创建新对话
async function createNewConversation() {
    try {
        const response = await fetch('/api/conversations/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: `对话 ${new Date().toLocaleString()}`,
                system_prompt: '你是一个友好的AI助手，可以帮助用户解答问题、编写代码、提供建议。'
            })
        });
        
        const data = await response.json();
        currentConversationId = data.conversation_id;
        await loadConversations();
        document.getElementById('chat-messages').innerHTML = '';
        document.getElementById('current-conversation-title').textContent = data.title;
    } catch (error) {
        alert('创建对话失败: ' + error.message);
    }
}

// 加载对话（修复event.target问题）
async function loadConversation(conversationId, targetElement) {
    try {
        const response = await fetch(`/api/conversations/${conversationId}`);
        const data = await response.json();
        
        currentConversationId = conversationId;
        document.getElementById('current-conversation-title').textContent = data.title;
        
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';
        
        data.messages.forEach(msg => {
            appendMessage(msg.role, msg.content, false);
        });
        
        // 更新选中状态
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        if (targetElement) {
            targetElement.classList.add('active');
        }
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        console.error('加载对话失败:', error);
    }
}

// ✅ 显示对话右键菜单
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
    deleteOption.innerHTML = '删除对话';
    deleteOption.onclick = function() {
        deleteConversation(conversationId, conversationTitle);
        menu.remove();
    };
    
    // 重命名选项（可选）
    const renameOption = document.createElement('div');
    renameOption.className = 'context-menu-item';
    renameOption.innerHTML = '重命名';
    renameOption.onclick = function() {
        renameConversation(conversationId, conversationTitle);
        menu.remove();
    };
    
    menu.appendChild(deleteOption);
    menu.appendChild(renameOption);
    document.body.appendChild(menu);
    
    // 点击其他地方关闭菜单
    setTimeout(() => {
        document.addEventListener('click', function closeMenu() {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        });
    }, 0);
}

// ✅ 删除对话
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
        console.error('删除对话失败:', error);
    }
}

// ✅ 重命名对话
async function renameConversation(conversationId, oldTitle) {
    const newTitle = prompt('请输入新的对话标题：', oldTitle);
    
    if (!newTitle || newTitle === oldTitle) {
        return;
    }
    
    try {
        // 注意：需要后端支持重命名API
        // 这里暂时使用一个占位实现
        alert('重命名功能待实现');
        // TODO: 实现重命名API
        
    } catch (error) {
        alert('重命名失败: ' + error.message);
        console.error('重命名对话失败:', error);
    }
}

// ✅ 显示Toast提示
function showToast(message, duration = 2000) {
    // 移除已存在的toast
    const existingToast = document.getElementById('toast-message');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 创建toast
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

// 发送消息（非流式，简化版）
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    if (!currentConversationId) {
        alert('请先创建或选择一个对话');
        return;
    }
    
    input.value = '';
    appendMessage('user', message, false);
    
    const useRag = document.getElementById('use-rag').checked;
    const temperature = parseFloat(document.getElementById('chat-temperature').value);
    
    const assistantDiv = appendMessage('assistant', '思考中...', false);
    const contentDiv = assistantDiv.querySelector('.message-content');
    
    try {
        const response = await fetch('/api/conversations/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message: message,
                temperature: temperature,
                max_tokens: 2048,
                use_rag: useRag,
                stream: false
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        contentDiv.innerHTML = marked.parse(data.response);
        contentDiv.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });
        
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
    } catch (error) {
        contentDiv.textContent = '错误: ' + error.message;
        console.error('发送消息失败:', error);
    }
}

// 添加消息到界面
function appendMessage(role, content, isPlaceholder) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (content) {
        contentDiv.innerHTML = marked.parse(content);
        contentDiv.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });
    }
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageDiv;
}

// 清空对话
async function clearCurrentConversation() {
    if (!currentConversationId) {
        alert('请先选择一个对话');
        return;
    }
    
    if (!confirm('确定要清空当前对话的历史记录吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/conversations/${currentConversationId}/clear`, {
            method: 'POST'
        });
        
        if (response.ok) {
            document.getElementById('chat-messages').innerHTML = '';
            alert('对话历史已清空');
        }
    } catch (error) {
        alert('清空失败: ' + error.message);
    }
}

// 代码切片
async function sliceCode() {
    const directory = document.getElementById('slice-directory').value.trim();
    if (!directory) {
        alert('请输入目录路径');
        return;
    }
    
    const extensions = [];
    document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked').forEach(cb => {
        extensions.push(cb.value);
    });
    
    if (extensions.length === 0) {
        alert('请至少选择一种文件类型');
        return;
    }
    
    const maxFiles = parseInt(document.getElementById('max-files').value);
    const maxTokens = parseInt(document.getElementById('max-tokens').value);
    const minTokens = parseInt(document.getElementById('min-tokens').value);
    const overlapTokens = parseInt(document.getElementById('overlap-tokens').value);
    const strategy = document.getElementById('slice-strategy').value;
    
    try {
        const response = await fetch('/api/code-slicer/slice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                directory: directory,
                extensions: extensions,
                max_files: maxFiles,
                max_tokens: maxTokens,
                min_tokens: minTokens,
                overlap_tokens: overlapTokens,
                strategy: strategy
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        document.getElementById('slice-status').style.display = 'block';
        pollSliceStatus();
    } catch (error) {
        alert('切片失败: ' + error.message);
    }
}

async function pollSliceStatus() {
    const progressBar = document.getElementById('slice-progress');
    const messageElement = document.getElementById('slice-message');
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch('/api/code-slicer/status');
            const data = await response.json();
            
            progressBar.style.width = data.progress + '%';
            messageElement.textContent = `${data.message} (${data.slices || 0} 个切片)`;
            
            if (data.status === 'completed') {
                clearInterval(interval);
                messageElement.textContent = `✓ ${data.message} - 共 ${data.slices} 个切片`;
            } else if (data.status === 'error') {
                clearInterval(interval);
                messageElement.textContent = `✗ 错误: ${data.message}`;
            }
        } catch (error) {
            clearInterval(interval);
            messageElement.textContent = '获取状态失败';
        }
    }, 1000);
}

// 知识库管理
async function loadKnowledgeBaseInfo() {
    try {
        const response = await fetch('/api/system/info');
        const data = await response.json();
        const infoElement = document.getElementById('kb-info');
        
        if (data.knowledge_base_loaded) {
            infoElement.innerHTML = `
                <p>✓ 知识库已加载</p>
                <p>代码片段数量: ${data.knowledge_base_size || 0}</p>
                <p>Embedding模型: sentence-transformers/all-MiniLM-L6-v2</p>
            `;
        } else {
            infoElement.innerHTML = '<p>✗ 知识库未加载</p>';
        }
    } catch (error) {
        document.getElementById('kb-info').innerHTML = '<p>✗ 获取状态失败</p>';
    }
}

async function buildKnowledgeBase() {
    const fileInput = document.getElementById('kb-file');
    if (!fileInput.files.length) {
        alert('请选择切片文件');
        return;
    }
    
    const useNpu = document.getElementById('use-npu').checked;
    const appendMode = document.querySelector('input[name="import-mode"]:checked').value === 'append';
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('use_npu', useNpu);
    formData.append('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2');
    formData.append('append_mode', appendMode);
    
    try {
        const response = await fetch('/api/knowledge-base/build', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        document.getElementById('kb-status').style.display = 'block';
        pollKBStatus();
    } catch (error) {
        alert('构建失败: ' + error.message);
    }
}

// ✅ 清除知识库
async function clearKnowledgeBase() {
    if (!confirm('确定要清除知识库吗？\n\n这将删除所有embedding数据和索引文件，此操作不可恢复！')) {
        return;
    }
    
    try {
        const response = await fetch('/api/knowledge-base/clear', {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ ' + data.message + '\n\n已删除文件：\n' + data.deleted_files.join('\n'));
            // 刷新知识库状态
            loadKnowledgeBaseInfo();
        } else {
            alert('清除失败: ' + (data.message || '未知错误'));
        }
    } catch (error) {
        alert('清除失败: ' + error.message);
    }
}

async function pollKBStatus() {
    const progressBar = document.getElementById('kb-progress');
    const messageElement = document.getElementById('kb-message');
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch('/api/knowledge-base/status');
            const data = await response.json();
            
            progressBar.style.width = data.progress + '%';
            messageElement.textContent = data.message;
            
            if (data.status === 'completed') {
                clearInterval(interval);
                messageElement.textContent = '✓ ' + data.message;
                setTimeout(loadKnowledgeBaseInfo, 1000);
            } else if (data.status === 'error') {
                clearInterval(interval);
                messageElement.textContent = '✗ 错误: ' + data.message;
            }
        } catch (error) {
            clearInterval(interval);
            messageElement.textContent = '获取状态失败';
        }
    }, 1000);
}

// 页面加载完成
document.addEventListener('DOMContentLoaded', () => {
    console.log('pomCoder 前端已加载');
    
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true
    });
    
    // 加载语言设置
    document.getElementById('language-select').value = currentLanguage;
    applyTranslations();
    
    // 加载保存的设置
    loadSettings();
});

// 设置管理
function loadSettings() {
    const savedModel = localStorage.getItem('ollama_model') || 'deepseek-coder:6.7b';
    const savedUrl = localStorage.getItem('ollama_url') || 'http://localhost:11434';
    
    document.getElementById('current-model').value = savedModel;
    document.getElementById('ollama-url').value = savedUrl;
}

async function saveSettings() {
    const model = document.getElementById('current-model').value.trim();
    const url = document.getElementById('ollama-url').value.trim();
    
    if (!model || !url) {
        alert(currentLanguage === 'zh' ? '请填写完整信息' : 'Please fill in all fields');
        return;
    }
    
    try {
        const response = await fetch('/api/settings/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model_name: model,
                ollama_url: url
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('ollama_model', model);
            localStorage.setItem('ollama_url', url);
            alert(currentLanguage === 'zh' ? '✓ 设置已保存并应用' : '✓ Settings saved and applied');
            loadSystemInfo();
        } else {
            const errorMsg = currentLanguage === 'zh' ? 
                `保存失败\n\n${data.message}\n\n${data.error || ''}` : 
                `Save failed\n\n${data.message}\n\n${data.error || ''}`;
            alert(errorMsg);
        }
    } catch (error) {
        alert(currentLanguage === 'zh' ? `保存失败: ${error.message}` : `Save failed: ${error.message}`);
    }
}

async function testModel() {
    const model = document.getElementById('current-model').value.trim();
    
    if (!model) {
        alert(currentLanguage === 'zh' ? '请输入模型名称' : 'Please enter model name');
        return;
    }
    
    try {
        const response = await fetch('/api/settings/test-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: model })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(currentLanguage === 'zh' ? 
                `✓ 模型测试成功\n响应: ${data.response}` : 
                `✓ Model test successful\nResponse: ${data.response}`);
        } else {
            alert(currentLanguage === 'zh' ? 
                `✗ 模型测试失败\n${data.error}` : 
                `✗ Model test failed\n${data.error}`);
        }
    } catch (error) {
        alert(currentLanguage === 'zh' ? 
            `测试失败: ${error.message}` : 
            `Test failed: ${error.message}`);
    }
}

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system/info');
        const data = await response.json();
        const infoElement = document.getElementById('system-info');
        
        const kbStatus = data.knowledge_base_loaded ? 
            (currentLanguage === 'zh' ? '✓ 已加载' : '✓ Loaded') : 
            (currentLanguage === 'zh' ? '✗ 未加载' : '✗ Not loaded');
        
        const modelStatus = data.model_name ? 
            data.model_name : 
            (currentLanguage === 'zh' ? '未配置' : 'Not configured');
        
        infoElement.innerHTML = `
            <p><strong>${currentLanguage === 'zh' ? '当前模型' : 'Current Model'}:</strong> ${modelStatus}</p>
            <p><strong>${currentLanguage === 'zh' ? '知识库状态' : 'Knowledge Base'}:</strong> ${kbStatus}</p>
            <p><strong>${currentLanguage === 'zh' ? '代码片段数量' : 'Code Snippets'}:</strong> ${data.knowledge_base_size || 0}</p>
            <p><strong>${currentLanguage === 'zh' ? '服务器版本' : 'Server Version'}:</strong> ${data.version || '3.0.0'}</p>
        `;
        
        // 如果模型未初始化，显示提示
        if (data.status === 'not_initialized') {
            const warningMsg = currentLanguage === 'zh' ? 
                '⚠️ 模型未初始化，请先配置并保存设置' : 
                '⚠️ Model not initialized, please configure and save settings first';
            infoElement.innerHTML = `<p style="color: #ff6b6b;">${warningMsg}</p>` + infoElement.innerHTML;
        }
    } catch (error) {
        document.getElementById('system-info').innerHTML = 
            `<p>${currentLanguage === 'zh' ? '✗ 获取系统信息失败' : '✗ Failed to load system info'}</p>`;
    }
}
