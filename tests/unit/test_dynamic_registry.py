"""DynamicAgentRegistry 測試。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from src.agents.dynamic_registry import DynamicAgentRegistry
from src.api.models import AgentStatus


def _write_yaml(directory: Path, filename: str, data: dict) -> Path:
    """在指定目錄寫入 YAML 檔案。"""
    filepath = directory / filename
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)
    return filepath


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """建立含測試 YAML 的暫時目錄。"""
    _write_yaml(
        tmp_path,
        "core-agent.yaml",
        {
            "id": "core-agent",
            "name": "wAI:core-agent",
            "display_name": "核心代理",
            "tier": "ai-ml",
            "core": True,
            "description": "核心測試代理",
            "skills": ["test_clean"],
            "task_routing": [
                {"match": ["test"], "pipeline": ["test_clean"]},
            ],
        },
    )
    _write_yaml(
        tmp_path,
        "optional-agent.yaml",
        {
            "id": "optional-agent",
            "name": "wData:optional-agent",
            "display_name": "選配代理",
            "tier": "data",
            "core": False,
            "description": "可選聘代理",
            "skills": [],
        },
    )
    _write_yaml(
        tmp_path,
        "leadership-agent.yaml",
        {
            "id": "leader-agent",
            "name": "wLab:leader",
            "display_name": "領導代理",
            "tier": "leadership",
            "core": True,
            "description": "領導層代理",
        },
    )
    return tmp_path


@pytest.fixture()
def registry(config_dir: Path) -> DynamicAgentRegistry:
    reg = DynamicAgentRegistry(config_dir=config_dir)
    return reg


class TestLoadSpecs:
    def test_load_specs_count(self, registry: DynamicAgentRegistry) -> None:
        count = registry.load_specs()
        assert count == 3

    def test_load_specs_creates_state(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        agents = registry.get_all_agents()
        assert len(agents) == 3

    def test_core_agents_start_idle(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        core = registry.get_agent("core-agent")
        assert core is not None
        assert core.status == AgentStatus.IDLE

    def test_noncore_agents_start_offline(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        optional = registry.get_agent("optional-agent")
        assert optional is not None
        assert optional.status == AgentStatus.OFFLINE

    def test_empty_directory(self, tmp_path: Path) -> None:
        """空目錄 → 載入 0 個。"""
        reg = DynamicAgentRegistry(config_dir=tmp_path)
        assert reg.load_specs() == 0

    def test_nonexistent_directory(self) -> None:
        """不存在的目錄 → 載入 0 個。"""
        reg = DynamicAgentRegistry(config_dir=Path("/nonexistent/path"))
        assert reg.load_specs() == 0

    def test_spec_and_instance_counts(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        assert registry.spec_count == 3
        assert registry.instance_count == 0  # 尚未 bootstrap


class TestBootstrapCore:
    def test_bootstrap_only_core(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        count = registry.bootstrap_core()
        assert count == 2  # core-agent + leader-agent
        assert registry.instance_count == 2

    def test_bootstrap_creates_instances(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        registry.bootstrap_core()
        assert registry.get_instance("core-agent") is not None
        assert registry.get_instance("optional-agent") is None

    def test_bootstrap_sets_status_idle(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        registry.bootstrap_core()
        model = registry.get_agent("core-agent")
        assert model is not None
        assert model.status == AgentStatus.IDLE


class TestHireAndFire:
    @pytest.mark.asyncio
    async def test_hire_success(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        model = await registry.hire("optional-agent")
        assert model.status == AgentStatus.IDLE
        assert registry.get_instance("optional-agent") is not None

    @pytest.mark.asyncio
    async def test_hire_nonexistent_raises(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        with pytest.raises(ValueError, match="不存在"):
            await registry.hire("ghost-agent")

    @pytest.mark.asyncio
    async def test_hire_already_hired_raises(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        await registry.hire("optional-agent")
        with pytest.raises(ValueError, match="已在職"):
            await registry.hire("optional-agent")

    @pytest.mark.asyncio
    async def test_fire_success(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        await registry.hire("optional-agent")
        await registry.fire("optional-agent")
        assert registry.get_instance("optional-agent") is None
        model = registry.get_agent("optional-agent")
        assert model is not None
        assert model.status == AgentStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_fire_not_hired_raises(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        with pytest.raises(ValueError, match="未在職"):
            await registry.fire("optional-agent")

    @pytest.mark.asyncio
    async def test_fire_core_raises(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        registry.bootstrap_core()
        with pytest.raises(ValueError, match="核心代理.*不可解聘"):
            await registry.fire("core-agent")


class TestUpgradeSkills:
    def test_upgrade_adds_skills(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        registry.upgrade_skills("core-agent", ["new_skill_a", "new_skill_b"])
        spec = registry._specs["core-agent"]
        assert "new_skill_a" in spec.skills
        assert "new_skill_b" in spec.skills

    def test_upgrade_no_duplicates(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        registry.upgrade_skills("core-agent", ["test_clean"])  # already in skills
        spec = registry._specs["core-agent"]
        assert spec.skills.count("test_clean") == 1

    def test_upgrade_nonexistent_raises(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        with pytest.raises(ValueError, match="不存在"):
            registry.upgrade_skills("ghost", ["skill_x"])


class TestQueryInterfaces:
    def test_get_all_agents(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        assert len(registry.get_all_agents()) == 3

    def test_get_active_agents(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        registry.bootstrap_core()
        active = registry.get_active_agents()
        assert len(active) == 2  # 2 core agents

    def test_get_available(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        registry.bootstrap_core()
        available = registry.get_available()
        assert len(available) == 1
        assert available[0]["id"] == "optional-agent"

    def test_update_agent_status(self, registry: DynamicAgentRegistry) -> None:
        registry.load_specs()
        result = registry.update_agent_status(
            "core-agent",
            status=AgentStatus.WORKING,
            current_task="清洗 SCADA 資料",
            progress=0.5,
        )
        assert result is not None
        assert result.status == AgentStatus.WORKING
        assert result.current_task == "清洗 SCADA 資料"
        assert result.progress == 0.5

    def test_update_nonexistent_returns_none(
        self, registry: DynamicAgentRegistry
    ) -> None:
        registry.load_specs()
        assert registry.update_agent_status("ghost", status=AgentStatus.IDLE) is None

    def test_get_agent_nonexistent(self, registry: DynamicAgentRegistry) -> None:
        assert registry.get_agent("ghost") is None
