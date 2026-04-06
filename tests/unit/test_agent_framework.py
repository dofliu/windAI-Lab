"""代理框架核心元件的單元測試。

測試 BaseAgent、MessageBus、AgentInstanceRegistry 的行為，
確保代理生命週期管理、訊息路由、以及實例註冊的正確性。
"""

from __future__ import annotations

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
from src.agents.registry import AgentInstanceRegistry
from src.api.agent_registry import reset_all_agents

# ── 測試用具體代理 ─────────────────────────────────────────────


class StubAgent(BaseAgent):
    """測試用的存根代理。"""

    def __init__(self, agent_id: str = "stub-agent") -> None:
        super().__init__(agent_id)
        self.execute_calls: list[tuple[str, TaskContext]] = []

    @property
    def capabilities(self) -> list[str]:
        return ["testing", "stubbing"]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        self.execute_calls.append((task, context))
        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"task": task},
            summary=f"Stub completed: {task}",
        )


class FailingAgent(BaseAgent):
    """測試用的失敗代理。"""

    def __init__(self) -> None:
        super().__init__("failing-agent")

    @property
    def capabilities(self) -> list[str]:
        return ["failing"]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        return TaskResult(
            status=TaskStatus.ERROR,
            errors=["deliberate failure"],
            summary="Failed on purpose",
        )


class ExceptionAgent(BaseAgent):
    """測試用的例外代理。"""

    def __init__(self) -> None:
        super().__init__("exception-agent")

    @property
    def capabilities(self) -> list[str]:
        return ["exceptions"]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        raise RuntimeError("unexpected crash")


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """確保每個測試間代理狀態隔離。"""
    reset_all_agents()
    yield  # type: ignore[misc]
    reset_all_agents()


@pytest.fixture()
def stub_agent() -> StubAgent:
    return StubAgent()


@pytest.fixture()
def message_bus() -> MessageBus:
    return MessageBus()


@pytest.fixture()
def registry() -> AgentInstanceRegistry:
    return AgentInstanceRegistry()


# ── BaseAgent Tests ──────────────────────────────────────────


