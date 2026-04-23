/**
 * AiEdToolsH 生成过程页面 - 双模式：默认流程 / 自定义模型分步执行
 */
console.log('[generate.js] 脚本已加载 v2');

// ========== 全局状态 ==========
let mode = '';              // 'default' | 'custom'
let query = '';             // 用户查询
let startTime = 0;          // 开始时间
let analysisResult = null;  // 学科分析结果
let dslResult = null;       // DSL生成结果
let htmlChunks = [];        // HTML代码收集
let currentProvider = '';   // 当前使用的模型

// ========== 辅助函数 ==========

/**
 * HTML转义函数，防止XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 获取已过去时间（秒）
 */
function getElapsed() {
    return ((Date.now() - startTime) / 1000).toFixed(1);
}

/**
 * 更新节点图标状态
 * @param {string} nodeId - 节点ID (analysis, dsl, runtime, html, complete)
 * @param {string} status - 状态 (waiting, running, done, error)
 */
function updateNodeIcon(nodeId, status) {
    const node = document.getElementById(`node-${nodeId}`);
    if (!node) return;
    
    const icon = node.querySelector('.node-icon');
    if (!icon) return;
    
    // 移除所有状态类
    icon.classList.remove('waiting', 'running', 'done', 'error');
    icon.classList.remove('bg-gray-100', 'text-gray-400');
    icon.classList.remove('bg-blue-100', 'text-blue-600');
    icon.classList.remove('bg-green-100', 'text-green-600');
    icon.classList.remove('bg-red-100', 'text-red-600');
    
    // 根据状态设置样式和图标
    if (status === 'running') {
        icon.classList.add('bg-blue-100', 'text-blue-600', 'running');
        icon.innerHTML = '<i class="fa-solid fa-spinner animate-spin-slow text-lg"></i>';
    } else if (status === 'done') {
        icon.classList.add('bg-green-100', 'text-green-600', 'done');
        icon.innerHTML = '<i class="fa-solid fa-check text-lg"></i>';
    } else if (status === 'error') {
        icon.classList.add('bg-red-100', 'text-red-600', 'error');
        icon.innerHTML = '<i class="fa-solid fa-xmark text-lg"></i>';
    } else {
        // waiting
        icon.classList.add('bg-gray-100', 'text-gray-400', 'waiting');
        const iconMap = {
            'analysis': 'fa-magnifying-glass',
            'dsl': 'fa-code',
            'runtime': 'fa-gears',
            'html': 'fa-file-code',
            'complete': 'fa-circle-check'
        };
        icon.innerHTML = `<i class="fa-solid ${iconMap[nodeId] || 'fa-circle'} text-lg"></i>`;
    }
}

/**
 * 设置节点时间/状态文本
 */
function setNodeTime(nodeId, text) {
    const node = document.getElementById(`node-${nodeId}`);
    if (!node) return;
    const el = node.querySelector('.node-time');
    if (el) el.textContent = text;
}

/**
 * 设置节点详情内容
 */
function setNodeDetails(nodeId, html, show = true) {
    const node = document.getElementById(`node-${nodeId}`);
    if (!node) return;
    const el = node.querySelector('.node-details');
    if (el) {
        el.innerHTML = html;
        if (show) {
            el.classList.remove('hidden');
        }
    }
}

/**
 * 追加代码到预览区
 */
function appendCode(text) {
    const codeEl = document.getElementById('code-preview');
    if (codeEl) {
        codeEl.textContent += text;
        codeEl.scrollTop = codeEl.scrollHeight;
    }
    // 更新字符计数
    const counterEl = document.getElementById('char-count');
    if (counterEl) {
        counterEl.textContent = htmlChunks.join('').length;
    }
}

/**
 * 显示错误信息
 */
function showError(message) {
    const errDiv = document.getElementById('error-message');
    const errText = document.getElementById('error-text');
    if (errDiv && errText) {
        errText.textContent = message;
        errDiv.classList.remove('hidden');
    }
}

/**
 * 激活查看结果按钮
 */
