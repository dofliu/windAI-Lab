"""SkillRegistry 與 BaseSkill 基礎架構測試。"""

from __future__ import annotations

import pytest

from src.skills.base import BaseSkill, SkillInput, SkillOutput, SkillStatus
from src.skills.registry import SkillRegistry

# ── 測試用假技能 ──


class DummySkill(BaseSkill):
    skill_id = "dummy_skill"
    display_name = "虛擬技能"
    description = "用於測試的虛擬技能"
    version = "0.1.0"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"echo": inp.parameters.get("msg", "hello")},
            summary="dummy done",
        )


class AnotherSkill(BaseSkill):
    skill_id = "another_skill"
    display_name = "另一個技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput(status=SkillStatus.SUCCESS, summary="another done")


class NoIdSkill(BaseSkill):
    """缺少 skill_id 的無效技能。"""

    display_name = "無 ID 技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput()


# ── SkillInput / SkillOutput 資料模型 ──


class TestSkillDataModels:
    def test_skill_input_defaults(self) -> None:
        inp = SkillInput()
        assert inp.parameters == {}
        assert inp.data is None
        assert inp.context == {}
        assert inp.dataframe is None

    def test_skill_input_with_values(self) -> None:
        inp = SkillInput(
            parameters={"turbine_id": "T01"},
            data=[1, 2, 3],
            context={"prev_step": "ok"},
        )
        assert inp.parameters["turbine_id"] == "T01"
        assert inp.data == [1, 2, 3]
        assert inp.context["prev_step"] == "ok"

    def test_skill_output_defaults(self) -> None:
        out = SkillOutput()
        assert out.status == SkillStatus.SUCCESS
        assert out.data == {}
        assert out.summary == ""
        assert out.errors == []
        assert out.artifacts == {}
        assert out.dataframe is None

    def test_skill_output_error(self) -> None:
        out = SkillOutput(
            status=SkillStatus.ERROR,
            errors=["file not found"],
            summary="載入失敗",
        )
        assert out.status == SkillStatus.ERROR
        assert len(out.errors) == 1

    def test_skill_status_values(self) -> None:
        assert SkillStatus.SUCCESS == "success"
        assert SkillStatus.PARTIAL == "partial"
        assert SkillStatus.ERROR == "error"


# ── SkillRegistry ──


class TestSkillRegistry:
    @pytest.fixture()
    def registry(self) -> SkillRegistry:
        return SkillRegistry()

    def test_register_and_get(self, registry: SkillRegistry) -> None:
        skill = DummySkill()
        registry.register(skill)
        assert registry.get("dummy_skill") is skill

    def test_register_missing_id_raises(self, registry: SkillRegistry) -> None:
        with pytest.raises(ValueError, match="缺少 skill_id"):
            registry.register(NoIdSkill())

    def test_has(self, registry: SkillRegistry) -> None:
        registry.register(DummySkill())
        assert registry.has("dummy_skill") is True
        assert registry.has("nonexistent") is False

    def test_get_nonexistent(self, registry: SkillRegistry) -> None:
        assert registry.get("nonexistent") is None

    def test_list_ids(self, registry: SkillRegistry) -> None:
        registry.register(DummySkill())
        registry.register(AnotherSkill())
        ids = registry.list_ids()
        assert "dummy_skill" in ids
        assert "another_skill" in ids

    def test_get_all(self, registry: SkillRegistry) -> None:
        registry.register(DummySkill())
        registry.register(AnotherSkill())
        assert len(registry.get_all()) == 2

    def test_count(self, registry: SkillRegistry) -> None:
        assert registry.count == 0
        registry.register(DummySkill())
        assert registry.count == 1

    def test_to_dict_list(self, registry: SkillRegistry) -> None:
        registry.register(DummySkill())
        result = registry.to_dict_list()
        assert len(result) == 1
        item = result[0]
        assert item["skill_id"] == "dummy_skill"
        assert item["display_name"] == "虛擬技能"
        assert item["description"] == "用於測試的虛擬技能"
        assert item["version"] == "0.1.0"

    def test_register_duplicate_overwrites(self, registry: SkillRegistry) -> None:
        """重複註冊同 ID 技能會覆蓋。"""
        skill1 = DummySkill()
        skill2 = DummySkill()
        registry.register(skill1)
        registry.register(skill2)
        assert registry.get("dummy_skill") is skill2
        assert registry.count == 1

    def test_auto_discover_returns_int(self, registry: SkillRegistry) -> None:
        """auto_discover 應回傳整數（發現的數量）。"""
        result = registry.auto_discover()
        assert isinstance(result, int)
        assert result >= 0


# ── BaseSkill 行為 ──


class TestBaseSkill:
    @pytest.mark.asyncio
    async def test_execute_returns_output(self) -> None:
        skill = DummySkill()
        inp = SkillInput(parameters={"msg": "test"})
        result = await skill.execute(inp)
        assert result.status == SkillStatus.SUCCESS
        assert result.data["echo"] == "test"

    @pytest.mark.asyncio
    async def test_execute_with_progress_callback(self) -> None:
        """確認 progress callback 不影響執行。"""
        skill = DummySkill()
        inp = SkillInput()

        progress_calls: list[tuple[float, str]] = []

        async def track_progress(p: float, msg: str) -> None:
            progress_calls.append((p, msg))

        result = await skill.execute(inp, progress_cb=track_progress)
        assert result.status == SkillStatus.SUCCESS

    def test_repr(self) -> None:
        skill = DummySkill()
        assert "DummySkill" in repr(skill)
        assert "dummy_skill" in repr(skill)

    def test_class_attributes(self) -> None:
        skill = DummySkill()
        assert skill.skill_id == "dummy_skill"
        assert skill.display_name == "虛擬技能"
        assert skill.version == "0.1.0"
