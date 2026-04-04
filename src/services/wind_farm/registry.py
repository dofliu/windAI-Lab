"""風場客戶註冊表 — 管理所有受監控的風場。

提供風場的 CRUD 操作、狀態查詢、統計摘要。
支援持久化至 JSON 檔案（未來可切換至 PostgreSQL）。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.services.wind_farm import (
    DataSourceConfig,
    DataSourceType,
    HealthLevel,
    WindFarm,
    WindFarmStatus,
)
from src.utils.logger import get_logger

logger = get_logger("wind_farm.registry")


class WindFarmRegistry:
    """風場客戶註冊表。"""

    def __init__(self, persist_path: str | None = None) -> None:
        self._farms: dict[str, WindFarm] = {}
        self._persist_path = persist_path or str(
            Path(__file__).resolve().parents[3] / "data" / "wind_farms.json"
        )
        self._load()

    # ── CRUD ────────────────────────────────────────────────

    def register(
        self,
        name: str,
        location: str = "",
        turbine_count: int = 0,
        rated_power_mw: float = 0.0,
        source_type: str = "local_file",
        source_path: str = "",
        poll_interval_min: int = 60,
        auto_diagnose: bool = True,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> WindFarm:
        """註冊新風場。

        Returns:
            新建的 WindFarm 實體。
        """
        farm = WindFarm(
            name=name,
            location=location,
            turbine_count=turbine_count,
            rated_power_mw=rated_power_mw,
            data_source=DataSourceConfig(
                source_type=DataSourceType(source_type),
                path=source_path,
            ),
            poll_interval_min=poll_interval_min,
            auto_diagnose=auto_diagnose,
            tags=tags or [],
            notes=notes,
        )
        self._farms[farm.id] = farm
        self._save()
        logger.info(f"風場已註冊：{farm.name} (id={farm.id})")
        return farm

    def get(self, farm_id: str) -> WindFarm | None:
        """取得風場。"""
        return self._farms.get(farm_id)

    def get_by_name(self, name: str) -> WindFarm | None:
        """依名稱查詢風場。"""
        for farm in self._farms.values():
            if farm.name == name:
                return farm
        return None

    def list_all(self) -> list[WindFarm]:
        """列出所有風場。"""
        return list(self._farms.values())

    def list_active(self) -> list[WindFarm]:
        """列出所有啟用中的風場。"""
        return [f for f in self._farms.values() if f.status == WindFarmStatus.ACTIVE]

    def update(self, farm_id: str, **kwargs: Any) -> WindFarm | None:
        """更新風場設定。"""
        farm = self._farms.get(farm_id)
        if farm is None:
            return None

        for key, value in kwargs.items():
            if hasattr(farm, key):
                setattr(farm, key, value)

        self._save()
        return farm

    def activate(self, farm_id: str) -> WindFarm | None:
        """啟用風場監控。"""
        return self.update(farm_id, status=WindFarmStatus.ACTIVE)

    def pause(self, farm_id: str) -> WindFarm | None:
        """暫停風場監控。"""
        return self.update(farm_id, status=WindFarmStatus.PAUSED)

    def remove(self, farm_id: str) -> bool:
        """移除風場。"""
        if farm_id in self._farms:
            name = self._farms[farm_id].name
            del self._farms[farm_id]
            self._save()
            logger.info(f"風場已移除：{name} (id={farm_id})")
            return True
        return False

    def update_turbine_health(
        self,
        farm_id: str,
        turbine_id: str,
        health_score: float,
        anomaly_count: int = 0,
        power_curve_deviation_pct: float = 0.0,
    ) -> HealthLevel:
        """更新風機健康狀態，回傳健康等級。"""
        from src.services.wind_farm import TurbineStatus

        farm = self._farms.get(farm_id)
        if farm is None:
            return HealthLevel.UNKNOWN

        if health_score >= farm.alert_threshold_warning:
            level = HealthLevel.HEALTHY
        elif health_score >= farm.alert_threshold_critical:
            level = HealthLevel.WARNING
        else:
            level = HealthLevel.CRITICAL

        farm.turbines[turbine_id] = TurbineStatus(
            turbine_id=turbine_id,
            health_score=health_score,
            health_level=level,
            last_check_at=datetime.now(UTC).isoformat(),
            anomaly_count=anomaly_count,
            power_curve_deviation_pct=power_curve_deviation_pct,
        )
        farm.last_health_check_at = datetime.now(UTC).isoformat()
        self._save()
        return level

    # ── 統計 ────────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        """取得全系統摘要。"""
        farms = list(self._farms.values())
        active = [f for f in farms if f.status == WindFarmStatus.ACTIVE]

        # 統計各健康等級的風機數
        health_counts: dict[str, int] = {
            "healthy": 0,
            "warning": 0,
            "critical": 0,
            "unknown": 0,
        }
        for farm in farms:
            for t in farm.turbines.values():
                health_counts[t.health_level] = health_counts.get(t.health_level, 0) + 1

        return {
            "total_farms": len(farms),
            "active_farms": len(active),
            "total_turbines": sum(f.turbine_count for f in farms),
            "monitored_turbines": sum(len(f.turbines) for f in farms),
            "total_capacity_mw": round(sum(f.rated_power_mw for f in farms), 1),
            "health_distribution": health_counts,
        }

    # ── 序列化 ──────────────────────────────────────────────

    def to_dict_list(self) -> list[dict[str, Any]]:
        """序列化所有風場為 dict（供 API 回傳）。"""
        results = []
        for farm in self._farms.values():
            d = asdict(farm)
            # 移除敏感欄位
            if "data_source" in d:
                d["data_source"].pop("auth_token", None)
                d["data_source"].pop("password", None)
            results.append(d)
        return results

    def _save(self) -> None:
        """持久化至 JSON。"""
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for fid, farm in self._farms.items():
                d = asdict(farm)
                # 不持久化敏感資訊的明文
                if "data_source" in d:
                    d["data_source"].pop("auth_token", None)
                    d["data_source"].pop("password", None)
                data[fid] = d
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"風場資料持久化失敗：{e}")

    def _load(self) -> None:
        """從 JSON 載入。"""
        path = Path(self._persist_path)
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for fid, d in raw.items():
                ds = d.pop("data_source", {})
                turbines_raw = d.pop("turbines", {})
                farm = WindFarm(**d)
                farm.data_source = DataSourceConfig(**ds)
                # 重建 turbines
                from src.services.wind_farm import TurbineStatus

                for tid, t in turbines_raw.items():
                    farm.turbines[tid] = TurbineStatus(**t)
                self._farms[fid] = farm
            logger.info(f"已載入 {len(self._farms)} 個風場")
        except Exception as e:
            logger.warning(f"風場資料載入失敗：{e}")


# 全域單例
wind_farm_registry = WindFarmRegistry()
