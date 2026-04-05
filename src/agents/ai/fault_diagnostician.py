"""wAI:fault-diagnostician — 故障診斷師。

負責風機故障分類、多標籤診斷、嚴重度評估與根因分析，
整合 ML 故障分類器、NBM 異常偵測、統計分析與 LLM 推理。

WindGuard AI 整合：在統計/ML 分析完成後，將結果送入 LLM
進行深層故障推理，產出具體故障類型、物理機制與維護建議。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class FaultDiagnostician(BaseAgent):
    """故障診斷代理，執行風機故障分類與異常偵測。

    支援兩種模式：
    - 基礎模式：統計 + ML 分析（無需 LLM API）
    - WindGuard 模式：統計 + ML + LLM 深層推理（需 GEMINI_API_KEY）
    """

    def __init__(self) -> None:
        super().__init__("fault-diagnostician")

    @property
    def capabilities(self) -> list[str]:
        return [
            "fault_classification",
            "anomaly_detection",
            "severity_assessment",
            "root_cause_analysis",
            "vibration_analysis",
            "power_curve_deviation",
            "ml_diagnosis",
            "llm_reasoning",
            "fleet_scanning",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行故障診斷任務。"""
        params = context.parameters
        task_lower = task.lower()

        if "fleet" in task_lower or "風場" in task or "批次" in task:
            return await self._run_fleet_scan(params)

        if "diagnose" in task_lower or "診斷" in task:
            enable_llm = params.get("enable_llm", True)
            return await self._run_diagnosis(params, enable_llm=enable_llm)

        if "anomaly" in task_lower or "異常" in task:
            return await self._detect_anomalies(params)

        if "investigate" in task_lower or "調查" in task:
            return await self._run_agentic_investigation(params)

        await self.update_progress(0.5, f"分析中：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"故障分析完成：{task}")

    async def _run_diagnosis(
        self, params: dict[str, Any], *, enable_llm: bool = True
    ) -> TaskResult:
        """執行完整故障診斷流程（統計分析 + ML 分類 + LLM 推理）。

        Args:
            params: 任務參數，須包含 turbine_id。
            enable_llm: 是否啟用 LLM 深層推理（WindGuard 模式）。
        """
        turbine_id = params.get("turbine_id", "WT-01")
        await self.update_progress(0.05, f"載入 {turbine_id} 的 SCADA 與感測器資料")

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.features.domain_features.wind_features import (
                compute_operational_features,
                compute_power_curve_features,
                compute_temperature_features,
            )
            from src.models.evaluation.anomaly_analysis import generate_diagnosis_report

            loop = asyncio.get_event_loop()

            # 載入資料
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            await self.update_progress(0.12, f"已載入 {len(df)} 筆記錄")

            # 清洗
            df_clean, quality = await loop.run_in_executor(None, lambda: clean_scada_data(df))
            await self.update_progress(0.22, "資料清洗完成")

            # 特徵工程
            df_feat = await loop.run_in_executor(
                None, lambda: compute_power_curve_features(df_clean)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_temperature_features(df_feat)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_operational_features(df_feat)
            )
            await self.update_progress(0.35, "特徵工程完成")

            # 統計異常偵測與健康評分
            report = await loop.run_in_executor(
                None, lambda: generate_diagnosis_report(df_feat, turbine_id)
            )
            await self.update_progress(0.48, "統計異常偵測完成")

            # ML 故障分類
            await self.update_progress(0.50, "訓練 ML 故障分類器...")
            ml_classification = await self._run_ml_classification(df_feat, loop)
            if ml_classification:
                report["ml_fault_classification"] = ml_classification
                await self.update_progress(0.62, "ML 故障分類完成")
            else:
                await self.update_progress(0.62, "ML 分類跳過（資料不足）")

            # NBM 異常偵測
            await self.update_progress(0.65, "訓練 NBM 功率曲線模型...")
            nbm_result = await self._run_nbm_analysis(df_clean, loop)
            if nbm_result:
                report["nbm_analysis"] = nbm_result
                await self.update_progress(0.75, "NBM 異常偵測完成")
            else:
                await self.update_progress(0.75, "NBM 分析跳過")

            # ── WindGuard LLM 推理（新增）──
            llm_result: dict[str, Any] | None = None
            if enable_llm:
                await self.update_progress(0.78, "啟動 WindGuard LLM 深層推理...")
                llm_result = await self._run_llm_reasoning(report, loop)
                if llm_result and llm_result.get("fault_type") != "parse_error":
                    report["windguard_llm_diagnosis"] = llm_result
                    fault_type = llm_result.get("fault_type_zh", "未判定")
                    severity = llm_result.get("severity", "未判定")
                    await self.update_progress(
                        0.92,
                        f"LLM 診斷：{fault_type}（嚴重度：{severity}）",
                    )
                else:
                    await self.update_progress(0.92, "LLM 推理跳過（API 不可用或解析失敗）")
            else:
                await self.update_progress(0.92, "LLM 推理已停用")

            health = report.get("health_score", 0)
            summary_parts = [f"{turbine_id} 故障診斷完成 — 健康分數 {health}/100"]
            if llm_result and llm_result.get("fault_type") not in (None, "parse_error"):
                summary_parts.append(
                    f"LLM 判定：{llm_result.get('fault_type_zh', '?')} "
                    f"({llm_result.get('severity', '?')})"
                )

            await self.update_progress(1.0, summary_parts[0])

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "health_score": health,
                    "report": report,
                    "quality_report": quality,
                    "llm_diagnosis": llm_result,
                },
                summary=" | ".join(summary_parts),
            )

        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"故障診斷失敗：{str(e)}"],
            )

    async def _run_ml_classification(
        self, df_feat: Any, loop: asyncio.AbstractEventLoop
    ) -> dict[str, Any] | None:
        """執行 ML 故障分類。"""
        try:
            from src.models.classification.fault_classifier import (
                FaultClassifier,
                generate_fault_labels,
            )

            labels = await loop.run_in_executor(None, lambda: generate_fault_labels(df_feat))
            clf = FaultClassifier()
            train_result = await loop.run_in_executor(None, lambda: clf.train(df_feat, labels))
            clf_result = await loop.run_in_executor(None, lambda: clf.classify(df_feat))

            return {
                "model_f1_macro": train_result.f1_macro,
                "fault_counts": clf_result.fault_counts,
                "fault_ratios": clf_result.fault_ratios,
                "severity_distribution": clf_result.severity_distribution,
                "top_faults": clf_result.top_faults[:10],
            }
        except Exception:
            return None

    async def _run_nbm_analysis(
        self, df_clean: Any, loop: asyncio.AbstractEventLoop
    ) -> dict[str, Any] | None:
        """執行 NBM 功率曲線異常偵測。"""
        try:
            from src.models.nbm.power_curve_nbm import PowerCurveNBM

            nbm = PowerCurveNBM()
            nbm_result = await loop.run_in_executor(None, lambda: nbm.train(df_clean))
            anomaly_result = await loop.run_in_executor(
                None, lambda: nbm.detect_anomalies(df_clean)
            )

            return {
                "model_r2": nbm_result.r2,
                "model_mae": nbm_result.mae,
                "anomaly_count": anomaly_result.anomaly_count,
                "anomaly_ratio": anomaly_result.anomaly_ratio,
                "threshold": anomaly_result.threshold,
                "top_anomalies": anomaly_result.anomalies[:10],
            }
        except Exception:
            return None

    async def _run_llm_reasoning(
        self, report: dict[str, Any], loop: asyncio.AbstractEventLoop
    ) -> dict[str, Any] | None:
        """執行 WindGuard LLM 深層推理。"""
        try:
            from src.services.windguard_diagnosis import WindGuardDiagnosis

            windguard = WindGuardDiagnosis()

            # 嘗試從 RAG 取得相關案例
            rag_contexts: list[dict[str, Any]] | None = None
            try:
                from src.services.rag_service import RAGService

                rag = RAGService()
                turbine_id = report.get("turbine_id", "")
                warnings = report.get("warnings", [])
                query = f"風機 {turbine_id} 故障診斷 {' '.join(warnings[:3])}"
                results = rag.search(query, n_results=3)
                if results:
                    rag_contexts = [
                        {
                            "content": r.content,
                            "source": r.metadata.get("source", ""),
                            "relevance": r.relevance_score,
                        }
                        for r in results
                    ]
            except Exception:
                pass  # RAG 不可用時靜默跳過

            result = await loop.run_in_executor(
                None,
                lambda: windguard.reason_about_diagnosis(report, rag_contexts),
            )
            return result
        except Exception as e:
            self._logger.warning(f"LLM 推理失敗：{e}")
            return None

    async def _run_fleet_scan(self, params: dict[str, Any]) -> TaskResult:
        """執行風場級別批次掃描。"""
        turbine_ids = params.get("turbine_ids", [])
        enable_llm = params.get("enable_llm", True)

        if not turbine_ids:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=["未指定風機 ID 列表（turbine_ids）"],
            )

        await self.update_progress(0.05, f"啟動風場掃描：{len(turbine_ids)} 台風機")

        try:
            from src.services.fleet_scanner import FleetScanner

            scanner = FleetScanner()
            loop = asyncio.get_event_loop()

            async def _progress_cb(pct: float, msg: str) -> None:
                # 掃描佔 0.05~0.80，LLM 佔 0.80~0.95
                adjusted = 0.05 + pct * 0.75
                await self.update_progress(adjusted, msg)

            def _sync_progress(pct: float, msg: str) -> None:
                asyncio.run_coroutine_threadsafe(_progress_cb(pct, msg), loop)

            if enable_llm:
                result = await loop.run_in_executor(
                    None,
                    lambda: scanner.scan_and_reason(turbine_ids, progress_cb=_sync_progress),
                )
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: scanner.scan_fleet(turbine_ids, progress_cb=_sync_progress),
                )

            summary = result.get("fleet_summary", {})
            await self.update_progress(
                1.0,
                f"風場掃描完成 — {summary.get('scanned_ok', 0)} 台成功, "
                f"平均健康 {summary.get('avg_health_score', 'N/A')}/100",
            )

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data=result,
                summary=(
                    f"風場掃描完成：{summary.get('scanned_ok', 0)}/{summary.get('total_turbines', 0)} 台, "
                    f"Critical={summary.get('critical_count', 0)}, "
                    f"High={summary.get('high_count', 0)}"
                ),
            )

        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"風場掃描失敗：{str(e)}"],
            )

    async def _run_agentic_investigation(self, params: dict[str, Any]) -> TaskResult:
        """執行 LLM 自主調查模式（Agentic Function Calling）。"""
        task_description = params.get("task_description", "")
        turbine_ids = params.get("turbine_ids", [])

        if not task_description:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=["未提供調查任務描述（task_description）"],
            )

        await self.update_progress(0.1, "啟動 LLM 自主調查模式...")

        try:
            from src.services.windguard_diagnosis import WindGuardDiagnosis

            windguard = WindGuardDiagnosis()
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                None,
                lambda: windguard.agentic_investigate(
                    task_description=task_description,
                    available_turbine_ids=turbine_ids,
                ),
            )

            rounds = result.get("investigation_rounds", 0)
            tool_calls = result.get("tool_calls", [])
            await self.update_progress(
                1.0,
                f"調查完成 — {rounds} 輪, {len(tool_calls)} 次工具呼叫",
            )

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data=result,
                summary=(
                    f"Agentic 調查完成：{rounds} 輪對話, "
                    f"{len(tool_calls)} 次工具呼叫"
                ),
            )

        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"Agentic 調查失敗：{str(e)}"],
            )

    async def _detect_anomalies(self, params: dict[str, Any]) -> TaskResult:
        """執行異常偵測。"""
        turbine_id = params.get("turbine_id", "WT-01")
        await self.update_progress(0.3, "載入並分析資料")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.models.evaluation.anomaly_analysis import generate_diagnosis_report

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))

            await self.update_progress(0.6, "執行異常偵測模型")

            report = await loop.run_in_executor(
                None, lambda: generate_diagnosis_report(df, turbine_id)
            )

            anomalies = report.get("temperature_anomalies", [])
            await self.update_progress(1.0, f"偵測到 {len(anomalies)} 個異常事件")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={"anomaly_count": len(anomalies), "anomalies": anomalies},
                summary=f"異常偵測完成：{len(anomalies)} 個異常事件",
            )
        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"異常偵測失敗：{str(e)}"],
            )
