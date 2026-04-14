"""MessageBus 完整測試 — 涵蓋 namespace 路由、並發、訂閱機制。"""

from __future__ import annotations

import asyncio

import pytest

from src.agents.base import (
    AgentMessage,
    BaseAgent,
    MessageType,
    TaskContext,
    TaskResult,
    TaskStatus,
)
from src.agents.message_bus import MessageBus

# ── 測試用代理 ──


class MockAgent(BaseAgent):
    """測試用代理，可追蹤收到的訊息。"""

    def __init__(self, agent_id: str, namespace_name: str | None = None) -> None:
        super().__init__(agent_id)
        self._namespace_name = namespace_name or agent_id
        self.received_messages: list[AgentMessage] = []

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    @property
    def namespace_name(self) -> str:
        return self._namespace_name

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        return TaskResult(status=TaskStatus.SUCCESS, data={"task": task})

    async def handle_message(self, message: AgentMessage) -> AgentMessage | None:
        self.received_messages.append(message)
        if message.type == MessageType.QUERY:
            return AgentMessage(
                from_agent=self._id,
                to_agent=message.from_agent,
                type=MessageType.RESPONSE,
                payload={"capabilities": self.capabilities},
                correlation_id=message.message_id,
            )
        return None


# ── Fixtures ──


@pytest.fixture()
def bus() -> MessageBus:
    return MessageBus()


# ── 基本註冊與移除 ──


class TestRegistration:
    def test_register(self, bus: MessageBus) -> None:
        agent = MockAgent("a1", "wAI:agent-1")
        bus.register(agent)
        assert bus.get_agent("a1") is agent
        assert len(bus.registered_agents) == 1

    def test_unregister(self, bus: MessageBus) -> None:
        agent = MockAgent("a1", "wAI:agent-1")
        bus.register(agent)
        bus.unregister("a1")
        assert bus.get_agent("a1") is None
        assert len(bus.registered_agents) == 0

    def test_unregister_nonexistent(self, bus: MessageBus) -> None:
        """移除不存在的代理不應錯誤。"""
        bus.unregister("nonexistent")

    def test_register_multiple(self, bus: MessageBus) -> None:
        a1 = MockAgent("a1", "wAI:agent-1")
        a2 = MockAgent("a2", "wData:agent-2")
        bus.register(a1)
        bus.register(a2)
        assert len(bus.registered_agents) == 2


# ── Namespace 路由 ──


class TestNamespaceRouting:
    def test_namespace_registration(self, bus: MessageBus) -> None:
        a1 = MockAgent("a1", "wAI:agent-1")
        a2 = MockAgent("a2", "wAI:agent-2")
        a3 = MockAgent("a3", "wData:agent-3")
        bus.register(a1)
        bus.register(a2)
        bus.register(a3)
        assert len(bus._namespace_map["wAI"]) == 2
        assert len(bus._namespace_map["wData"]) == 1

    @pytest.mark.asyncio
    async def test_namespace_broadcast(self, bus: MessageBus) -> None:
        """Namespace 廣播只送達同 namespace 的代理。"""
        ai1 = MockAgent("ai1", "wAI:model-trainer")
        ai2 = MockAgent("ai2", "wAI:experiment-tracker")
        data1 = MockAgent("data1", "wData:scada-processor")
        bus.register(ai1)
        bus.register(ai2)
        bus.register(data1)

        msg = AgentMessage(
            from_agent="director",
            to_agent="wAI:*",
            type=MessageType.NOTIFICATION,
            payload={"info": "ai team only"},
        )
        result = await bus.publish(msg)
        assert result is None  # 群組廣播無回傳
        assert len(ai1.received_messages) == 1
        assert len(ai2.received_messages) == 1
        assert len(data1.received_messages) == 0

    @pytest.mark.asyncio
    async def test_namespace_broadcast_excludes_sender(self, bus: MessageBus) -> None:
        """Namespace 廣播排除發送者。"""
        ai1 = MockAgent("ai1", "wAI:model-1")
        ai2 = MockAgent("ai2", "wAI:model-2")
        bus.register(ai1)
        bus.register(ai2)

        msg = AgentMessage(
            from_agent="ai1",  # 發送者也在 wAI namespace
            to_agent="wAI:*",
            type=MessageType.NOTIFICATION,
            payload={},
        )
        await bus.publish(msg)
        assert len(ai1.received_messages) == 0
        assert len(ai2.received_messages) == 1

    def test_unregister_removes_from_namespace(self, bus: MessageBus) -> None:
        a1 = MockAgent("a1", "wAI:agent-1")
        bus.register(a1)
        assert "a1" in bus._namespace_map["wAI"]
        bus.unregister("a1")
        assert "a1" not in bus._namespace_map["wAI"]

    def test_no_colon_in_name_no_namespace(self, bus: MessageBus) -> None:
        """不含冒號的名稱不加入任何 namespace。"""
        agent = MockAgent("plain-agent", "plain-agent")
        bus.register(agent)
        # 不應建立任何 namespace entry
        for ns_agents in bus._namespace_map.values():
            assert "plain-agent" not in ns_agents


