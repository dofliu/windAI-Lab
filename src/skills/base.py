"""技能模組基底介面。

每個技能是一個獨立的可重用單元，具有標準化的輸入/輸出格式。
代理透過組合多個技能來執行任務，技能本身不依賴任何代理。

使用方式：
    class MySkill(BaseSkill):
        skill_id = "my_skill"
        display_name = "我的技能"

        async def execute(self, inp, progress_cb=None):
            # ... 執行邏輯
            return SkillOutput(status=SkillStatus.SUCCESS, data={...})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SkillStatus(StrEnum):
    """技能執行結果狀態。"""

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class SkillInput:
    """技能的統一輸入格式。

    Attributes
    ----------
    parameters : dict
        任務參數（如 turbine_id、file_path 等）。
    data : Any
        上游技能傳入的資料（如 DataFrame）。
    context : dict
        額外上下文（如前一步驟的結果摘要）。
    dataframe : Any
        明確的 DataFrame 傳遞（優先於 data）。
    """

    parameters: dict[str, Any] = field(default_factory=dict)
    data: Any = None
    context: dict[str, Any] = field(default_factory=dict)
    dataframe: Any = None


@dataclass
class SkillOutput:
    """技能的統一輸出格式。

    Attributes
    ----------
    status : SkillStatus
        執行結果狀態。
    data : dict
        主要輸出資料（可被下游技能消費）。
    summary : str
        人類可讀的結果摘要。
    errors : list[str]
        錯誤訊息列表。
    artifacts : dict
        附加產出物（如圖表路徑、模型檔案等）。
    dataframe : Any
        若輸出包含 DataFrame，放在這裡供下游直接使用。
    """

    status: SkillStatus = SkillStatus.SUCCESS
    data: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    errors: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    dataframe: Any = None


# 進度回呼型別
ProgressCallback = Callable[[float, str], Coroutine[Any, Any, None]] | None


class BaseSkill(ABC):
    """所有技能的抽象基底。

    子類別必須定義 class 屬性並實作 execute()。
    """

    skill_id: str = ""
    display_name: str = ""
    description: str = ""
    version: str = "1.0.0"

    @abstractmethod
    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行技能。

        Parameters
        ----------
        inp : SkillInput
            輸入資料與參數。
        progress_cb : callable | None
            進度回呼，簽名 ``async (progress: float, message: str) -> None``。

        Returns
        -------
        SkillOutput
            執行結果。
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} skill_id={self.skill_id!r}>"
