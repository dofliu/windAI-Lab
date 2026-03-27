"""技能註冊表 — 管理所有可用技能的集中查詢與自動發現。

啟動時自動掃描 src/skills/ 下所有 BaseSkill 子類別並註冊。
代理透過 skill_id 查詢取得技能實例。
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill
from src.utils.logger import get_logger

logger = get_logger("skills.registry")


class SkillRegistry:
    """技能集中註冊表。"""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """註冊技能實例。"""
        if not skill.skill_id:
            raise ValueError(f"技能 {skill.__class__.__name__} 缺少 skill_id")
        self._skills[skill.skill_id] = skill
        logger.debug(f"技能已註冊：{skill.skill_id} ({skill.display_name})")

    def get(self, skill_id: str) -> BaseSkill | None:
        """依 ID 取得技能。"""
        return self._skills.get(skill_id)

    def get_all(self) -> list[BaseSkill]:
        """取得所有已註冊技能。"""
        return list(self._skills.values())

    def list_ids(self) -> list[str]:
        """列出所有已註冊技能 ID。"""
        return list(self._skills.keys())

    def has(self, skill_id: str) -> bool:
        """檢查技能是否已註冊。"""
        return skill_id in self._skills

    @property
    def count(self) -> int:
        return len(self._skills)

    def to_dict_list(self) -> list[dict[str, Any]]:
        """序列化為前端可用的清單。"""
        return [
            {
                "skill_id": s.skill_id,
                "display_name": s.display_name,
                "description": s.description,
                "version": s.version,
            }
            for s in self._skills.values()
        ]

    def auto_discover(self) -> int:
        """自動掃描 src/skills/ 下所有子模組，找到 BaseSkill 子類別並註冊。

        Returns
        -------
        int
            新發現並註冊的技能數量。
        """
        skills_root = Path(__file__).parent
        count_before = self.count

        for subdir in ["data", "ml", "features", "reporting", "rag"]:
            pkg_path = skills_root / subdir
            if not pkg_path.exists():
                continue
            pkg_name = f"src.skills.{subdir}"

            for _importer, module_name, _is_pkg in pkgutil.iter_modules([str(pkg_path)]):
                full_name = f"{pkg_name}.{module_name}"
                try:
                    mod = importlib.import_module(full_name)
                except Exception:
                    logger.warning(f"無法載入技能模組：{full_name}")
                    continue

                # 找出模組中所有 BaseSkill 子類別
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseSkill)
                        and attr is not BaseSkill
                        and attr.skill_id  # 必須有 skill_id
                        and not self.has(attr.skill_id)
                    ):
                        try:
                            instance = attr()
                            self.register(instance)
                        except Exception:
                            logger.warning(f"無法實例化技能：{attr_name}")

        discovered = self.count - count_before
        if discovered:
            logger.info(f"自動發現 {discovered} 個技能")
        return discovered


# 全域單例
skill_registry = SkillRegistry()
