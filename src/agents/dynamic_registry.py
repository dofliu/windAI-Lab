"""動態代理註冊表 — 從 YAML 載入代理定義，支援聘用/解聘/技能更新。

統一管理代理的「定義」（AgentSpec from YAML）、「狀態」（AgentModel）、
「實例」（BaseAgent subclass），取代原本分散的 agent_registry 與 registry。
"""

from __future__ import annotations

import importlib
from datetime import UTC
from pathlib import Path
from typing import Any

import yaml

from src.agents.base import BaseAgent  # noqa: TCH001
from src.agents.message_bus import bus
from src.agents.skill_composing_agent import AgentSpec, SkillComposingAgent
from src.api.models import AgentModel, AgentStatus, AgentTier  # noqa: TCH001
from src.api.websocket_manager import manager as ws_manager
from src.skills.registry import SkillRegistry, skill_registry
from src.utils.logger import get_logger

logger = get_logger("dynamic_registry")

# Tier 字串 → AgentTier 列舉對照
_TIER_MAP: dict[str, AgentTier] = {
    "leadership": AgentTier.LEADERSHIP,
    "data": AgentTier.DATA,
    "ai-ml": AgentTier.AI_ML,
    "domain": AgentTier.DOMAIN,
    "engineering": AgentTier.ENGINEERING,
    "research": AgentTier.RESEARCH,
}