function activateViewButton(url) {
    const viewBtn = document.getElementById('view-result-btn');
    const hint = document.getElementById('result-hint');
    
    if (viewBtn) {
        viewBtn.disabled = false;
        viewBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        viewBtn.classList.add('hover:bg-blue-700', 'cursor-pointer');
        viewBtn.onclick = () => window.open(url, '_blank');
    }
    
    if (hint) {
        hint.textContent = '点击按钮在新窗口查看交互动画';
        hint.classList.remove('text-gray-400');
        hint.classList.add('text-green-600');
    }
}

// ========== 模式入口函数 ==========

/**
 * 启动默认模式
 */
function startDefaultMode() {
    mode = 'default';
    document.getElementById('mode-selector').style.display = 'none';
    document.getElementById('timeline-container').style.display = 'block';
    document.getElementById('page-title').textContent = '正在生成交互动画';
    startTime = Date.now();
    htmlChunks = [];
    runDefaultFlow();
}

/**
 * 启动自定义模式
 */
function startCustomMode() {
    mode = 'custom';
    document.getElementById('mode-selector').style.display = 'none';
    document.getElementById('timeline-container').style.display = 'block';
    document.getElementById('page-title').textContent = '自定义模型 - 分步生成';
    startTime = Date.now();
    htmlChunks = [];
    runAnalysis();
}

// ========== 默认模式逻辑 ==========

/**
 * 默认流程 - 调用 /api/generate
 */
