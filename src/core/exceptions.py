"""WindAI Lab 自定義例外類別。

集中定義所有應用程式特有的例外，方便統一錯誤處理與日誌記錄。
"""

from __future__ import annotations


class WindAIError(Exception):
    """WindAI Lab 基礎例外類別。"""

    def __init__(self, message: str = "發生未預期的錯誤") -> None:
        self.message = message
        super().__init__(self.message)


# ── 代理相關 ──


class AgentNotFoundError(WindAIError):
    """指定的代理不存在。"""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"代理 '{agent_id}' 不存在")
        self.agent_id = agent_id


class AgentBusyError(WindAIError):
    """代理正在執行其他任務。"""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"代理 '{agent_id}' 正在執行其他任務，無法接受新任務")
        self.agent_id = agent_id


# ── 工作流程相關 ──


class WorkflowNotFoundError(WindAIError):
    """指定的工作流程不存在。"""

    def __init__(self, workflow_name: str) -> None:
        super().__init__(f"工作流程 '{workflow_name}' 不存在")
        self.workflow_name = workflow_name


class WorkflowExecutionError(WindAIError):
    """工作流程執行過程中發生錯誤。"""

    def __init__(self, workflow_name: str, reason: str) -> None:
        super().__init__(f"工作流程 '{workflow_name}' 執行失敗：{reason}")
        self.workflow_name = workflow_name
        self.reason = reason


# ── 資料相關 ──


class DataLoadError(WindAIError):
    """資料載入失敗。"""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"無法載入資料 '{source}'：{reason}")
        self.source = source
        self.reason = reason


class DataValidationError(WindAIError):
    """資料驗證失敗。"""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"資料驗證失敗 — 欄位 '{field}'：{reason}")
        self.field = field
        self.reason = reason


# ── 模型相關 ──


class ModelNotFoundError(WindAIError):
    """指定的模型不存在。"""

    def __init__(self, model_name: str) -> None:
        super().__init__(f"模型 '{model_name}' 不存在於註冊表中")
        self.model_name = model_name


class ModelTrainingError(WindAIError):
    """模型訓練過程中發生錯誤。"""

    def __init__(self, model_name: str, reason: str) -> None:
        super().__init__(f"模型 '{model_name}' 訓練失敗：{reason}")
        self.model_name = model_name
        self.reason = reason
