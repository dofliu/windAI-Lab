"""WindAI Lab 工作流程定義。

定義所有可執行的工作流程（slash commands），每個流程由多個步驟組成，
每個步驟指定參與的代理、執行方式和預期產出。

每個 WorkflowStep 同時攜帶：
- task_template + task_parameters → 給真實代理的執行指令
- sub_messages + progress_messages + duration → 給模擬 fallback 的動畫設定

引擎會自動判斷代理是否有實例，有則走真實路徑，無則播放動畫。
"""

from src.agents.orchestrator.engine import StepType, Workflow, WorkflowStep


def create_diagnose_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /diagnose 故障診斷工作流程。

    真實模式：觸發 fault-diagnostician 的完整 skill pipeline
    （scada_ingestion → turbine_profiler → scada_cleaning →
      domain_feature_extraction → fault_classification → nbm_training），
    再由 power-curve-expert 和 predictive-modeler 平行執行 NBM + RUL。

    模擬模式：依 sub_messages/progress_messages 播放動畫。
    """
    return Workflow(
        id="diagnose",
        name=f"風機故障診斷 — {turbine_id}",
        description=f"對 {turbine_id} 風機執行全面故障診斷分析",
        parameters={"turbine_id": turbine_id},
        steps=[
            # ── Step 1: 總監確認任務 ──
            WorkflowStep(
                name="任務分派與確認",
                agent_ids=["project-director"],
                description=f"確認 {turbine_id} 風機資訊，規劃診斷範圍",
                duration=3.0,
                task_template="確認 {turbine_id} 風機資訊並分派故障診斷任務",
                sub_messages=[
                    f"已確認 {turbine_id} 風機基本資訊",
                    "診斷範圍：齒輪箱、主軸承、葉片、發電機",
                ],
                progress_messages={
                    30: f"正在查詢 {turbine_id} 基本資訊...",
                    70: "已取得風機規格與近期維護紀錄",
                },
            ),
            # ── Step 2: 故障診斷師執行完整管線 ──
            WorkflowStep(
                name="AI 故障分析",
                agent_ids=["fault-diagnostician"],
                description=f"對 {turbine_id} 執行故障分類與異常偵測",
                duration=5.0,
                task_template="diagnose {turbine_id}",
                collaborator_ids=["predictive-modeler", "power-curve-expert"],
                sub_messages=[
                    "異常偵測結果：齒輪箱油溫偏高",
                    "故障分類結果：疑似齒輪箱軸承初期磨損",
                    "Power Curve 偏差分析完成",
                ],
                progress_messages={
                    10: "載入預訓練故障分類模型...",
                    30: "執行 Normal Behavior Model 異常偵測...",
                    50: "分析振動頻譜特徵...",
                    70: "計算 BPFO/BPFI 軸承特徵頻率...",
                    90: "生成故障機率評估...",
                },
            ),
            # ── Step 3: NBM + RUL 平行執行 ──
            WorkflowStep(
                name="功率曲線建模 + RUL 預測",
                agent_ids=["power-curve-expert", "predictive-modeler"],
                description=f"平行執行 {turbine_id} 的 NBM 建模與 RUL 預測",
                duration=4.0,
                step_type=StepType.PARALLEL,
                task_template="NBM {turbine_id}",
                sub_messages=[
                    "NBM 功率曲線建模完成",
                    f"RUL 預測完成：{turbine_id} 剩餘壽命估算已產出",
                ],
                progress_messages={
                    20: "載入 NBM / RUL 預測模型...",
                    50: "計算退化趨勢指標...",
                    80: "執行蒙特卡羅模擬估算信賴區間...",
                },
            ),
            # ── Step 4: 文獻佐證 ──
            WorkflowStep(
                name="文獻佐證",
                agent_ids=["literature-reviewer"],
                description="搜索相關故障案例與維護文獻",
                duration=3.0,
                task_template="搜索相關故障案例文獻",
                sub_messages=[
                    "找到相關軸承故障案例文獻",
                    "參考文獻建議：油液分析可進一步確認磨損程度",
                ],
                progress_messages={
                    40: "搜索 IEEE / Wind Energy 期刊相關案例...",
                    80: "整理文獻摘要與建議措施...",
                },
            ),
            # ── Step 5: 報告 ──
            WorkflowStep(
                name="生成診斷報告",
                agent_ids=["paper-writer"],
                description="彙整所有分析結果，生成故障診斷報告",
                duration=3.5,
                task_template="生成診斷報告",
                sub_messages=[
                    "診斷報告已生成",
                    "包含：異常摘要、故障分類、RUL 預測、維護建議、參考文獻",
                ],
                progress_messages={
                    20: "整理異常偵測結果摘要...",
                    40: "撰寫故障分類分析段落...",
                    60: "插入趨勢圖表與頻譜分析圖...",
                    80: "撰寫維護建議與優先順序...",
                },
            ),
            # ── Step 6: 最終審核 ──
            WorkflowStep(
                name="最終審核",
                agent_ids=["research-lead", "project-director"],
                description="研究主管與專案總監最終審核",
                duration=2.0,
                step_type=StepType.SEQUENTIAL,
                task_template="審核診斷報告",
                sub_messages=[
                    "研究主管：分析方法論合理，結果可信",
                    "專案總監：已核准診斷報告",
                    f"📋 {turbine_id} 故障診斷完成",
                ],
                progress_messages={
                    50: "研究主管審核分析品質...",
                },
            ),
        ],
    )


def create_train_nbm_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /train-nbm NBM 功率曲線訓練工作流程。"""
    return Workflow(
        id="train-nbm",
        name=f"NBM 功率曲線訓練 — {turbine_id}",
        description=f"訓練 {turbine_id} 的 NBM 功率曲線模型",
        parameters={"turbine_id": turbine_id},
        steps=[
            WorkflowStep(
                name="NBM 功率曲線訓練",
                agent_ids=["power-curve-expert"],
                description=f"訓練 {turbine_id} 的 NBM 功率曲線模型",
                duration=5.0,
                task_template="NBM {turbine_id}",
                sub_messages=["NBM 模型訓練完成"],
                progress_messages={
                    30: "載入 SCADA 資料...",
                    60: "訓練 Gradient Boosting 模型中...",
                    90: "計算評估指標...",
                },
            ),
        ],
    )