# ── 全域廣播 ──


class TestGlobalBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_all(self, bus: MessageBus) -> None:
        a1 = MockAgent("a1")
        a2 = MockAgent("a2")
        a3 = MockAgent("a3")
        bus.register(a1)
        bus.register(a2)
        bus.register(a3)

        msg = AgentMessage(
            from_agent="a1",
            to_agent="*",
            type=MessageType.NOTIFICATION,
            payload={},
        )
        await bus.publish(msg)
        # a1 是發送者，不收到
        assert len(a1.received_messages) == 0
        assert len(a2.received_messages) == 1
        assert len(a3.received_messages) == 1

    @pytest.mark.asyncio
    async def test_broadcast_all_with_external_sender(self, bus: MessageBus) -> None:
        """外部發送者（不在 bus 上）的全域廣播送達所有代理。"""
        a1 = MockAgent("a1")
        a2 = MockAgent("a2")
        bus.register(a1)
        bus.register(a2)

        msg = AgentMessage(
            from_agent="external",
            to_agent="*",
            type=MessageType.NOTIFICATION,
            payload={},
        )
        await bus.publish(msg)
        assert len(a1.received_messages) == 1
        assert len(a2.received_messages) == 1


# ── 點對點 ──


class TestPointToPoint:
    @pytest.mark.asyncio
    async def test_direct_message(self, bus: MessageBus) -> None:
        receiver = MockAgent("receiver")
        bus.register(receiver)

        msg = AgentMessage(
            from_agent="sender",
            to_agent="receiver",
            type=MessageType.QUERY,
            payload={},
        )
        reply = await bus.publish(msg)
        assert reply is not None
        assert reply.type == MessageType.RESPONSE
        assert len(receiver.received_messages) == 1

    @pytest.mark.asyncio
    async def test_message_to_nonexistent(self, bus: MessageBus) -> None:
        msg = AgentMessage(
            from_agent="sender",
            to_agent="ghost",
            type=MessageType.QUERY,
            payload={},
        )
        result = await bus.publish(msg)
        assert result is None


# ── 訊息歷史 ──


class TestHistory:
    @pytest.mark.asyncio
    async def test_history_records(self, bus: MessageBus) -> None:
        msg = AgentMessage(
            from_agent="a", to_agent="b", type=MessageType.NOTIFICATION, payload={}
        )
        await bus.publish(msg)
        assert len(bus.history) == 1
        assert bus.history[0].from_agent == "a"

    @pytest.mark.asyncio
    async def test_history_limit(self, bus: MessageBus) -> None:
        bus._max_history = 3
        for i in range(10):
            msg = AgentMessage(
                from_agent="a",
                to_agent="b",
                type=MessageType.NOTIFICATION,
                payload={"i": i},
            )
            await bus.publish(msg)
        assert len(bus.history) == 3
        # 保留最新的 3 條
        assert bus.history[0].payload["i"] == 7

    def test_clear_history(self, bus: MessageBus) -> None:
        bus._history.append(
            AgentMessage(from_agent="a", to_agent="b", type=MessageType.NOTIFICATION)
        )
        bus.clear_history()
        assert len(bus.history) == 0


# ── 訂閱機制 ──


