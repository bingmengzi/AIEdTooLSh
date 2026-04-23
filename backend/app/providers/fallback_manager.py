"""多模型降级策略管理器"""
import time
import logging
from typing import AsyncGenerator
from app.providers.kimi import KimiClient
from app.providers.qwen import QwenClient
from app.providers.deepseek import DeepSeekClient
from app.providers.openai_provider import OpenAIClient

logger = logging.getLogger(__name__)

class FallbackManager:
    """按优先级逐个尝试AI模型，失败自动切换到下一个"""
    
    def __init__(self):
        # 按优先级排序: Kimi → Qwen → DeepSeek → OpenAI
        self.providers = [
            KimiClient(),
            QwenClient(),
            DeepSeekClient(),
            OpenAIClient(),
        ]
    
    async def chat_stream_with_fallback(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> AsyncGenerator[dict, None]:
        """带降级的流式调用
        
        Yields:
            dict: 包含以下类型事件:
            - {"event": "provider_start", "provider": "kimi"} - 开始尝试某个提供商
            - {"event": "chunk", "provider": "kimi", "content": "..."} - 文本块
            - {"event": "provider_error", "provider": "kimi", "error": "..."} - 某提供商失败
            - {"event": "fallback", "from": "kimi", "to": "qwen"} - 降级事件
            - {"event": "done", "provider": "kimi"} - 完成
        """
        last_error = None
        errors_summary = []  # 收集所有错误
        
        logger.info(f"[FallbackManager] 开始降级调用 | 可用providers: {[p.name for p in self.providers]}")
        
        for i, provider in enumerate(self.providers):
            start_time = time.time()
            try:
                logger.info(f"[FallbackManager] 尝试provider {i+1}/{len(self.providers)} | name={provider.name} | model={provider.model}")
                yield {"event": "provider_start", "provider": provider.name, "model": provider.model}
                
                has_content = False
                async for content in provider.chat_stream(messages, temperature, max_tokens):
                    has_content = True
                    yield {"event": "chunk", "provider": provider.name, "content": content}
                
                if has_content:
                    elapsed = time.time() - start_time
                    yield {"event": "done", "provider": provider.name}
                    logger.info(f"[FallbackManager] {provider.name} 调用成功 | 耗时={elapsed:.2f}s")
                    return
                else:
                    raise Exception(f"{provider.name} 返回空内容")
                    
            except Exception as e:
                elapsed = time.time() - start_time
                last_error = str(e)
                errors_summary.append(f"{provider.name}: {last_error}")
                logger.warning(f"[FallbackManager] {provider.name} 调用失败 | 耗时={elapsed:.2f}s | error={last_error}")
                yield {"event": "provider_error", "provider": provider.name, "error": str(e)}
                
                # 如果还有下一个提供商，发出降级事件
                if i < len(self.providers) - 1:
                    next_provider = self.providers[i + 1]
                    logger.info(f"[FallbackManager] 降级切换 | from={provider.name} → to={next_provider.name}")
                    yield {
                        "event": "fallback",
                        "from": provider.name,
                        "to": next_provider.name
                    }
        
        # 所有提供商都失败
        logger.error(f"[FallbackManager] 所有provider均失败 | errors={errors_summary}")
        yield {"event": "all_failed", "error": f"所有AI模型均不可用，最后错误: {last_error}"}
    
    async def chat_stream_single(
        self,
        provider_name: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> AsyncGenerator[dict, None]:
        """直接使用指定模型（不降级）"""
        logger.info(f"[FallbackManager] 指定模型调用 | provider_name={provider_name}")
        
        provider = None
        for p in self.providers:
            if p.name == provider_name:
                provider = p
                break
        
        if not provider:
            logger.error(f"[FallbackManager] 未找到指定模型 | provider_name={provider_name}")
            yield {"event": "all_failed", "error": f"未找到模型: {provider_name}"}
            return
        
        start_time = time.time()
        try:
            logger.info(f"[FallbackManager] 使用指定模型 | name={provider.name} | model={provider.model}")
            yield {"event": "provider_start", "provider": provider.name, "model": provider.model}
            
            has_content = False
            async for content in provider.chat_stream(messages, temperature, max_tokens):
                has_content = True
                yield {"event": "chunk", "provider": provider.name, "content": content}
            
            if has_content:
                elapsed = time.time() - start_time
                yield {"event": "done", "provider": provider.name}
                logger.info(f"[FallbackManager] {provider.name} 指定调用成功 | 耗时={elapsed:.2f}s")
            else:
                raise Exception(f"{provider.name} 返回空内容")
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(f"[FallbackManager] {provider.name} 指定调用失败 | 耗时={elapsed:.2f}s | error={e}")
            yield {"event": "provider_error", "provider": provider.name, "error": str(e)}
            yield {"event": "all_failed", "error": str(e)}

    async def get_available_providers(self) -> list[dict]:
        """返回所有已配置的提供商状态"""
        result = []
        for p in self.providers:
            result.append({
                "name": p.name,
                "model": p.model,
                "priority": p.priority,
                "has_key": bool(p.api_key and not p.api_key.startswith("sk-your")),
            })
        return result