async function runDefaultFlow() {
    updateNodeIcon('analysis', 'running');
    setNodeTime('analysis', '分析中...');
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        if (!response.ok) {
            throw new Error(`API错误: ${response.status} ${response.statusText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') continue;
                    try {
                        const event = JSON.parse(data);
                        handleDefaultEvent(event);
                    } catch (e) {
                        console.warn('JSON parse error:', e, data);
                    }
                }
            }
        }
    } catch (error) {
        console.error('生成失败:', error);
        showError(error.message || '网络错误，请检查后端服务是否运行');
        updateNodeIcon('analysis', 'error');
        setNodeTime('analysis', '错误');
    }
}

/**
 * 处理默认模式的SSE事件
 */
function handleDefaultEvent(event) {
    const elapsed = getElapsed();
    
    switch (event.event) {
        // ============ 阶段1: 学科分析 ============
        case 'analysis_start':
            updateNodeIcon('analysis', 'running');
            setNodeTime('analysis', '分析中...');
            break;
            
        case 'analysis_done':
            updateNodeIcon('analysis', 'done');
            setNodeTime('analysis', `${elapsed}s`);
            setNodeDetails('analysis', `
                <div class="grid grid-cols-2 gap-2 text-sm">
                    <div><span class="text-gray-500">学科:</span> <b class="text-gray-800">${event.subject || '-'}</b></div>
                    <div><span class="text-gray-500">分支:</span> <b class="text-gray-800">${event.branch || '-'}</b></div>
                    <div><span class="text-gray-500">场景:</span> <b class="text-gray-800">${event.scene_type || '-'}</b></div>
                    <div><span class="text-gray-500">置信度:</span> <b class="text-gray-800">${event.confidence ? (event.confidence * 100).toFixed(0) + '%' : '-'}</b></div>
                </div>
                ${event.keywords_matched && event.keywords_matched.length > 0 ? 
                    '<div class="mt-2 flex gap-1 flex-wrap">' + 
                    event.keywords_matched.map(k => `<span class="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">${k}</span>`).join('') + 
                    '</div>' : ''}
            `);
            updateNodeIcon('dsl', 'running');
            setNodeTime('dsl', '生成中...');
            break;
        
        // ============ 阶段2: DSL生成 ============
        case 'dsl_start':
            updateNodeIcon('dsl', 'running');
            setNodeTime('dsl', '生成中...');
            break;
            
        case 'dsl_provider':
            setNodeTime('dsl', `${event.provider} (${event.model || '...'})`);
            break;
            
        case 'dsl_prompt':
            if (event.full_messages && event.full_messages.length > 0) {
                let promptHtml = '<div class="mt-2 space-y-2">';
                event.full_messages.forEach(msg => {
                    const roleLabel = msg.role === 'system' ? 'System Prompt' : 'User Prompt';
                    const roleColor = msg.role === 'system' ? 'text-purple-500' : 'text-blue-500';
                    promptHtml += `
                    <details class="border border-gray-200 rounded">
                        <summary class="px-3 py-2 text-xs cursor-pointer hover:bg-gray-50 flex items-center justify-between">
                            <span class="${roleColor} font-medium">查看完整提示词（${roleLabel}）</span>
                            <span class="text-gray-400">${msg.content.length} 字符</span>
                        </summary>
                        <div class="relative">
                            <button onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent).then(()=>{this.textContent='已复制!';setTimeout(()=>{this.textContent='复制'},1500)})" 
                                    class="absolute right-2 top-2 px-2 py-1 bg-slate-600 text-white text-xs rounded hover:bg-slate-500 z-10">复制</button>
                            <pre class="p-3 bg-slate-800 text-slate-200 rounded-b text-xs overflow-auto max-h-96 whitespace-pre-wrap">${escapeHtml(msg.content)}</pre>
                        </div>
                    </details>`;
                });
                promptHtml += '</div>';
                setNodeDetails('dsl', promptHtml);
            }
            break;
            
        case 'dsl_done':
            updateNodeIcon('dsl', 'done');
            setNodeTime('dsl', `${elapsed}s · ${event.provider || ''}`);
            const dsl = event.dsl || {};
            setNodeDetails('dsl', `
                <div class="text-sm space-y-1">
                    <div><span class="text-gray-500">场景类型:</span> <b class="text-gray-800">${dsl.scene_type || ''}</b></div>
                    <div><span class="text-gray-500">主题:</span> <b class="text-gray-800">${dsl.topic || ''}</b></div>
                    <div><span class="text-gray-500">布局:</span> <span class="text-gray-700">${dsl.layout || ''}</span></div>
                </div>
                <details class="mt-2">
                    <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-600">查看完整DSL</summary>
                    <pre class="mt-1 p-2 bg-gray-50 rounded text-xs overflow-auto max-h-40">${JSON.stringify(dsl, null, 2)}</pre>
                </details>
            `);
            break;
            
        case 'dsl_fallback':
            setNodeDetails('dsl', `
                <div class="text-amber-600 text-sm mb-2">
                    <i class="fa-solid fa-triangle-exclamation mr-1"></i>
                    DSL校验失败，使用默认配置
                </div>
            `, true);
            break;
        
        // ============ 阶段3: Runtime引擎 ============
        case 'runtime_start':
            updateNodeIcon('runtime', 'running');
            setNodeTime('runtime', `场景: ${event.scene_type || ''}`);
            break;
            
        case 'render_start':
            updateNodeIcon('runtime', 'running');
            setNodeTime('runtime', `模板: ${event.template || ''}`);
            break;
            
        case 'prompt_built':
            updateNodeIcon('runtime', 'done');
            setNodeTime('runtime', `${elapsed}s`);
            
            let runtimePromptHtml = `
                <div class="text-sm space-y-1">
                    <div><span class="text-gray-500">系统提示词:</span> <span class="text-gray-700">${event.total_system_length || 0} 字符</span></div>
                    <div><span class="text-gray-500">用户提示词:</span> <span class="text-gray-700">${event.total_user_length || 0} 字符</span></div>
                </div>
                <div class="mt-2 space-y-2">`;
            
            if (event.full_system_prompt) {
                runtimePromptHtml += `
                <details class="border border-gray-200 rounded">
                    <summary class="px-3 py-2 text-xs cursor-pointer hover:bg-gray-50 flex items-center justify-between">
                        <span class="text-purple-500 font-medium">查看完整提示词（System Prompt）</span>
                        <span class="text-gray-400">${event.full_system_prompt.length} 字符</span>
                    </summary>
                    <div class="relative">
                        <button onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent).then(()=>{this.textContent='已复制!';setTimeout(()=>{this.textContent='复制'},1500)})" 
                                class="absolute right-2 top-2 px-2 py-1 bg-slate-600 text-white text-xs rounded hover:bg-slate-500 z-10">复制</button>
                        <pre class="p-3 bg-slate-800 text-slate-200 rounded-b text-xs overflow-auto max-h-96 whitespace-pre-wrap">${escapeHtml(event.full_system_prompt)}</pre>
                    </div>
                </details>`;
            }
            
            if (event.full_user_prompt) {
                runtimePromptHtml += `
                <details class="border border-gray-200 rounded">
                    <summary class="px-3 py-2 text-xs cursor-pointer hover:bg-gray-50 flex items-center justify-between">
                        <span class="text-blue-500 font-medium">查看完整提示词（User Prompt）</span>
                        <span class="text-gray-400">${event.full_user_prompt.length} 字符</span>
                    </summary>
                    <div class="relative">
                        <button onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent).then(()=>{this.textContent='已复制!';setTimeout(()=>{this.textContent='复制'},1500)})" 
                                class="absolute right-2 top-2 px-2 py-1 bg-slate-600 text-white text-xs rounded hover:bg-slate-500 z-10">复制</button>
                        <pre class="p-3 bg-slate-800 text-slate-200 rounded-b text-xs overflow-auto max-h-96 whitespace-pre-wrap">${escapeHtml(event.full_user_prompt)}</pre>
                    </div>
                </details>`;
            }
            
            runtimePromptHtml += '</div>';
            setNodeDetails('runtime', runtimePromptHtml);
            
            updateNodeIcon('html', 'running');
            setNodeTime('html', '生成中...');
            // 显示代码预览区
            showHtmlCodePreview();
            break;
        
        // ============ 阶段4: HTML生成 ============
        case 'provider_start':
            currentProvider = event.provider;
            setNodeTime('html', `${event.provider} (${event.model || ''}) · 生成中...`);
            break;
            
        case 'chunk':
            htmlChunks.push(event.content);
            appendCode(event.content);
            break;
            
        case 'fallback':
            const existingDetails = document.querySelector('#node-html .node-details .fallback-notice');
            if (!existingDetails) {
                const detailsEl = document.querySelector('#node-html .node-details');
                if (detailsEl) {
                    const notice = document.createElement('div');
                    notice.className = 'fallback-notice text-amber-600 text-sm mb-2';
                    notice.innerHTML = `<i class="fa-solid fa-rotate mr-1"></i>${event.from || ''} 失败，切换到 ${event.to || ''}`;
                    detailsEl.insertBefore(notice, detailsEl.firstChild);
                }
            }
            break;
            
        case 'provider_error':
            break;
            
        case 'done':
            updateNodeIcon('html', 'done');
            setNodeTime('html', `${elapsed}s · ${event.provider || currentProvider} · ${htmlChunks.join('').length} 字符`);
            break;
        
        // ============ 阶段5: 完成 ============
        case 'postprocess_start':
            updateNodeIcon('complete', 'running');
            setNodeTime('complete', '处理中...');
            break;
            
        case 'complete':
            updateNodeIcon('complete', 'done');
            setNodeTime('complete', `${elapsed}s`);
            setNodeDetails('complete', `
                <div class="text-sm space-y-1">
                    <div><span class="text-gray-500">使用模型:</span> <b class="text-gray-800">${event.provider || currentProvider}</b></div>
                    <div><span class="text-gray-500">结果ID:</span> <span class="text-gray-700">${event.result_id || ''}</span></div>
                    <div><span class="text-gray-500">HTML大小:</span> <span class="text-gray-700">${event.html_length || 0} 字符</span></div>
                </div>
            `);
            activateViewButton(event.html_url);
            break;
        
        // ============ 错误处理 ============
        case 'render_error':
            updateNodeIcon('html', 'error');
            setNodeTime('html', '错误');
            showError(event.error || 'Runtime渲染失败');
            break;
            
        case 'error':
            const errorStage = event.stage || 'unknown';
            const errorMsg = event.message || '未知错误';
            showError(`[${errorStage}] ${errorMsg}`);
            const stageMap = {
                'analysis': 'analysis',
                'dsl': 'dsl',
                'runtime': 'runtime',
                'html': 'html',
                'unknown': 'analysis'
            };
            const errorNode = stageMap[errorStage] || 'analysis';
            updateNodeIcon(errorNode, 'error');
            setNodeTime(errorNode, '错误');
            break;
            
        case 'all_failed':
            showError(event.error || '所有模型均失败');
            break;
    }
}

// ========== 自定义模式逻辑 ==========

/**
 * Step 1: 学科分析（自动执行）
 */
async function runAnalysis() {
    updateNodeIcon('analysis', 'running');
    setNodeTime('analysis', '分析中...');
    
    try {
        const response = await fetch('/api/step/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        if (!response.ok) {
            throw new Error(`API错误: ${response.status}`);
        }
        
        analysisResult = await response.json();
        
        updateNodeIcon('analysis', 'done');
        const elapsed = getElapsed();
        setNodeTime('analysis', `${elapsed}s`);
        setNodeDetails('analysis', `
            <div class="grid grid-cols-2 gap-2 text-sm">
                <div><span class="text-gray-500">学科:</span> <b class="text-gray-800">${analysisResult.subject || '-'}</b></div>
                <div><span class="text-gray-500">分支:</span> <b class="text-gray-800">${analysisResult.branch || '-'}</b></div>
                <div><span class="text-gray-500">场景:</span> <b class="text-gray-800">${analysisResult.scene_type || '-'}</b></div>
                <div><span class="text-gray-500">置信度:</span> <b class="text-gray-800">${analysisResult.confidence ? (analysisResult.confidence * 100).toFixed(0) + '%' : '-'}</b></div>
            </div>
            ${analysisResult.keywords_matched && analysisResult.keywords_matched.length > 0 ? 
                '<div class="mt-2 flex gap-1 flex-wrap">' + 
                analysisResult.keywords_matched.map(k => `<span class="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">${k}</span>`).join('') + 
                '</div>' : ''}
        `);
        
        // 显示DSL节点的模型选择器
        showModelSelector('dsl');
        
    } catch (error) {
        updateNodeIcon('analysis', 'error');
        setNodeTime('analysis', '错误');
        showError(error.message);
    }
}

/**
 * 显示模型选择器
 */
function showModelSelector(stage) {
    const bgColor = stage === 'dsl' ? 'blue' : 'green';
    const btnText = stage === 'dsl' ? '生成 DSL' : '生成 HTML';
    const confirmFunc = stage === 'dsl' ? 'confirmDSL' : 'confirmHTML';
    
    const selectorHtml = `
        <div class="model-selector mt-3 p-3 bg-${bgColor}-50 rounded-lg border border-${bgColor}-200">
            <label class="text-sm font-medium text-gray-700 mb-2 block">选择AI模型：</label>
            <select id="${stage}-model-select" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-3 focus:ring-2 focus:ring-${bgColor}-500 focus:border-${bgColor}-500">
                <option value="kimi">Kimi (moonshot-v1-128k)</option>
                <option value="deepseek">DeepSeek (deepseek-chat)</option>
                <option value="openai">OpenAI (gpt-5.4)</option>
                <option value="qwen">Qwen (qwen3.5-plus)</option>
            </select>
            <button onclick="${confirmFunc}()" class="w-full py-2 bg-${bgColor}-600 text-white rounded-lg hover:bg-${bgColor}-700 transition text-sm font-medium">
                <i class="fa-solid fa-play mr-1"></i> 开始${btnText}
            </button>
        </div>
    `;
    
    const nodeId = stage;
    const detailsEl = document.querySelector(`#node-${nodeId} .node-details`);
    if (detailsEl) {
        detailsEl.innerHTML = selectorHtml;
        detailsEl.classList.remove('hidden');
    }
}