class TestSubscription:
    @pytest.mark.asyncio
    async def test_subscribe_to_agent_topic(self, bus: MessageBus) -> None:
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("target-agent", handler)
        msg = AgentMessage(
            from_agent="sender",
            to_agent="target-agent",
            type=MessageType.NOTIFICATION,
            payload={},
        )
        await bus.publish(msg)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_subscribe_to_message_type(self, bus: MessageBus) -> None:
        """可用 message type 值訂閱。"""
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("notification", handler)
        msg = AgentMessage(
            from_agent="a",
            to_agent="b",
            type=MessageType.NOTIFICATION,
            payload={},
        )
        await bus.publish(msg)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_subscribe_wildcard(self, bus: MessageBus) -> None:
        """訂閱 * 收到所有訊息。"""
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("*", handler)
        msg1 = AgentMessage(
            from_agent="a", to_agent="b", type=MessageType.NOTIFICATION, payload={}
        )
        msg2 = AgentMessage(
            from_agent="c", to_agent="d", type=MessageType.QUERY, payload={}
        )
        await bus.publish(msg1)
        await bus.publish(msg2)
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_subscriber_exception_doesnt_break_publish(self, bus: MessageBus) -> None:
        """訂閱者拋出異常不應影響訊息發布。"""
        async def bad_handler(msg: AgentMessage) -> None:
            raise RuntimeError("subscriber crash")

        good_received: list[AgentMessage] = []

        async def good_handler(msg: AgentMessage) -> None:
            good_received.append(msg)

        bus.subscribe("*", bad_handler)
        bus.subscribe("*", good_handler)

        msg = AgentMessage(
            from_agent="a", to_agent="b", type=MessageType.NOTIFICATION, payload={}
        )
        await bus.publish(msg)
        assert len(good_received) == 1


# ── 超時機制 ──


class TestRequest:
    @pytest.mark.asyncio
    async def test_request_with_reply(self, bus: MessageBus) -> None:
        receiver = MockAgent("receiver")
        bus.register(receiver)

        msg = AgentMessage(
            from_agent="sender",
            to_agent="receiver",
            type=MessageType.QUERY,
            payload={},
        )
        reply = await bus.request(msg, timeout=5.0)
        assert reply is not None
        assert reply.type == MessageType.RESPONSE

    @pytest.mark.asyncio
    async def test_request_to_nonexistent_returns_none(self, bus: MessageBus) -> None:
        msg = AgentMessage(
            from_agent="sender",
            to_agent="ghost",
            type=MessageType.QUERY,
            payload={},
        )
        result = await bus.request(msg, timeout=1.0)
        assert result is None


# ── 並發安全 ──


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_publishes(self, bus: MessageBus) -> None:
        """多個並發訊息發布不應遺漏。"""
        a1 = MockAgent("receiver-1")
        bus.register(a1)

        messages = [
            AgentMessage(
                from_agent=f"sender-{i}",
                to_agent="receiver-1",
                type=MessageType.NOTIFICATION,
                payload={"i": i},
            )
            for i in range(20)
        ]
        await asyncio.gather(*[bus.publish(m) for m in messages])
        assert len(a1.received_messages) == 20
        assert len(bus.history) == 20

    @pytest.mark.asyncio
    async def test_concurrent_namespace_broadcast(self, bus: MessageBus) -> None:
        """並發 namespace 廣播不應遺漏。"""
        agents = [MockAgent(f"ai-{i}", f"wAI:agent-{i}") for i in range(5)]
        for a in agents:
            bus.register(a)

        messages = [
            AgentMessage(
                from_agent="external",
                to_agent="wAI:*",
                type=MessageType.NOTIFICATION,
                payload={"batch": j},
            )
            for j in range(3)
        ]
        await asyncio.gather(*[bus.publish(m) for m in messages])
        # 每個 agent 應收到 3 條
        for a in agents:
            assert len(a.received_messages) == 3


# ── AgentMessage 序列化 ──


class TestAgentMessageSerialization:
    def test_to_dict(self) -> None:
        msg = AgentMessage(
            from_agent="sender",
            to_agent="receiver",
            type=MessageType.TASK_REQUEST,
            payload={"data": 42},
            correlation_id="corr-123",
        )
        d = msg.to_dict()
        assert d["from"] == "sender"
        assert d["to"] == "receiver"
        assert d["type"] == "task_request"
        assert d["payload"]["data"] == 42
        assert d["correlation_id"] == "corr-123"
        assert "message_id" in d
        assert "timestamp" in d

    def test_default_fields(self) -> None:
        msg = AgentMessage(
            from_agent="a", to_agent="b", type=MessageType.NOTIFICATION
        )
        assert msg.message_id  # auto UUID
        assert msg.timestamp  # auto ISO
        assert msg.correlation_id is None
        assert msg.payload == {}
