"""Kimi 模型客户端"""
import os
import httpx
import json
import logging
from typing import AsyncGenerator
from app.providers.base import AIProvider
from app.providers.kimi.config import KIMI_CONFIG
from app.config import settings

logger = logging.getLogger(__name__)

class KimiClient(AIProvider):
    def __init__(self):
        self.name = KIMI_CONFIG["name"]
        # Allow overriding the model via Settings (from .env)
        self.model = getattr(settings, 'KIMI_MODEL', None) or KIMI_CONFIG["model"]
        # Allow overriding the API base via Settings (from .env) or environment variable.
        # Priority: settings.KIMI_BASE_URL (pydantic-loaded .env) -> OS env KIMI_BASE_URL -> hardcoded config
        api_base_from_settings = getattr(settings, 'KIMI_BASE_URL', None)
        if api_base_from_settings:
            self.api_base = api_base_from_settings
        else:
            self.api_base = os.environ.get("KIMI_BASE_URL", KIMI_CONFIG["api_base"])
        self.priority = KIMI_CONFIG["priority"]
        self.timeout = KIMI_CONFIG["timeout"]
        self.api_key = settings.KIMI_API_KEY
    
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = None
    ) -> AsyncGenerator[str, None]:
        # API Key 检查
        if not self.api_key or self.api_key.startswith("sk-your"):
            logger.warning(f"[{self.name}] API Key 未配置")
            raise ValueError(f"{self.name} API Key 未配置")
        
        logger.info(f"[{self.name}] API Key 检查通过")
        
        max_tokens = max_tokens or KIMI_CONFIG["max_tokens"]
        # Build the full URL for the completions endpoint. If the configured api_base
        # already contains the path (e.g. endswith or contains '/chat/completions'),
        # use it as-is to avoid duplicating the path.
        if "/chat/completions" in self.api_base:
            url = self.api_base.rstrip('/')
        else:
            url = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        # 日志：HTTP请求信息
        # Prepare a masked preview of the Authorization header for safe logging
        if self.api_key:
            masked_key = f"{self.api_key[:8]}..." if len(self.api_key) > 8 else self.api_key
            auth_preview = f"Bearer {masked_key} (len={len(self.api_key)})"
        else:
            auth_preview = "<no-key>"

        logger.info(f"[{self.name}] 发送请求 | URL={url} | model={self.model} | max_tokens={max_tokens} | temperature={temperature} | Authorization_preview={auth_preview}")
        
        # DEBUG: 记录 messages 内容（截取前2000字符）
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            content_preview = content[:2000] + f"...(总长度:{len(content)})" if len(content) > 2000 else content
            logger.debug(f"[{self.name}] messages[{i}] role={msg.get('role')} content=\n{content_preview}")
        
        chunk_count = 0
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                logger.info(f"[{self.name}] HTTP响应状态码: {response.status_code}")
                
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"[{self.name}] API错误 | status={response.status_code} | body={error_body.decode()[:500]}")
                    raise Exception(f"{self.name} API 返回 {response.status_code}: {error_body.decode()}")
                
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]  # 去掉 "data: " 前缀
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            chunk_count += 1
                            yield content
                    except json.JSONDecodeError:
                        continue
        
        logger.info(f"[{self.name}] 流式响应完成 | 总chunk数={chunk_count}")
