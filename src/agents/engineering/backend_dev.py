"""wEng:backend-dev — 後端開發師。

負責 FastAPI 後端服務的設計與實作，開發 RESTful API 端點
與 WebSocket 即時通訊伺服器，整合 Celery 任務佇列。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class BackendDev(BaseAgent):
    """後端開發代理，負責 FastAPI 服務開發與 API 設計。"""

    def __init__(self) -> None:
        super().__init__("backend-dev")

    @property
    def capabilities(self) -> list[str]:
        return [
            "fastapi_development",
            "restful_api_implementation",
            "websocket_server_development",
            "celery_task_queue_integration",
            "database_orm_design",
            "authentication_authorization",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行後端開發任務。"""
        params = context.parameters

        if "api" in task.lower() or "endpoint" in task.lower():
            return await self._design_api(task, params)

        if "websocket" in task.lower():
            return await self._implement_websocket(task, params)

        if "database" in task.lower() or "orm" in task.lower():
            return await self._design_orm(task, params)

        # 通用後端開發任務
        await self.update_progress(0.3, f"分析需求：{task}")
        await self.update_progress(0.6, "實作中")
        await self.update_progress(1.0, "後端開發完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"task": task},
            summary=f"後端開發完成：{task}",
        )

    async def _design_api(self, task: str, params: dict[str, Any]) -> TaskResult:
        """設計並實作 API 端點。"""
        await self.update_progress(0.2, "分析 API 需求與路由設計")
        await self.update_progress(0.5, "實作 FastAPI 端點")
        await self.update_progress(0.8, "撰寫 Pydantic 模型與驗證")
        await self.update_progress(1.0, "API 端點實作完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"endpoint_count": params.get("endpoint_count", 1)},
            summary=f"API 設計完成：{task}",
        )

    async def _implement_websocket(self, task: str, params: dict[str, Any]) -> TaskResult:
        """實作 WebSocket 伺服器功能。"""
        await self.update_progress(0.3, "設計 WebSocket 訊息協定")
        await self.update_progress(0.7, "實作即時通訊處理器")
        await self.update_progress(1.0, "WebSocket 功能完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"feature": "websocket"},
            summary=f"WebSocket 實作完成：{task}",
        )

    async def _design_orm(self, task: str, params: dict[str, Any]) -> TaskResult:
        """設計 ORM 資料模型。"""
        await self.update_progress(0.3, "分析資料需求")
        await self.update_progress(0.6, "設計 SQLAlchemy 模型")
        await self.update_progress(1.0, "ORM 模型設計完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"feature": "orm_design"},
            summary=f"ORM 設計完成：{task}",
        )