/**
 * Step 2: DSL生成（用户确认后执行）
 */
async function confirmDSL() {
    const model = document.getElementById('dsl-model-select').value;
    
    updateNodeIcon('dsl', 'running');
    setNodeTime('dsl', `使用 ${model} 生成中...`);
    
    // 清除模型选择UI
    const detailsEl = document.querySelector('#node-dsl .node-details');
    if (detailsEl) detailsEl.innerHTML = '';
    
    try {
        const response = await fetch('/api/step/dsl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                analysis: analysisResult,
                model: model
            })
        });
        
        if (!response.ok) {
            throw new Error(`API错误: ${response.status}`);
        }
        
        // 处理SSE流
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') continue;
                    try {
                        const event = JSON.parse(data);
                        handleDSLEvent(event);
                    } catch (e) {}
                }
            }
        }
    } catch (error) {
        updateNodeIcon('dsl', 'error');
        setNodeTime('dsl', '错误');
        showError(error.message);
    }
}

/**
 * 处理DSL生成的SSE事件
 */
function handleDSLEvent(event) {
    const elapsed = getElapsed();
    
    switch (event.event) {
        case 'dsl_provider':
            setNodeTime('dsl', `模型: ${event.provider} (${event.model || ''}) · 生成中...`);
            break;
            
        case 'dsl_prompt':
            if (event.full_messages && event.full_messages.length > 0) {
                let promptHtml = '<div class="mt-2 space-y-2">';
                event.full_messages.forEach(msg => {
                    const roleLabel = msg.role === 'system' ? 'System Prompt' : 'User Prompt';
                    const roleColor = msg.role === 'system' ? 'text-purple-500' : 'text-blue-500';
                    promptHtml += `
                    <details class="border border-gray-200 rounded">
                        <summary class="px-3 py-2 text-xs cursor-pointer hover:bg-gray-50 flex items-center justify-between">
                            <span class="${roleColor} font-medium">查看完整提示词（${roleLabel}）</span>
                            <span class="text-gray-400">${msg.content.length} 字符</span>
                        </summary>
                        <div class="relative">
                            <button onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent).then(()=>{this.textContent='已复制!';setTimeout(()=>{this.textContent='复制'},1500)})" 
                                    class="absolute right-2 top-2 px-2 py-1 bg-slate-600 text-white text-xs rounded hover:bg-slate-500 z-10">复制</button>
                            <pre class="p-3 bg-slate-800 text-slate-200 rounded-b text-xs overflow-auto max-h-96 whitespace-pre-wrap">${escapeHtml(msg.content)}</pre>
                        </div>
                    </details>`;
                });
                promptHtml += '</div>';
                setNodeDetails('dsl', promptHtml);
            }
            break;
            
        case 'dsl_done':
            dslResult = event.dsl;
            updateNodeIcon('dsl', 'done');
            setNodeTime('dsl', `${elapsed}s · ${event.provider || ''}`);
            setNodeDetails('dsl', `
                <div class="text-sm space-y-1">
                    <div><span class="text-gray-500">场景类型:</span> <b class="text-gray-800">${event.dsl?.scene_type || ''}</b></div>
                    <div><span class="text-gray-500">主题:</span> <b class="text-gray-800">${event.dsl?.topic || ''}</b></div>
                </div>
                <details class="mt-2">
                    <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-600">查看完整DSL</summary>
                    <pre class="mt-1 p-2 bg-gray-50 rounded text-xs overflow-auto max-h-40">${JSON.stringify(event.dsl, null, 2)}</pre>
                </details>
            `);
            // 显示 Runtime 信息 + HTML模型选择器
            showRuntimeInfo();
            showModelSelector('html');
            break;
            
        case 'dsl_fallback':
            setNodeDetails('dsl', `
                <div class="text-amber-600 text-sm mb-2">
                    <i class="fa-solid fa-triangle-exclamation mr-1"></i>
                    DSL校验失败，使用默认配置
                </div>
            `, true);
            break;
            
        case 'error':
            updateNodeIcon('dsl', 'error');
            setNodeTime('dsl', '错误');
            showError(event.message || '生成失败');
            break;
    }
}

