"""wEng:frontend-dev — 前端開發者。

負責 React + TypeScript 前端元件開發、UI 設計與效能優化，
專注於虛擬辦公室介面與資料視覺化面板。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class FrontendDev(BaseAgent):
    """前端開發代理。

    能力：
    - React 元件開發
    - TypeScript 型別設計
    - Tailwind CSS 樣式設計
    - 資料視覺化元件（Recharts）
    - WebSocket 整合
    - 效能優化
    """

    def __init__(self) -> None:
        super().__init__("frontend-dev")

    @property
    def capabilities(self) -> list[str]:
        return [
            "react_component_development",
            "typescript_design",
            "tailwind_styling",
            "data_visualization",
            "websocket_integration",
            "performance_optimization",
            "responsive_design",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行前端開發任務。"""
        params = context.parameters

        if "component" in task or "元件" in task:
            return await self._design_component(params)

        if "review" in task or "審查" in task:
            return await self._review_code(params)

        if "optimize" in task or "優化" in task:
            return await self._optimize(params)

        await self.update_progress(0.5, f"前端開發：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"前端任務完成：{task}")

    async def _design_component(self, params: dict[str, Any]) -> TaskResult:
        """設計 React 元件規格。"""
        component_name = params.get("name", "UnnamedComponent")
        component_type = params.get("type", "functional")

        await self.update_progress(0.3, f"設計元件規格：{component_name}")

        spec = {
            "name": component_name,
            "type": component_type,
            "framework": "React 18 + TypeScript",
            "styling": "Tailwind CSS",
            "state_management": "useState / useMemo",
            "recommendations": [
                "使用 memo() 避免不必要的重新渲染",
                "使用 useCallback 穩定事件處理器",
                "TypeScript strict mode 確保型別安全",
            ],
        }

        await self.update_progress(1.0, f"元件 {component_name} 規格已完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=spec,
            summary=f"元件 '{component_name}' 規格設計完成",
        )

    async def _review_code(self, params: dict[str, Any]) -> TaskResult:
        """審查前端程式碼。"""
        target = params.get("target", "全部元件")
        await self.update_progress(0.5, f"審查前端程式碼：{target}")
        await self.update_progress(1.0, "程式碼審查完成")
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary=f"前端程式碼審查完成：{target}",
        )

    async def _optimize(self, params: dict[str, Any]) -> TaskResult:
        """前端效能優化建議。"""
        await self.update_progress(0.5, "分析前端效能")
        await self.update_progress(1.0, "效能分析完成")
        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "recommendations": [
                    "使用 React.memo 減少不必要重渲染",
                    "大列表使用虛擬滾動 (react-window)",
                    "圖表資料使用 useMemo 快取",
                    "WebSocket 訊息使用 useRef 避免閉包問題",
                ],
            },
            summary="前端效能優化建議已產出",
        )