class DynamicAgentRegistry:
    """統一的代理生命週期管理器。

    職責：
    1. 從 configs/agents/registry/*.yaml 載入所有代理定義
    2. 啟動時只實例化 core=True 的代理
    3. 支援 hire/fire/upgrade 動態操作
    4. 提供所有舊版 API 的相容介面
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or (
            Path(__file__).resolve().parents[2] / "configs" / "agents" / "registry"
        )
        self._specs: dict[str, AgentSpec] = {}
        self._state: dict[str, AgentModel] = {}
        self._instances: dict[str, BaseAgent] = {}
        self._skill_registry: SkillRegistry = skill_registry

    # ── 初始化 ──

    def load_specs(self) -> int:
        """從 YAML 目錄載入所有代理定義。

        Returns
        -------
        int
            載入的代理定義數量。
        """
        if not self._config_dir.exists():
            logger.warning(f"代理設定目錄不存在：{self._config_dir}")
            return 0

        count = 0
        for yaml_file in sorted(self._config_dir.glob("*.yaml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and "id" in data:
                    spec = AgentSpec.from_yaml_dict(data)
                    self._specs[spec.id] = spec

                    # 建立對應的 AgentModel 狀態
                    self._state[spec.id] = AgentModel(
                        id=spec.id,
                        name=spec.name,
                        display_name=spec.display_name,
                        tier=_TIER_MAP.get(spec.tier, AgentTier.RESEARCH),
                        status=AgentStatus.OFFLINE if not spec.core else AgentStatus.IDLE,
                        current_task=None,
                        progress=0.0,
                        collaborating_with=[],
                        color=spec.color,
                        icon=spec.icon,
                    )
                    count += 1
            except Exception as e:
                logger.warning(f"載入 YAML 失敗：{yaml_file.name} — {e}")

        logger.info(
            f"載入 {count} 個代理定義（{sum(1 for s in self._specs.values() if s.core)} 個核心）"
        )
        return count

    def bootstrap_core(self) -> int:
        """只實例化 core=True 的代理。

        Returns
        -------
        int
            啟動的核心代理數量。
        """
        # 先自動發現技能
        self._skill_registry.auto_discover()

        count = 0
        for spec in self._specs.values():
            if not spec.core:
                continue
            try:
                agent = self._create_agent(spec)
                self._instances[spec.id] = agent
                bus.register(agent)
                self._state[spec.id].status = AgentStatus.IDLE
                count += 1
                logger.debug(f"核心代理已啟動：{spec.id} ({agent.__class__.__name__})")
            except Exception as e:
                logger.error(f"核心代理啟動失敗：{spec.id} — {e}")

        logger.info(f"已啟動 {count} 個核心代理")
        return count

    # ── 聘用 / 解聘 ──

    async def hire(self, agent_id: str) -> AgentModel:
        """聘用代理：建立實例、註冊、廣播狀態。

        Parameters
        ----------
        agent_id : str
            要聘用的代理 ID（必須存在於 YAML 定義中）。

        Returns
        -------
        AgentModel
            聘用後的代理狀態。

        Raises
        ------
        ValueError
            代理不存在或已聘用。
        """
        if agent_id not in self._specs:
            raise ValueError(f"代理 '{agent_id}' 不存在於定義中")
        if agent_id in self._instances:
            raise ValueError(f"代理 '{agent_id}' 已在職")

        spec = self._specs[agent_id]
        agent = self._create_agent(spec)
        self._instances[agent_id] = agent
        bus.register(agent)

        # 更新狀態
        self._state[agent_id].status = AgentStatus.IDLE
        model = self._state[agent_id]

        # WebSocket 廣播
        await ws_manager.broadcast(
            {
                "type": "agent_hired",
                "timestamp": _iso_now(),
                "payload": model.model_dump(mode="json"),
            }
        )

        logger.info(f"代理已聘用：{agent_id} ({spec.display_name})")
        return model

    async def fire(self, agent_id: str) -> None:
        """解聘代理：移除實例、設為 offline、廣播狀態。

        不會刪除 YAML 定義，可以重新聘用。
        """
        if agent_id not in self._instances:
            raise ValueError(f"代理 '{agent_id}' 未在職")

        spec = self._specs.get(agent_id)
        if spec and spec.core:
            raise ValueError(f"核心代理 '{agent_id}' 不可解聘")

        # 移除實例
        self._instances.pop(agent_id)
        bus.unregister(agent_id)

        # 更新狀態
        self._state[agent_id].status = AgentStatus.OFFLINE
        self._state[agent_id].current_task = None
        self._state[agent_id].progress = 0.0

        # WebSocket 廣播
        await ws_manager.broadcast(
            {
                "type": "agent_fired",
                "timestamp": _iso_now(),
                "payload": {"agent_id": agent_id},
            }
        )

        logger.info(f"代理已解聘：{agent_id}")

    # ── 技能管理 ──

    def upgrade_skills(self, agent_id: str, skill_ids: list[str]) -> None:
        """為代理新增技能。"""
        if agent_id not in self._specs:
            raise ValueError(f"代理 '{agent_id}' 不存在")

        spec = self._specs[agent_id]
        for sid in skill_ids:
            if sid not in spec.skills:
                spec.skills.append(sid)

        logger.info(f"已更新 {agent_id} 的技能：{spec.skills}")

    # ── 查詢介面（相容舊版 API）──

    def get_agent(self, agent_id: str) -> AgentModel | None:
        """取得代理狀態。"""
        return self._state.get(agent_id)

    def get_all_agents(self) -> list[AgentModel]:
        """取得所有代理狀態（含未聘用的）。"""
        return list(self._state.values())

    def get_active_agents(self) -> list[AgentModel]:
        """取得所有已聘用的代理。"""
        return [m for m in self._state.values() if m.status != AgentStatus.OFFLINE]

    def get_available(self) -> list[dict[str, Any]]:
        """取得可聘用但未啟用的代理清單。"""
        result = []
        for agent_id, spec in self._specs.items():
            if agent_id not in self._instances:
                result.append(
                    {
                        "id": spec.id,
                        "name": spec.name,
                        "display_name": spec.display_name,
                        "tier": spec.tier,
                        "color": spec.color,
                        "icon": spec.icon,
                        "description": spec.description,
                        "skills": spec.skills,
                    }
                )
        return result

    def get_instance(self, agent_id: str) -> BaseAgent | None:
        """取得代理實例（給 orchestration engine 用）。"""
        return self._instances.get(agent_id)

    def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus | None = None,
        current_task: str | None = None,
        progress: float | None = None,
        collaborating_with: list[str] | None = None,
    ) -> AgentModel | None:
        """更新代理狀態（相容舊版介面）。"""
        model = self._state.get(agent_id)
        if model is None:
            return None

        if status is not None:
            model.status = status
        if current_task is not None:
            model.current_task = current_task
        if progress is not None:
            model.progress = progress
        if collaborating_with is not None:
            model.collaborating_with = collaborating_with

        return model

    @property
    def instance_count(self) -> int:
        """已啟動的代理實例數量。"""
        return len(self._instances)

    @property
    def spec_count(self) -> int:
        """YAML 定義的代理總數。"""
        return len(self._specs)

    # ── 內部方法 ──

    def _create_agent(self, spec: AgentSpec) -> BaseAgent:
        """根據 spec 建立代理實例。

        如果 spec 有 custom_class，則動態載入該 class；
        否則使用通用的 SkillComposingAgent。
        """
        if spec.custom_class:
            try:
                module_path, class_name = spec.custom_class.rsplit(".", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                return cls()
            except Exception as e:
                logger.warning(
                    f"無法載入自訂 class {spec.custom_class}，" f"改用 SkillComposingAgent：{e}"
                )

        return SkillComposingAgent(spec, self._skill_registry)


def _iso_now() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


# 全域單例
dynamic_registry = DynamicAgentRegistry()
