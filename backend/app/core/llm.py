"""
CaseWise 法律AI工具 - LLM 抽象层模块

使用 OpenAI 兼容的 API 格式调用火山方舟大模型，
支持流式和非流式响应，提供统一的对话补全接口。
"""

import logging
from typing import AsyncGenerator, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM 抽象层服务

    封装火山方舟 API 的调用逻辑，使用 OpenAI 兼容格式，
    提供同步和流式对话补全能力。
    """

    def __init__(self) -> None:
        """
        初始化 LLM 服务

        使用 .env 中的 ARK_API_URL 和 ARK_API_KEY 创建异步 OpenAI 客户端。
        """
        self.client = AsyncOpenAI(
            base_url=settings.ARK_API_URL,
            api_key=settings.ARK_API_KEY,
        )
        self.model = settings.ARK_CHAT_MODEL
        logger.info("LLM 服务初始化完成，模型: %s", self.model)

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> Optional[str]:
        """
        非流式对话补全

        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 生成温度，越高越随机，范围 0-2
            max_tokens: 最大生成 token 数
            stream: 是否使用流式响应（此方法中应为 False）

        Returns:
            str: 模型生成的回复文本，失败时返回 None
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            content = response.choices[0].message.content
            logger.debug("LLM 非流式响应完成，token 用量: %s", response.usage)
            return content
        except Exception as e:
            logger.error("LLM 非流式调用失败: %s", str(e))
            return None

    async def chat_completion_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话补全

        逐 token 生成回复，适用于需要实时展示生成过程的场景。

        Args:
            messages: 对话消息列表
            temperature: 生成温度
            max_tokens: 最大生成 token 数

        Yields:
            str: 逐个生成的文本片段
        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error("LLM 流式调用失败: %s", str(e))
            yield f"[错误] LLM 调用失败: {str(e)}"

    async def chat_with_system(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """
        带系统提示的对话补全

        封装了 system + user 消息的常见对话模式。

        Args:
            system_prompt: 系统提示词，定义AI的角色和行为约束
            user_message: 用户消息
            temperature: 生成温度
            max_tokens: 最大生成 token 数

        Returns:
            str: 模型生成的回复文本，失败时返回 None
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# 全局 LLM 服务单例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    获取 LLM 服务单例

    Returns:
        LLMService: LLM 服务实例
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
