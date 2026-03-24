"""WindAI Lab 工作流程定義。

定義所有可執行的工作流程（slash commands），每個流程由多個步驟組成，
每個步驟指定參與的代理、執行方式和預期產出。
"""

from src.agents.orchestrator.engine import StepType, Workflow, WorkflowStep


def create_diagnose_workflow(turbine_id: str = "WT-07") -> Workflow:
    """建立 /diagnose 故障診斷工作流程。"""
    return Workflow(
        id="diagnose",
        name=f"風機故障診斷 — {turbine_id}",
        description=f"對 {turbine_id} 風機執行全面故障診斷分析",
        steps=[
            WorkflowStep(
                name="任務分派與確認",
                agent_ids=["project-director"],
                description=f"確認 {turbine_id} 風機資訊，規劃診斷範圍",
                duration=3.0,
                sub_messages=[
                    f"已確認 {turbine_id} 為 2MW 風機，位於彰化外海風場",
                    "診斷範圍：齒輪箱、主軸承、葉片、發電機",
                ],
                progress_messages={
                    30: f"正在查詢 {turbine_id} 基本資訊...",
                    70: "已取得風機規格與近期維護紀錄",
                },
            ),
            WorkflowStep(
                name="研究主管審核診斷方案",
                agent_ids=["research-lead"],
                description="審核診斷方法論與分析流程",
                duration=2.5,
                sub_messages=[
                    "診斷方案已審核通過",
                    "建議重點關注齒輪箱溫度趨勢與振動頻譜",
                ],
                progress_messages={
                    50: "正在審核診斷流程與方法論...",
                },
            ),
            WorkflowStep(
                name="平行資料擷取",
                agent_ids=["predictive-modeler", "fault-diagnostician"],
                description=f"擷取 {turbine_id} 的 SCADA 與感測器資料",
                duration=4.0,
                step_type=StepType.PARALLEL,
                sub_messages=[
                    "SCADA 資料擷取完成：過去 30 天，共 4,320 筆 10 分鐘均值",
                    "振動感測器資料擷取完成：齒輪箱加速度計 × 3 軸",
                ],
                progress_messages={
                    20: "連線至 SCADA 資料庫...",
                    50: "資料下載中 (2,160/4,320 筆)...",
                    80: "資料格式轉換與時間對齊中...",
                },
            ),
            WorkflowStep(
                name="AI 故障分析",
                agent_ids=["fault-diagnostician"],
                description="執行故障分類與異常偵測",
                duration=5.0,
                sub_messages=[
                    "異常偵測結果：齒輪箱油溫偏高 (78°C → 正常值 65°C)",
                    "故障分類結果：疑似齒輪箱軸承初期磨損 (信心度 87.3%)",
                    "Power Curve 偏差分析：低風速段效率下降 3.2%",
                ],
                progress_messages={
                    10: "載入預訓練故障分類模型...",
                    30: "執行 Normal Behavior Model 異常偵測...",
                    50: "分析振動頻譜特徵...",
                    70: "計算 BPFO/BPFI 軸承特徵頻率...",
                    90: "生成故障機率評估...",
                },
            ),
            WorkflowStep(
                name="預測性分析",
                agent_ids=["predictive-modeler"],
                description="預測剩餘使用壽命 (RUL)",
                duration=4.0,
                sub_messages=[
                    "齒輪箱軸承 RUL 預測：剩餘約 45 ± 12 天",
                    "建議在 30 天內安排預防性維護",
                    "退化趨勢：線性退化模型 R² = 0.91",
                ],
                progress_messages={
                    20: "載入 RUL 預測模型 (LSTM-based)...",
                    50: "計算退化趨勢指標...",
                    80: "執行蒙特卡羅模擬估算信賴區間...",
                },
            ),
            WorkflowStep(
                name="文獻佐證",
                agent_ids=["literature-reviewer"],
                description="搜索相關故障案例與維護文獻",
                duration=3.0,
                sub_messages=[
                    "找到 5 篇相關軸承故障案例文獻",
                    "參考文獻建議：油液分析可進一步確認磨損程度",
                ],
                progress_messages={
                    40: "搜索 IEEE / Wind Energy 期刊相關案例...",
                    80: "整理文獻摘要與建議措施...",
                },
            ),
            WorkflowStep(
                name="生成診斷報告",
                agent_ids=["paper-writer"],
                description="彙整所有分析結果，生成故障診斷報告",
                duration=3.5,
                sub_messages=[
                    "診斷報告已生成，共 8 頁",
                    "包含：異常摘要、故障分類、RUL 預測、維護建議、參考文獻",
                ],
                progress_messages={
                    20: "整理異常偵測結果摘要...",
                    40: "撰寫故障分類分析段落...",
                    60: "插入趨勢圖表與頻譜分析圖...",
                    80: "撰寫維護建議與優先順序...",
                },
            ),
            WorkflowStep(
                name="最終審核",
                agent_ids=["research-lead", "project-director"],
                description="研究主管與專案總監最終審核",
                duration=2.0,
                step_type=StepType.SEQUENTIAL,
                sub_messages=[
                    "研究主管：分析方法論合理，結果可信",
                    "專案總監：已核准診斷報告，建議排入下週維護排程",
                    f"📋 {turbine_id} 故障診斷完成 — 建議 30 天內進行齒輪箱軸承檢修",
                ],
                progress_messages={
                    50: "研究主管審核分析品質...",
                },
            ),
        ],
    )


def create_lit_search_workflow(topic: str = "wind turbine fault diagnosis LLM") -> Workflow:
    """建立 /lit-search 文獻搜索工作流程。"""
    return Workflow(
        id="lit-search",
        name=f"文獻搜索 — {topic}",
        description=f"針對「{topic}」執行系統性文獻搜索",
        steps=[
            WorkflowStep(
                name="確認搜索策略",
                agent_ids=["research-lead"],
                description=f"規劃「{topic}」的搜索關鍵字與資料庫",
                duration=2.0,
                sub_messages=[
                    f"搜索主題：{topic}",
                    "搜索資料庫：arXiv, IEEE Xplore, Scopus",
                    "關鍵字組合已確認：3 組主要搜索式",
                ],
            ),
            WorkflowStep(
                name="執行文獻搜索",
                agent_ids=["literature-reviewer"],
                description="搜索並篩選相關論文",
                duration=5.0,
                sub_messages=[
                    "arXiv 搜索完成：找到 23 篇候選論文",
                    "IEEE Xplore 搜索完成：找到 15 篇候選論文",
                    "經篩選後保留 18 篇高相關性論文",
                ],
                progress_messages={
                    20: "搜索 arXiv 資料庫...",
                    40: "搜索 IEEE Xplore...",
                    60: "搜索 Scopus...",
                    80: "依相關性篩選與排序...",
                },
            ),
            WorkflowStep(
                name="整理文獻摘要",
                agent_ids=["literature-reviewer", "paper-writer"],
                description="整理論文摘要與比較分析",
                duration=4.0,
                step_type=StepType.PARALLEL,
                sub_messages=[
                    "文獻摘要表已建立（18 篇）",
                    "研究缺口分析：3 個潛在研究方向已標記",
                    "文獻回顧報告已存檔至 docs/literature/",
                ],
            ),
        ],
    )


# Import real workflow

# 可用的工作流程註冊表
AVAILABLE_WORKFLOWS = {
    "diagnose": create_diagnose_workflow,
    "lit-search": create_lit_search_workflow,
    "diagnose-real": None,  # Special handler — see main.py (uses run_real_diagnose)
}
