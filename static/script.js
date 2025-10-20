document.addEventListener('DOMContentLoaded', () => {
    // --- DOM 元素获取 ---
    const apiKeyInput = document.getElementById('api-key');
    const modelSelect = document.getElementById('model-select');
    const ratioSelect = document.getElementById('ratio-select');
    const promptInput = document.getElementById('prompt-input');
    const generateBtn = document.getElementById('generate-btn');
    const historyList = document.getElementById('history-list');
    const historyPlaceholder = document.getElementById('history-placeholder');
    const sortSelect = document.getElementById('sort-select');
    const previewPanel = document.getElementById('preview-panel');
    const previewPlaceholder = document.getElementById('preview-placeholder');
    const previewContent = document.getElementById('preview-content');
    const previewImage = document.getElementById('preview-image');
    const previewModel = document.getElementById('preview-model');
    const previewPrompt = document.getElementById('preview-prompt');

    let history = [];
    let activeTaskId = null;

    // --- 核心功能 ---

    // 从 localStorage 加载历史记录
    function loadHistory() {
        const savedHistory = localStorage.getItem('vidsme-history');
        history = savedHistory ? JSON.parse(savedHistory) : [];
        renderHistory();
    }

    // 保存历史记录到 localStorage
    function saveHistory() {
        localStorage.setItem('vidsme-history', JSON.stringify(history));
    }

    // 渲染历史记录列表
    function renderHistory() {
        historyPlaceholder.classList.toggle('hidden', history.length > 0);
        historyList.innerHTML = ''; // 清空现有列表

        const sortedHistory = [...history].sort((a, b) => {
            if (sortSelect.value === 'oldest') {
                return a.created - b.created;
            }
            return b.created - a.created; // 默认最新
        });

        sortedHistory.forEach(task => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.dataset.id = task.id;
            if (task.id === activeTaskId) {
                item.classList.add('active');
            }

            let thumbnailContent = '';
            if (task.status === 'processing') {
                thumbnailContent = '<div class="spinner"></div>';
            } else if (task.status === 'completed' && task.resultUrl) {
                thumbnailContent = `<img src="${task.resultUrl}" alt="thumbnail">`;
            }

            item.innerHTML = `
                <div class="thumbnail">${thumbnailContent}</div>
                <div class="info">
                    <div class="prompt">${task.prompt}</div>
                    <div class="meta">
                        <span>${task.model}</span> | <span>${new Date(task.created).toLocaleString()}</span>
                    </div>
                </div>
                <div class="status ${task.status}">${task.status}</div>
            `;
            item.addEventListener('click', () => showPreview(task.id));
            historyList.appendChild(item);
        });
    }

    // 显示任务预览
    function showPreview(taskId) {
        const task = history.find(t => t.id === taskId);
        if (!task) return;

        activeTaskId = taskId;
        renderHistory(); // 更新 active 状态

        previewPlaceholder.classList.add('hidden');
        previewContent.classList.remove('hidden');

        previewImage.src = task.resultUrl || 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; // 透明像素
        previewModel.textContent = task.model;
        previewPrompt.textContent = task.prompt;
    }

    // 添加并执行新任务
    async function addNewTask() {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert("请输入提示词！");
            return;
        }

        const task = {
            id: `task-${Date.now()}`,
            prompt: prompt,
            model: modelSelect.value,
            ratio: ratioSelect.value,
            status: 'processing', // processing, completed, failed
            created: Date.now(),
            resultUrl: null,
            error: null,
        };

        history.push(task);
        renderHistory();
        saveHistory();

        try {
            const apiKey = apiKeyInput.value.trim();
            const payload = {
                model: task.model,
                prompt: task.prompt,
                n: 1,
                size: task.ratio,
                response_format: "url"
            };

            const response = await fetch('/v1/images/generations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || '生成失败，未知错误。');

            // 更新任务状态为 completed
            task.status = 'completed';
            task.resultUrl = result.data[0].url;

        } catch (error) {
            // 更新任务状态为 failed
            task.status = 'failed';
            task.error = error.message;
            console.error(`任务 ${task.id} 失败:`, error);
        } finally {
            renderHistory();
            saveHistory();
            // 如果是当前预览的任务，则更新预览图
            if (task.id === activeTaskId) {
                showPreview(task.id);
            }
        }
    }

    // 加载可用模型
    async function populateModels() {
        modelSelect.innerHTML = '<option>正在加载...</option>';
        modelSelect.disabled = true;
        generateBtn.disabled = true;

        try {
            const apiKey = apiKeyInput.value.trim();
            if (!apiKey) throw new Error("请输入 API Key");

            const response = await fetch('/v1/models', {
                headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || '获取模型列表失败');
            
            modelSelect.innerHTML = '';
            result.data.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.id.charAt(0).toUpperCase() + model.id.slice(1);
                modelSelect.appendChild(option);
            });
            
            modelSelect.disabled = false;
            generateBtn.disabled = false;

        } catch (error) {
            modelSelect.innerHTML = `<option>加载失败</option>`;
            alert(`模型加载失败: ${error.message}`);
        }
    }

    // --- 事件监听 ---
    generateBtn.addEventListener('click', addNewTask);
    sortSelect.addEventListener('change', renderHistory);
    apiKeyInput.addEventListener('change', populateModels);

    // --- 初始化 ---
    loadHistory();
    populateModels();
});
