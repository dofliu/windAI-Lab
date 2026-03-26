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


def create_data_load_workflow(turbine_id: str = "Kelmarsh_1") -> Workflow:
    """建立 /data:load 資料載入工作流程。"""
    return Workflow(
        id="data-load",
        name=f"資料載入 — {turbine_id}",
        description=f"智慧載入 {turbine_id} 的 SCADA 資料並執行初步分析",
        steps=[
            WorkflowStep(
                name="智慧資料偵測",
                agent_ids=["scada-processor"],
                description=f"自動辨識 {turbine_id} 的檔案格式與欄位結構",
                duration=3.0,
                sub_messages=[
                    f"掃描資料目錄，搜尋 {turbine_id} 相關檔案...",
                    "自動偵測欄位映射完成",
                ],
                progress_messages={
                    30: "正在偵測檔案格式（CSV/Parquet/ZIP）...",
                    70: "欄位辨識中：風速、功率、溫度...",
                },
            ),
            WorkflowStep(
                name="資料品質檢查",
                agent_ids=["quality-checker"],
                description="驗證資料完整性、缺失值與異常值分析",
                duration=4.0,
                sub_messages=[
                    "品質檢查完成",
                    "產出資料品質報告",
                ],
                progress_messages={
                    25: "檢查缺失值比例...",
                    50: "驗證資料範圍合理性...",
                    75: "偵測異常值...",
                },
            ),
            WorkflowStep(
                name="特徵自動探索",
                agent_ids=["feature-engineer", "scada-processor"],
                description="自動分析所有欄位的特徵重要度、相關性、分佈",
                duration=5.0,
                step_type=StepType.PARALLEL,
                sub_messages=[
                    "特徵重要度排序完成",
                    "發現高相關欄位對",
                ],
                progress_messages={
                    30: "計算欄位間相關性矩陣...",
                    60: "分析特徵重要度...",
                    90: "產出分析建議...",
                },
            ),
        ],
    )


def create_data_clean_workflow(turbine_id: str = "Kelmarsh_1") -> Workflow:
    """建立 /data:clean 資料清洗工作流程。"""
    return Workflow(
        id="data-clean",
        name=f"資料清洗 — {turbine_id}",
        description=f"對 {turbine_id} 執行自動資料清洗與異常過濾",
        steps=[
            WorkflowStep(
                name="載入原始資料",
                agent_ids=["scada-processor"],
                description="從資料源載入原始 SCADA 資料",
                duration=2.0,
                sub_messages=["原始資料已載入"],
                progress_messages={50: f"正在載入 {turbine_id} 的資料..."},
            ),
            WorkflowStep(
                name="自動清洗處理",
                agent_ids=["quality-checker", "scada-processor"],
                description="執行去重、插值、異常值過濾",
                duration=6.0,
                step_type=StepType.PARALLEL,
                sub_messages=[
                    "移除重複時間戳記",
                    "小間隙插值完成",
                    "異常值已標記過濾",
                ],
                progress_messages={
                    20: "移除重複時間戳記...",
                    40: "處理缺失值（線性插值）...",
                    60: "過濾異常值（負功率、超額定等）...",
                    80: "產出品質報告...",
                },
            ),
            WorkflowStep(
                name="驗證與報告",
                agent_ids=["quality-checker"],
                description="驗證清洗結果並產出品質報告",
                duration=2.0,
                sub_messages=["清洗完成，品質報告已產出"],
                progress_messages={50: "驗證清洗後資料品質..."},
            ),
        ],
    )


def create_ai_train_workflow(turbine_id: str = "Kelmarsh_1") -> Workflow:
    """建立 /ai:train 模型訓練工作流程。"""
    return Workflow(
        id="ai-train",
        name=f"ML 模型訓練 — {turbine_id}",
        description="端到端訓練三個 ML 模型：NBM 功率曲線、故障分類器、RUL 退化模型",
        steps=[
            WorkflowStep(
                name="資料準備",
                agent_ids=["scada-processor", "feature-engineer"],
                description="載入、清洗並計算訓練特徵",
                duration=5.0,
                step_type=StepType.PARALLEL,
                sub_messages=[
                    f"正在載入 {turbine_id} SCADA 資料...",
                    "特徵工程：功率曲線特徵、溫度特徵、運營特徵",
                ],
                progress_messages={
                    25: "載入原始資料...",
                    50: "執行資料清洗...",
                    75: "計算特徵...",
                },
            ),
            WorkflowStep(
                name="模型訓練（平行）",
                agent_ids=["fault-diagnostician", "predictive-modeler", "anomaly-detector"],
                description="同時訓練 NBM、故障分類器、RUL 退化模型",
                duration=8.0,
                step_type=StepType.PARALLEL,
                sub_messages=[
                    "NBM 功率曲線模型訓練中...",
                    "故障分類器訓練中...",
                    "RUL 退化模型擬合中...",
                ],
                progress_messages={
                    20: "NBM: Gradient Boosting 訓練中...",
                    40: "故障分類器: Random Forest 訓練中...",
                    60: "RUL: 退化曲線擬合中...",
                    80: "計算評估指標...",
                },
            ),
            WorkflowStep(
                name="結果評估",
                agent_ids=["experiment-tracker"],
                description="記錄實驗結果、比較模型效能",
                duration=3.0,
                sub_messages=[
                    "所有模型評估完成",
                    "已記錄至實驗追蹤系統",
                ],
                progress_messages={
                    50: "彙整三個模型的評估指標...",
                },
            ),
        ],
    )


def create_ai_evaluate_workflow(turbine_id: str = "Kelmarsh_1") -> Workflow:
    """建立 /ai:evaluate 模型評估工作流程。"""
    return Workflow(
        id="ai-evaluate",
        name=f"模型效能評估 — {turbine_id}",
        description="評估已訓練模型的效能，包含交叉驗證、殘差分析、泛化測試",
        steps=[
            WorkflowStep(
                name="載入訓練結果",
                agent_ids=["experiment-tracker"],
                description="從實驗追蹤系統取得最近的訓練結果",
                duration=2.0,
                sub_messages=["已載入最新模型"],
                progress_messages={50: "正在讀取模型與訓練紀錄..."},
            ),
            WorkflowStep(
                name="效能分析",
                agent_ids=["fault-diagnostician", "predictive-modeler"],
                description="執行殘差分析、混淆矩陣、校準曲線",
                duration=5.0,
                step_type=StepType.PARALLEL,
                sub_messages=[
                    "NBM 殘差分析完成",
                    "故障分類器混淆矩陣已產出",
                    "RUL 預測誤差分析完成",
                ],
                progress_messages={
                    30: "計算 NBM 殘差分佈...",
                    60: "分析故障分類精準度...",
                    90: "評估 RUL 預測可靠度...",
                },
            ),
            WorkflowStep(
                name="報告產出",
                agent_ids=["report-generator"],
                description="彙整所有評估結果，產出效能報告",
                duration=2.0,
                sub_messages=["效能評估報告已產出"],
                progress_messages={50: "撰寫評估報告..."},
            ),
        ],
    )


# 可用的工作流程註冊表
AVAILABLE_WORKFLOWS = {
    "diagnose": create_diagnose_workflow,
    "lit-search": create_lit_search_workflow,
    "diagnose-real": None,  # Special handler — see main.py (uses run_real_diagnose)
    "data:load": create_data_load_workflow,
    "data:clean": create_data_clean_workflow,
    "ai:train": create_ai_train_workflow,
    "ai:evaluate": create_ai_evaluate_workflow,
}
