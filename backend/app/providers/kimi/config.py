"""Kimi (Moonshot) 模型配置"""
KIMI_CONFIG = {
    "name": "kimi",
    "model": "moonshot-v1-128k",
    "api_base": "https://api.moonshot.cn/v1",
    "priority": 1,
    "timeout": 180,  # 大模型需要更长超时
    "max_tokens": 16384,
}