class TestBaseAgent:
    """BaseAgent 基本功能測試。"""

    def test_agent_id(self, stub_agent: StubAgent) -> None:
        """代理 ID 正確設定。"""
        assert stub_agent.id == "stub-agent"

    def test_capabilities(self, stub_agent: StubAgent) -> None:
        """capabilities 屬性回傳正確列表。"""
        assert stub_agent.capabilities == ["testing", "stubbing"]

    def test_description_default(self, stub_agent: StubAgent) -> None:
        """未覆寫時 description 回傳預設格式。"""
        desc = stub_agent.description
        assert "stub-agent" in desc

    @pytest.mark.asyncio()
    async def test_execute_success(self, stub_agent: StubAgent) -> None:
        """execute() 回傳成功結果。"""
        ctx = TaskContext(parameters={"key": "value"})
        result = await stub_agent.execute("test task", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert result.data == {"task": "test task"}
        assert len(stub_agent.execute_calls) == 1

    @pytest.mark.asyncio()
    async def test_execute_error(self) -> None:
        """失敗代理回傳 ERROR 結果。"""
        agent = FailingAgent()
        ctx = TaskContext()
        result = await agent.execute("fail task", ctx)
        assert result.status == TaskStatus.ERROR
        assert "deliberate failure" in result.errors

    @pytest.mark.asyncio()
    async def test_run_task_catches_exceptions(self) -> None:
        """run_task() 捕獲 execute() 中的未預期例外。"""
        agent = ExceptionAgent()
        ctx = TaskContext()
        result = await agent.run_task("crash task", ctx)
        assert result.status == TaskStatus.ERROR
        assert any("unexpected crash" in e for e in result.errors)

    @pytest.mark.asyncio()
    async def test_handle_query_message(self, stub_agent: StubAgent) -> None:
        """handle_message 處理 QUERY 類型訊息。"""
        msg = AgentMessage(
            from_agent="other",
            to_agent="stub-agent",
            type=MessageType.QUERY,
            payload={},
        )
        reply = await stub_agent.handle_message(msg)
        assert reply is not None
        assert reply.type == MessageType.RESPONSE
        assert "capabilities" in reply.payload


# ── MessageBus Tests ─────────────────────────────────────────


class TestMessageBus:
    """MessageBus 訊息路由測試。"""

    def test_register_agent(self, message_bus: MessageBus) -> None:
        """代理成功註冊至 bus。"""
        agent = StubAgent("test-bus-agent")
        message_bus.register(agent)
        assert message_bus.get_agent("test-bus-agent") is agent

    def test_unregister_agent(self, message_bus: MessageBus) -> None:
        """代理成功從 bus 移除。"""
        agent = StubAgent("remove-me")
        message_bus.register(agent)
        message_bus.unregister("remove-me")
        assert message_bus.get_agent("remove-me") is None

    @pytest.mark.asyncio()
    async def test_point_to_point_message(self, message_bus: MessageBus) -> None:
        """點對點訊息路由至目標代理。"""
        receiver = StubAgent("receiver")
        message_bus.register(receiver)

        msg = AgentMessage(
            from_agent="sender",
            to_agent="receiver",
            type=MessageType.QUERY,
            payload={"data": "test"},
        )
        reply = await message_bus.publish(msg)
        assert reply is not None
        assert reply.type == MessageType.RESPONSE

    @pytest.mark.asyncio()
    async def test_message_to_unknown_agent(self, message_bus: MessageBus) -> None:
        """訊息目標不存在時回傳 None。"""
        msg = AgentMessage(
            from_agent="sender",
            to_agent="nonexistent",
            type=MessageType.QUERY,
            payload={},
        )
        result = await message_bus.publish(msg)
        assert result is None

    @pytest.mark.asyncio()
    async def test_broadcast_all(self, message_bus: MessageBus) -> None:
        """全域廣播送達所有已註冊代理（排除發送者）。"""
        a1 = StubAgent("agent-1")
        a2 = StubAgent("agent-2")
        message_bus.register(a1)
        message_bus.register(a2)

        msg = AgentMessage(
            from_agent="agent-1",
            to_agent="*",
            type=MessageType.NOTIFICATION,
            payload={"info": "hello"},
        )
        result = await message_bus.publish(msg)
        assert result is None  # 廣播無回傳

    @pytest.mark.asyncio()
    async def test_message_history(self, message_bus: MessageBus) -> None:
        """訊息歷史正確記錄。"""
        msg = AgentMessage(from_agent="a", to_agent="b", type=MessageType.NOTIFICATION, payload={})
        await message_bus.publish(msg)
        assert len(message_bus.history) == 1
        assert message_bus.history[0].from_agent == "a"

    @pytest.mark.asyncio()
    async def test_history_limit(self, message_bus: MessageBus) -> None:
        """歷史記錄不超過上限。"""
        message_bus._max_history = 5
        for i in range(10):
            msg = AgentMessage(
                from_agent="a",
                to_agent="b",
                type=MessageType.NOTIFICATION,
                payload={"i": i},
            )
            await message_bus.publish(msg)
        assert len(message_bus.history) == 5

    def test_clear_history(self, message_bus: MessageBus) -> None:
        """clear_history() 清空記錄。"""
        message_bus._history.append(
            AgentMessage(from_agent="a", to_agent="b", type=MessageType.NOTIFICATION)
        )
        message_bus.clear_history()
        assert len(message_bus.history) == 0

    @pytest.mark.asyncio()
    async def test_subscribe_topic(self, message_bus: MessageBus) -> None:
        """訂閱者收到對應主題的訊息。"""
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        message_bus.subscribe("test-topic", handler)
        msg = AgentMessage(
            from_agent="a",
            to_agent="test-topic",
            type=MessageType.NOTIFICATION,
            payload={},
        )
        await message_bus.publish(msg)
        assert len(received) == 1


# ── AgentInstanceRegistry Tests ──────────────────────────────


class TestAgentInstanceRegistry:
    """AgentInstanceRegistry 實例管理測試。"""

    def test_register_and_get(self, registry: AgentInstanceRegistry) -> None:
        """註冊代理後可透過 ID 取得。"""
        # 需要獨立的 MessageBus 避免影響全域
        agent = StubAgent("reg-test")
        registry._instances[agent.id] = agent  # 直接加入避免 bus 依賴
        assert registry.get("reg-test") is agent

    def test_get_nonexistent(self, registry: AgentInstanceRegistry) -> None:
        """查詢不存在的代理回傳 None。"""
        assert registry.get("nonexistent") is None

    def test_has(self, registry: AgentInstanceRegistry) -> None:
        """has() 正確判斷代理是否存在。"""
        agent = StubAgent("check-me")
        registry._instances[agent.id] = agent
        assert registry.has("check-me") is True
        assert registry.has("not-here") is False

    def test_get_all(self, registry: AgentInstanceRegistry) -> None:
        """get_all() 回傳所有已註冊代理。"""
        a1 = StubAgent("a1")
        a2 = StubAgent("a2")
        registry._instances[a1.id] = a1
        registry._instances[a2.id] = a2
        assert len(registry.get_all()) == 2

    def test_count(self, registry: AgentInstanceRegistry) -> None:
        """count 屬性回傳正確數量。"""
        assert registry.count == 0
        registry._instances["x"] = StubAgent("x")
        assert registry.count == 1

    def test_repr(self, registry: AgentInstanceRegistry) -> None:
        """__repr__ 包含數量資訊。"""
        assert "count=0" in repr(registry)


# ── TaskContext & TaskResult Tests ────────────────────────────


class TestDataModels:
    """任務上下文與結果資料模型測試。"""

    def test_task_context_defaults(self) -> None:
        """TaskContext 預設值正確。"""
        ctx = TaskContext()
        assert ctx.parameters == {}
        assert ctx.results == {}
        assert ctx.collaborators == []
        assert ctx.parent_task_id is None
        assert ctx.task_id  # 應自動生成

    def test_task_context_with_values(self) -> None:
        """TaskContext 可帶入自訂值。"""
        ctx = TaskContext(
            parameters={"key": "val"},
            collaborators=["agent-a"],
            parent_task_id="parent-123",
        )
        assert ctx.parameters["key"] == "val"
        assert ctx.collaborators == ["agent-a"]
        assert ctx.parent_task_id == "parent-123"

    def test_task_result_success(self) -> None:
        """成功的 TaskResult。"""
        result = TaskResult(status=TaskStatus.SUCCESS, summary="done")
        assert result.status == TaskStatus.SUCCESS
        assert result.errors == []

    def test_task_result_error(self) -> None:
        """失敗的 TaskResult。"""
        result = TaskResult(status=TaskStatus.ERROR, errors=["err1", "err2"])
        assert len(result.errors) == 2

    def test_agent_message_to_dict(self) -> None:
        """AgentMessage.to_dict() 序列化正確。"""
        msg = AgentMessage(
            from_agent="sender",
            to_agent="receiver",
            type=MessageType.TASK_REQUEST,
            payload={"data": 42},
        )
        d = msg.to_dict()
        assert d["from"] == "sender"
        assert d["to"] == "receiver"
        assert d["type"] == "task_request"
        assert d["payload"]["data"] == 42
        assert "message_id" in d
        assert "timestamp" in d


# ── Bootstrap Tests ──────────────────────────────────────────


class TestBootstrap:
    """bootstrap_agents() 整合測試。"""

    def test_bootstrap_registers_agents(self) -> None:
        """bootstrap_agents() 成功註冊所有已實作的代理。"""
        from src.agents.registry import bootstrap_agents

        registry = bootstrap_agents()
        assert registry.count >= 16

        # 驗證各 tier 至少有一個代理
        assert registry.get("project-director") is not None
        assert registry.get("scada-processor") is not None
        assert registry.get("fault-diagnostician") is not None
        assert registry.get("power-curve-expert") is not None
        assert registry.get("backend-dev") is not None
        assert registry.get("paper-writer") is not None

    def test_bootstrap_agents_have_capabilities(self) -> None:
        """所有已註冊代理都有宣告 capabilities。"""
        from src.agents.registry import bootstrap_agents

        registry = bootstrap_agents()
        for agent in registry.get_all():
            assert len(agent.capabilities) > 0, f"{agent.id} 沒有宣告 capabilities"


# ── Concrete Agent Tests ─────────────────────────────────────


class TestConcreteAgents:
    """具體代理類別的行為測試。"""

    @pytest.mark.asyncio()
    async def test_project_director_review(self) -> None:
        """ProjectDirector 執行審核任務。"""
        from src.agents.leadership.director import ProjectDirector

        agent = ProjectDirector()
        ctx = TaskContext()
        result = await agent.execute("審核成果", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert result.data.get("approved") is True

    @pytest.mark.asyncio()
    async def test_backend_dev_api_task(self) -> None:
        """BackendDev 執行 API 開發任務。"""
        from src.agents.engineering.backend_dev import BackendDev

        agent = BackendDev()
        ctx = TaskContext()
        result = await agent.execute("design API endpoint", ctx)
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio()
    async def test_test_engineer_unit_tests(self) -> None:
        """TestEngineer 執行單元測試任務。"""
        from src.agents.engineering.test_engineer import TestEngineer

        agent = TestEngineer()
        ctx = TaskContext(parameters={"target": "src/agents/"})
        result = await agent.execute("run unit tests", ctx)
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio()
    async def test_devops_pipeline_task(self) -> None:
        """DevOpsEngineer 執行 CI/CD 任務。"""
        from src.agents.engineering.devops_engineer import DevOpsEngineer

        agent = DevOpsEngineer()
        ctx = TaskContext()
        result = await agent.execute("update CI pipeline", ctx)
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio()
    async def test_literature_reviewer_search(self) -> None:
        """LiteratureReviewer 執行文獻搜索。"""
        from src.agents.research.literature_reviewer import LiteratureReviewer

        agent = LiteratureReviewer()
        ctx = TaskContext(parameters={"topic": "wind turbine SCADA"})
        result = await agent.execute("搜索文獻", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert result.data.get("total_found", 0) > 0

    @pytest.mark.asyncio()
    async def test_paper_writer_report(self) -> None:
        """PaperWriter 執行報告生成。"""
        from src.agents.research.paper_writer import PaperWriter

        agent = PaperWriter()
        ctx = TaskContext(results={"diagnosis": {"health_score": 85}})
        result = await agent.execute("生成診斷報告", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert "report_markdown" in result.data or "report_sections" in result.data

    @pytest.mark.asyncio()
    async def test_research_lead_review(self) -> None:
        """ResearchLead 執行審閱任務。"""
        from src.agents.leadership.research_lead import ResearchLead

        agent = ResearchLead()
        ctx = TaskContext()
        result = await agent.execute("審核分析方法", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert result.data.get("approved") is True
