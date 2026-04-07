"""WindAI Lab 代理訊息匯流排。

實作 publish/subscribe 模式的訊息路由系統，
支援點對點訊息、廣播、以及 namespace 群組訊息。
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.agents.base import AgentMessage, BaseAgent

logger = get_logger("message_bus")

# 訊息處理器類型：接收 AgentMessage，回傳 AgentMessage 或 None
MessageHandler = Callable[["AgentMessage"], Coroutine[None, None, "AgentMessage | None"]]


class MessageBus:
    """代理間訊息匯流排。

    路由規則：
    - 點對點：``to_agent`` 精確匹配已註冊的代理 ID
    - Namespace 群組：``to_agent`` 為 ``wData:*`` 格式，廣播至該 namespace 所有代理
    - 全域廣播：``to_agent`` 為 ``*``，廣播至所有已註冊代理
    """

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._namespace_map: dict[str, list[str]] = defaultdict(list)
        self._subscribers: dict[str, list[MessageHandler]] = defaultdict(list)
        self._history: list[AgentMessage] = []
        self._max_history: int = 500

    def register(self, agent: BaseAgent) -> None:
        """註冊代理至匯流排。

        Args:
            agent: 要註冊的代理實例。
        """
        self._agents[agent.id] = agent

        # 解析 namespace（從 agent.namespace_name 如 "wAI:fault-diagnostician"）
        ns_name = agent.namespace_name
        if ":" in ns_name:
            ns = ns_name.split(":")[0]
            if agent.id not in self._namespace_map[ns]:
                self._namespace_map[ns].append(agent.id)

        logger.debug(f"已註冊代理：{agent.id} ({ns_name})")

    def unregister(self, agent_id: str) -> None:
        """從匯流排移除代理。"""
        agent = self._agents.pop(agent_id, None)
        if agent:
            ns_name = agent.namespace_name
            if ":" in ns_name:
                ns = ns_name.split(":")[0]
                self._namespace_map[ns] = [
                    aid for aid in self._namespace_map[ns] if aid != agent_id
                ]
            logger.debug(f"已移除代理：{agent_id}")

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """取得已註冊的代理實例。"""
        return self._agents.get(agent_id)

    @property
    def registered_agents(self) -> dict[str, BaseAgent]:
        """所有已註冊的代理。"""
        return dict(self._agents)

    @property
    def history(self) -> list[AgentMessage]:
        """訊息歷史記錄。"""
        return list(self._history)

    def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """訂閱特定主題的訊息。

        Args:
            topic: 主題名稱（可為代理 ID、namespace、或自定義主題）。
            handler: 訊息處理回呼函式。
        """
        self._subscribers[topic].append(handler)

    async def publish(self, message: AgentMessage) -> AgentMessage | None:
        """發布訊息至匯流排，路由至目標代理。

        同時透過 WebSocket 廣播訊息至前端，供虛擬辦公室顯示訊息流。

        Args:
            message: 要發布的訊息。

        Returns:
            目標代理的回覆（僅點對點訊息有回覆），群組/廣播回傳 None。
        """
        # 記錄歷史
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        # 廣播至前端 WebSocket（非阻塞）
        try:
            from src.api.websocket_manager import manager as ws_manager

            await ws_manager.broadcast_agent_message(message.to_dict())
        except Exception:
            logger.warning("WebSocket 廣播代理訊息失敗（可能無連線）")

        target = message.to_agent

        # 通知訂閱者
        await self._notify_subscribers(message)

        # 全域廣播
        if target == "*":
            await self._broadcast_all(message)
            return None

        # Namespace 群組廣播（如 "wData:*"）
        if target.endswith(":*"):
            ns = target.split(":")[0]
            await self._broadcast_namespace(ns, message)
            return None

        # 點對點
        agent = self._agents.get(target)
        if agent is None:
            logger.warning(f"訊息目標代理不存在：{target}（來自 {message.from_agent}）")
            return None

        return await agent.handle_message(message)

    async def request(self, message: AgentMessage, timeout: float = 30.0) -> AgentMessage | None:
        """發送請求並等待回覆（含超時）。

        Args:
            message: 要發送的訊息。
            timeout: 超時秒數。

        Returns:
            回覆訊息，超時則回傳 None。
        """
        try:
            return await asyncio.wait_for(self.publish(message), timeout=timeout)
        except TimeoutError:
            logger.warning(
                f"訊息超時：{message.from_agent} → {message.to_agent} "
                f"(type={message.type}, timeout={timeout}s)"
            )
            return None

    async def _broadcast_all(self, message: AgentMessage) -> None:
        """廣播訊息至所有代理（排除發送者）。"""
        tasks = [
            agent.handle_message(message)
            for aid, agent in self._agents.items()
            if aid != message.from_agent
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _broadcast_namespace(self, namespace: str, message: AgentMessage) -> None:
        """廣播訊息至指定 namespace 的所有代理。"""
        agent_ids = self._namespace_map.get(namespace, [])
        tasks = [
            self._agents[aid].handle_message(message)
            for aid in agent_ids
            if aid in self._agents and aid != message.from_agent
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _notify_subscribers(self, message: AgentMessage) -> None:
        """通知所有相關主題的訂閱者。"""
        targets = [message.to_agent, message.type.value, "*"]
        for topic in targets:
            handlers = self._subscribers.get(topic, [])
            for handler in handlers:
                try:
                    await handler(message)
                except Exception:
                    logger.exception(f"訂閱者處理訊息失敗：topic={topic}")

    def clear_history(self) -> None:
        """清除訊息歷史記錄。"""
        self._history.clear()


# 全域單例
bus = MessageBus()