def create_predict_rul_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /predict-rul RUL 壽命預測工作流程。"""
    return Workflow(
        id="predict-rul",
        name=f"RUL 壽命預測 — {turbine_id}",
        description=f"預測 {turbine_id} 風機的剩餘使用壽命",
        parameters={"turbine_id": turbine_id},
        steps=[
            WorkflowStep(
                name="RUL 壽命預測",
                agent_ids=["predictive-modeler"],
                description=f"預測 {turbine_id} 的剩餘使用壽命",
                duration=5.0,
                task_template="predict RUL {turbine_id}",
                sub_messages=["RUL 預測完成"],
                progress_messages={
                    30: "載入 SCADA 資料與特徵...",
                    60: "執行退化曲線擬合...",
                    90: "計算 RUL 估算與信賴區間...",
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
                task_template="規劃文獻搜索策略：{topic}",
                task_parameters={"topic": topic},
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
                task_template="搜索相關文獻：{topic}",
                task_parameters={"topic": topic},
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
                task_template="整理文獻摘要",
                sub_messages=[
                    "文獻摘要表已建立",
                    "研究缺口分析：潛在研究方向已標記",
                    "文獻回顧報告已存檔至 docs/literature/",
                ],
            ),
        ],
    )


def create_data_load_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /data:load 資料載入工作流程。"""
    return Workflow(
        id="data-load",
        name=f"資料載入 — {turbine_id}",
        description=f"智慧載入 {turbine_id} 的 SCADA 資料並執行初步分析",
        parameters={"turbine_id": turbine_id},
        steps=[
            WorkflowStep(
                name="智慧資料偵測",
                agent_ids=["scada-processor"],
                description=f"自動辨識 {turbine_id} 的檔案格式與欄位結構",
                duration=3.0,
                task_template="load {turbine_id}",
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
                task_template="quality check {turbine_id}",
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
                task_template="feature exploration {turbine_id}",
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


def create_data_clean_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /data:clean 資料清洗工作流程。"""
    return Workflow(
        id="data-clean",
        name=f"資料清洗 — {turbine_id}",
        description=f"對 {turbine_id} 執行自動資料清洗與異常過濾",
        parameters={"turbine_id": turbine_id},
        steps=[
            WorkflowStep(
                name="載入原始資料",
                agent_ids=["scada-processor"],
                description="從資料源載入原始 SCADA 資料",
                duration=2.0,
                task_template="load {turbine_id}",
                sub_messages=["原始資料已載入"],
                progress_messages={50: f"正在載入 {turbine_id} 的資料..."},
            ),
            WorkflowStep(
                name="自動清洗處理",
                agent_ids=["quality-checker", "scada-processor"],
                description="執行去重、插值、異常值過濾",
                duration=6.0,
                step_type=StepType.PARALLEL,
                task_template="clean {turbine_id}",
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
                task_template="validate {turbine_id}",
                sub_messages=["清洗完成，品質報告已產出"],
                progress_messages={50: "驗證清洗後資料品質..."},
            ),
        ],
    )


def create_ai_train_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /ai:train 模型訓練工作流程。"""
    return Workflow(
        id="ai-train",
        name=f"ML 模型訓練 — {turbine_id}",
        description="端到端訓練三個 ML 模型：NBM 功率曲線、故障分類器、RUL 退化模型",
        parameters={"turbine_id": turbine_id},
        steps=[
            WorkflowStep(
                name="資料準備",
                agent_ids=["scada-processor", "feature-engineer"],
                description="載入、清洗並計算訓練特徵",
                duration=5.0,
                step_type=StepType.PARALLEL,
                task_template="load {turbine_id}",
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
                agent_ids=["fault-diagnostician", "predictive-modeler"],
                description="同時訓練 NBM + 故障分類器 + RUL 退化模型",
                duration=8.0,
                step_type=StepType.PARALLEL,
                task_template="diagnose {turbine_id}",
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
                task_template="evaluate models",
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


def create_ai_evaluate_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /ai:evaluate 模型評估工作流程。"""
    return Workflow(
        id="ai-evaluate",
        name=f"模型效能評估 — {turbine_id}",
        description="評估已訓練模型的效能，包含交叉驗證、殘差分析、泛化測試",
        parameters={"turbine_id": turbine_id},
        steps=[
            WorkflowStep(
                name="載入訓練結果",
                agent_ids=["experiment-tracker"],
                description="從實驗追蹤系統取得最近的訓練結果",
                duration=2.0,
                task_template="load experiment results",
                sub_messages=["已載入最新模型"],
                progress_messages={50: "正在讀取模型與訓練紀錄..."},
            ),
            WorkflowStep(
                name="效能分析",
                agent_ids=["fault-diagnostician", "predictive-modeler"],
                description="執行殘差分析、混淆矩陣、校準曲線",
                duration=5.0,
                step_type=StepType.PARALLEL,
                task_template="evaluate {turbine_id}",
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
                task_template="generate evaluation report",
                sub_messages=["效能評估報告已產出"],
                progress_messages={50: "撰寫評估報告..."},
            ),
        ],
    )


# ── 工作流程參數萃取 ─────────────────────────────────────────


def extract_workflow_params(command_name: str, parameters: dict) -> dict:
    """從指令參數萃取 workflow factory 所需的 kwargs。"""
    if command_name in (
        "diagnose",
        "train-nbm",
        "predict-rul",
        "data:load",
        "data:clean",
        "ai:train",
        "ai:evaluate",
    ):
        return {"turbine_id": parameters.get("turbine_id", "WT-01")}
    elif command_name == "lit-search":
        return {"topic": parameters.get("topic", "wind turbine fault diagnosis")}
    return {}


# ── 可用的工作流程註冊表 ─────────────────────────────────────

AVAILABLE_WORKFLOWS: dict[str, callable] = {
    "diagnose": create_diagnose_workflow,
    "train-nbm": create_train_nbm_workflow,
    "predict-rul": create_predict_rul_workflow,
    "lit-search": create_lit_search_workflow,
    "data:load": create_data_load_workflow,
    "data:clean": create_data_clean_workflow,
    "ai:train": create_ai_train_workflow,
    "ai:evaluate": create_ai_evaluate_workflow,
}