/**
 * 显示Runtime信息
 */
function showRuntimeInfo() {
    updateNodeIcon('runtime', 'done');
    setNodeTime('runtime', 'Prompt 组装完成');
    setNodeDetails('runtime', `
        <div class="text-sm text-gray-600">
            <i class="fa-solid fa-check text-green-500 mr-1"></i>
            Runtime引擎已根据DSL组装提示词，等待选择模型生成HTML。
        </div>
    `);
}

/**
 * 显示HTML代码预览区
 */
function showHtmlCodePreview() {
    const detailsEl = document.querySelector('#node-html .node-details');
    if (detailsEl) {
        detailsEl.innerHTML = `
            <div class="mb-2 flex justify-between text-xs text-gray-400">
                <span>代码预览</span>
                <span>已接收 <span id="char-count">0</span> 字符</span>
            </div>
            <pre id="code-preview" class="code-preview-box p-3 rounded-lg"></pre>
        `;
        detailsEl.classList.remove('hidden');
    }
}

/**
 * Step 3: HTML生成（用户确认后执行）
 */
async function confirmHTML() {
    const model = document.getElementById('html-model-select').value;
    
    updateNodeIcon('html', 'running');
    setNodeTime('html', `使用 ${model} 生成中...`);
    
    // 清除模型选择UI，添加代码预览区
    showHtmlCodePreview();
    htmlChunks = [];
    
    try {
        const response = await fetch('/api/step/html', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                dsl: dslResult,
                model: model
            })
        });
        
        if (!response.ok) {
            throw new Error(`API错误: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') continue;
                    try {
                        const event = JSON.parse(data);
                        handleHTMLEvent(event);
                    } catch (e) {}
                }
            }
        }
    } catch (error) {
        updateNodeIcon('html', 'error');
        setNodeTime('html', '错误');
        showError(error.message);
    }
}

/**
 * 处理HTML生成的SSE事件
 */
function handleHTMLEvent(event) {
    const elapsed = getElapsed();
    
    switch (event.event) {
        case 'provider_start':
            currentProvider = event.provider;
            setNodeTime('html', `模型: ${event.provider} · 生成中...`);
            break;
            
        case 'chunk':
            htmlChunks.push(event.content);
            appendCode(event.content);
            break;
            
        case 'done':
            updateNodeIcon('html', 'done');
            setNodeTime('html', `${elapsed}s · ${event.provider || currentProvider} · ${htmlChunks.join('').length} 字符`);
            break;
            
        case 'complete':
            updateNodeIcon('complete', 'done');
            setNodeTime('complete', `总耗时 ${elapsed}s`);
            setNodeDetails('complete', `
                <div class="text-sm space-y-1 mb-3">
                    <div><span class="text-gray-500">使用模型:</span> <b class="text-gray-800">${event.provider || currentProvider}</b></div>
                    <div><span class="text-gray-500">结果ID:</span> <span class="text-gray-700">${event.result_id || ''}</span></div>
                    <div><span class="text-gray-500">HTML大小:</span> <span class="text-gray-700">${event.html_length || 0} 字符</span></div>
                </div>
            `);
            activateViewButton(event.html_url);
            break;
            
        case 'error':
        case 'all_failed':
            updateNodeIcon('html', 'error');
            setNodeTime('html', '错误');
            showError(event.message || event.error || '生成失败');
            break;
    }
}

// ========== 页面初始化 ==========

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    query = params.get('query');
    
    if (!query) {
        window.location.href = 'index.html';
        return;
    }
    
    // 显示查询内容
    document.getElementById('query-display').textContent = query;
    
    // 绑定模式选择按钮事件
    const btnDefault = document.getElementById('btn-default');
    const btnCustom = document.getElementById('btn-custom');
    
    if (btnDefault) {
        btnDefault.addEventListener('click', startDefaultMode);
    }
    if (btnCustom) {
        btnCustom.addEventListener('click', startCustomMode);
    }
});

// 显式暴露函数到全局作用域（供动态生成的 onclick 调用）
window.startDefaultMode = startDefaultMode;
window.startCustomMode = startCustomMode;
window.confirmDSL = confirmDSL;
window.confirmHTML = confirmHTML;
