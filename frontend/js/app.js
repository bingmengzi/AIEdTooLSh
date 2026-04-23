/**
 * AiEdToolsH 首页交互逻辑
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('search-form');
    const input = document.getElementById('search-input');
    const exampleBtns = document.querySelectorAll('.example-btn');
    
    // 表单提交
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (query) {
            window.location.href = `generate.html?query=${encodeURIComponent(query)}`;
        }
    });
    
    // 示例标签点击 - 填入文字但不自动提交
    exampleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            input.value = btn.dataset.query || btn.textContent.trim();
            input.focus();
        });
    });
    
    // 输入框自动聚焦
    input.focus();
});
