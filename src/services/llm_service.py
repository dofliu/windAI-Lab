"""LLM 服務 — 透過 Gemini API 進行文字生成。

提供統一的 LLM 介面供 RAG 問答、文件分類、規格萃取等功能使用。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("service.llm")


class LLMService:
    """Gemini LLM 服務封裝。"""

    def __init__(self, model_name: str = "gemini-3-flash-preview") -> None:
        self._model_name = model_name
        self._client: Any = None

    @property
    def client(self) -> Any:
        """延遲載入 Gemini 客戶端。"""
        if self._client is None:
            from google import genai

            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise RuntimeError("未設定 GEMINI_API_KEY 環境變數")

            self._client = genai.Client(api_key=api_key)
            logger.info(f"Gemini 客戶端已初始化，模型：{self._model_name}")
        return self._client

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """呼叫 Gemini 生成文字。

        Args:
            prompt: 使用者提示。
            system_instruction: 系統指令。
            temperature: 生成溫度（0.0–1.0）。
            max_tokens: 最大生成 token 數。

        Returns:
            生成的文字回覆。
        """
        try:
            config: dict[str, Any] = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if system_instruction:
                config["system_instruction"] = system_instruction

            response = self.client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            logger.info(f"LLM 生成完成，長度：{len(text)} 字元")
            return text
        except Exception as e:
            logger.error(f"LLM 生成失敗：{e}")
            raise

    def rag_answer(
        self,
        query: str,
        contexts: list[dict[str, Any]],
        language: str = "繁體中文",
    ) -> str:
        """基於 RAG 檢索結果生成回答。

        Args:
            query: 使用者的問題。
            contexts: 檢索到的文件片段列表，每個包含 content, source, relevance。
            language: 回答語言。

        Returns:
            LLM 整理後的回答。
        """
        if not contexts:
            return "知識庫中未找到相關文件，無法回答此問題。"

        # 組裝 context 文字
        context_parts: list[str] = []
        for i, ctx in enumerate(contexts, 1):
            source = ctx.get("source", "未知來源")
            relevance = ctx.get("relevance", 0)
            content = ctx.get("content", "")
            context_parts.append(
                f"[文件 {i}] 來源：{source}（相關度：{relevance:.0%}）\n{content}"
            )
        context_text = "\n\n---\n\n".join(context_parts)

        system_instruction = (
            f"你是風力發電領域的 AI 研究助理。"
            f"請根據以下檢索到的文件片段回答使用者的問題。"
            f"回答要求：\n"
            f"1. 使用{language}回答\n"
            f"2. 條理清晰，重點明確\n"
            f"3. 若文件中有具體數據或規格，請引用\n"
            f"4. 標註資訊來源（文件編號）\n"
            f"5. 若檢索內容不足以完整回答，請誠實說明"
        )

        prompt = (
            f"## 檢索到的相關文件\n\n{context_text}\n\n"
            f"---\n\n"
            f"## 使用者問題\n\n{query}\n\n"
            f"請根據上述文件回答問題。"
        )

        return self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,
            max_tokens=2048,
        )

    # ── 檔案分類 ─────────────────────────────────────────────────

    # 副檔名 fallback 規則
    _EXT_CATEGORY: dict[str, str] = {
        ".csv": "scada_data",
        ".tsv": "scada_data",
        ".parquet": "scada_data",
        ".xlsx": "scada_data",
        ".xls": "scada_data",
        ".pdf": "specification_doc",
        ".txt": "specification_doc",
        ".md": "specification_doc",
        ".docx": "specification_doc",
        ".doc": "specification_doc",
        ".jpg": "photo",
        ".jpeg": "photo",
        ".png": "photo",
        ".bmp": "photo",
    }

    def classify_files(
        self,
        file_summaries: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """使用 LLM 智能分類檔案。

        Args:
            file_summaries: [{name, extension, head_text}] 每個檔案的摘要。

        Returns:
            [{name, category}] 分類結果。
        """
        if not file_summaries:
            return []

        # 組裝 prompt
        file_lines: list[str] = []
        for i, f in enumerate(file_summaries):
            preview = f.get("head_text", "")[:200].replace("\n", " ")
            file_lines.append(
                f"{i}. {f['name']} (副檔名: {f['extension']})"
                + (f" | 內容預覽: {preview}" if preview else "")
            )
        file_list = "\n".join(file_lines)

        prompt = (
            f"以下是一個風力發電專案資料夾中的檔案清單。請判斷每個檔案的類別。\n\n"
            f"## 檔案清單\n{file_list}\n\n"
            f"## 分類類別\n"
            f"- scada_data：SCADA 運轉資料、感測器數據、時序資料\n"
            f"- specification_doc：技術規格書、使用手冊、設計文件\n"
            f"- maintenance_report：維護報告、故障紀錄、檢修文件\n"
            f"- photo：照片、圖片\n"
            f"- unknown：無法判斷\n\n"
            f'請僅輸出 JSON 陣列，格式：[{{"index": 0, "category": "scada_data"}}, ...]\n'
            f"不要輸出其他文字。"
        )

        try:
            raw = self.generate(prompt=prompt, temperature=0.1, max_tokens=4096)
            # 清除 markdown code fence，嘗試提取 JSON 陣列
            cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
            # 找到第一個 [ 和最後一個 ] 之間的內容
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
            parsed = json.loads(cleaned)

            result: list[dict[str, str]] = []
            for i, f in enumerate(file_summaries):
                cat = "unknown"
                for item in parsed:
                    if item.get("index") == i:
                        cat = item.get("category", "unknown")
                        break
                result.append({"name": f["name"], "category": cat})
            return result

        except Exception as e:
            logger.warning(f"LLM 檔案分類失敗，使用 fallback：{e}")
            return self._classify_by_extension(file_summaries)

    def _classify_by_extension(self, file_summaries: list[dict[str, str]]) -> list[dict[str, str]]:
        """副檔名 fallback 分類。"""
        return [
            {
                "name": f["name"],
                "category": self._EXT_CATEGORY.get(f["extension"].lower(), "unknown"),
            }
            for f in file_summaries
        ]

    # ── 風機規格萃取 ─────────────────────────────────────────────

    def extract_turbine_specs(
        self,
        rag_contexts: list[dict[str, Any]],
        turbine_hint: str = "",
    ) -> dict[str, Any]:
        """從 RAG 檢索結果中萃取結構化風機規格。

        Args:
            rag_contexts: [{content, source, relevance}] 檢索結果。
            turbine_hint: 風機型號提示。

        Returns:
            結構化規格字典（欄位可能為 null）。
        """
        if not rag_contexts:
            return {}

        context_parts = [
            f"[文件 {i+1}] {ctx.get('source', '未知')}\n{ctx['content']}"
            for i, ctx in enumerate(rag_contexts)
        ]
        context_text = "\n\n---\n\n".join(context_parts)

        prompt = (
            f"根據以下風力發電相關文件，萃取風機技術規格。\n\n"
            f"## 文件內容\n{context_text}\n\n"
            f"{'## 風機型號提示：' + turbine_hint + chr(10) if turbine_hint else ''}"
            f"## 要求\n"
            f"請萃取以下欄位，輸出為 JSON 物件。找不到的欄位設為 null。\n"
            f"- turbine_model: 風機型號（字串）\n"
            f"- manufacturer: 製造商（字串）\n"
            f"- rated_power_kw: 額定功率 kW（數字）\n"
            f"- cut_in_speed_ms: 切入風速 m/s（數字）\n"
            f"- cut_out_speed_ms: 切出風速 m/s（數字）\n"
            f"- rated_wind_speed_ms: 額定風速 m/s（數字）\n"
            f"- rotor_diameter_m: 轉子直徑 m（數字）\n"
            f"- hub_height_m: 輪轂高度 m（數字）\n\n"
            f"僅輸出 JSON，不要其他文字。"
        )

        try:
            raw = self.generate(prompt=prompt, temperature=0.1, max_tokens=1024)
            cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
            # 提取 JSON 物件
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
            specs = json.loads(cleaned)
            logger.info(f"風機規格萃取成功：{specs.get('turbine_model', '未知型號')}")
            return specs
        except Exception as e:
            logger.warning(f"風機規格萃取失敗：{e}")
            return {}
