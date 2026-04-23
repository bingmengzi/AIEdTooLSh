"""AI模型提供商抽象基类"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """所有AI模型提供商的统一基类"""
    
    name: str = ""           # 提供商名称，如 "kimi"
    model: str = ""          # 模型名称，如 "moonshot-v1-8k"
    priority: int = 0        # 优先级，数字越小优先级越高
    api_base: str = ""       # API基础URL
    
    @abstractmethod
    async def chat_stream(
        self, 
        messages: list[dict], 
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> AsyncGenerator[str, None]:
        """流式调用AI模型，逐块返回文本内容
        
        Args:
            messages: OpenAI格式的消息列表 [{"role": "system", "content": "..."}, ...]
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            str: 每次返回一小段文本内容
        """
        ...
    
    async def health_check(self) -> bool:
        """检查该提供商是否可用"""
        try:
            async for _ in self.chat_stream(
                [{"role": "user", "content": "hi"}],
                max_tokens=5
            ):
                return True
        except Exception as e:
            logger.warning(f"{self.name} 健康检查失败: {e}")
            return False
