/**
 * AiEdToolsH API 请求封装
 */
const API_BASE = window.location.origin;

const api = {
    /**
     * 健康检查
     */
    async health() {
        const res = await fetch(`${API_BASE}/api/health`);
        return res.json();
    },
    
    /**
     * 流式生成请求 (SSE)
     * @param {string} query - 用户输入
     * @param {function} onEvent - 事件回调 (eventType, data) => void
     * @returns {Promise} 
     */
    async generate(query, onEvent) {
        const res = await fetch(`${API_BASE}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });
        
        if (!res.ok) {
            throw new Error(`API错误: ${res.status}`);
        }
        
        const reader = res.body.getReader();
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
                    const data = line.slice(6);
                    if (data === '[DONE]') return;
                    try {
                        const parsed = JSON.parse(data);
                        if (onEvent) onEvent(parsed.event, parsed);
                    } catch (e) {
                        // 忽略解析错误
                    }
                }
            }
        }
    }
};
