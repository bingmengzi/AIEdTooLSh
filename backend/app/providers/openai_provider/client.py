"""OpenAI 模型客户端"""
import httpx
import json
import logging
from typing import AsyncGenerator
from app.providers.base import AIProvider
from app.providers.openai_provider.config import OPENAI_CONFIG
from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIClient(AIProvider):
    def __init__(self):
        self.name = OPENAI_CONFIG["name"]
        self.model = OPENAI_CONFIG["model"]
        self.api_base = OPENAI_CONFIG["api_base"]
        self.priority = OPENAI_CONFIG["priority"]
        self.timeout = OPENAI_CONFIG["timeout"]
        self.api_key = settings.OPENAI_API_KEY
    
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
        
        max_tokens = max_tokens or OPENAI_CONFIG["max_tokens"]
        url = f"{self.api_base}/chat/completions"
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
        logger.info(f"[{self.name}] 发送请求 | URL={url} | model={self.model} | max_tokens={max_tokens} | temperature={temperature}")
        
        # DEBUG: 记录 messages 内容（截取前2000字符）
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            content_preview = content[:2000] + f"...(总长度:{len(content)})" if len(content) > 2000 else content
            logger.debug(f"[{self.name}] messages[{i}] role={msg.get('role')} content=\n{content_preview}")
        
        chunk_count = 0
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    logger.info(f"[{self.name}] HTTP响应状态码: {response.status_code}")
                    
                    if response.status_code != 200:
                        error_body = await response.aread()
                        error_text = error_body.decode()[:500]
                        logger.error(f"[{self.name}] API错误 | status={response.status_code} | body={error_text}")
                        raise Exception(f"{self.name} API 返回 {response.status_code}: {error_text}")
                    
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            # 记录非标准行（可能是错误信息）
                            if line.strip():
                                logger.debug(f"[{self.name}] 非标准响应行: {line[:200]}")
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
                        except json.JSONDecodeError as je:
                            logger.warning(f"[{self.name}] JSON解析失败 | data={data[:200]} | error={je}")
                            continue
        except Exception as e:
            logger.error(f"[{self.name}] 流式请求异常 | error={type(e).__name__}: {e}")
            raise
        
        logger.info(f"[{self.name}] 流式响应完成 | 总chunk数={chunk_count}")
