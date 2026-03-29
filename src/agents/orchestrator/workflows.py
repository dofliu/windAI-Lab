"""WindAI Lab 工作流程定義。

定義所有可執行的工作流程（slash commands），每個流程由多個步驟組成。
每個步驟指定參與的代理、執行方式和預期產出。

設計原則：
1. 每個 workflow 的 Step 1 必須是「總監確認/分派」
2. 每個 workflow 的最後 Step 必須是「總監審核」
3. 每個 WorkflowStep 同時攜帶 task_template（真實）+ sub_messages（模擬 fallback）
"""

from src.agents.orchestrator.engine import StepType, Workflow, WorkflowStep

# ── 共用的總監 Step 工廠 ────────────────────────────────────────


def _director_dispatch(task_name: str, turbine_id: str = "") -> WorkflowStep:
    """建立總監分派步驟（所有 workflow 的 Step 1）。"""
    target = f" — {turbine_id}" if turbine_id else ""
    return WorkflowStep(
        name="總監分派",
        agent_ids=["project-director"],
        description=f"確認任務範圍並分派：{task_name}{target}",
        duration=2.0,
        task_template=f"分派任務：{task_name} {{turbine_id}}",
        sub_messages=[
            f"📋 任務確認：{task_name}{target}",
            "已分派至對應代理，開始執行",
        ],
        progress_messages={50: "確認任務範圍與參數中..."},
    )


def _director_review(task_name: str) -> WorkflowStep:
    """建立總監審核步驟（所有 workflow 的最後 Step）。"""
    return WorkflowStep(
        name="總監審核",
        agent_ids=["project-director"],
        description=f"審核 {task_name} 結果並核准",
        duration=2.0,
        task_template=f"審核 {task_name} 結果",
        sub_messages=[
            f"✅ {task_name} 已審核通過",
            "結果已歸檔，建議事項已記錄",
        ],
        progress_messages={50: "審核分析品質與結果..."},
    )


# ═══════════════════════════════════════════════════════════════
# 故障診斷
# ═══════════════════════════════════════════════════════════════


def create_diagnose_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /diagnose 故障診斷工作流程。"""
    return Workflow(
        id="diagnose",
        name=f"風機故障診斷 — {turbine_id}",
        description=f"對 {turbine_id} 風機執行全面故障診斷分析",
        parameters={"turbine_id": turbine_id},
        steps=[
            _director_dispatch("故障診斷", turbine_id),
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
            WorkflowStep(
                name="功率曲線 + RUL",
                agent_ids=["power-curve-expert", "predictive-modeler"],
                description=f"平行執行 {turbine_id} 的 NBM 建模與 RUL 預測",
                duration=4.0,
                step_type=StepType.PARALLEL,
                task_template="NBM {turbine_id}",
                sub_messages=[
                    "NBM 功率曲線建模完成",
                    "RUL 預測完成",
                ],
                progress_messages={
                    30: "訓練 NBM / RUL 模型中...",
                    70: "計算退化趨勢...",
                },
            ),
            WorkflowStep(
                name="文獻佐證",
                agent_ids=["literature-reviewer"],
                description="搜索相關故障案例與維護文獻",
                duration=3.0,
                task_template="搜索相關故障案例文獻",
                sub_messages=[
                    "找到相關軸承故障案例文獻",
                    "參考文獻建議：油液分析可確認磨損程度",
                ],
                progress_messages={
                    40: "搜索 IEEE / Wind Energy 期刊...",
                    80: "整理文獻摘要...",
                },
            ),
            WorkflowStep(
                name="生成診斷報告",
                agent_ids=["paper-writer"],
                description="彙整所有分析結果，生成故障診斷報告",
                duration=3.0,
                task_template="生成診斷報告",
                sub_messages=[
                    "診斷報告已生成",
                    "包含：異常摘要、故障分類、RUL 預測、維護建議",
                ],
                progress_messages={
                    30: "整理分析結果...",
                    60: "撰寫報告...",
                    90: "排版校對...",
                },
            ),
            _director_review("故障診斷"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# 月度健康評估（新）
# ═══════════════════════════════════════════════════════════════


def create_monthly_review_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /monthly-review 月度健康評估工作流程。

    整合三種月度資料：
    1. SCADA 運轉資料 → 功率曲線偏差 + 故障分類
    2. 警報事件清單 → 警報頻率/嚴重度趨勢
    3. 運維月報 PDF → RAG 嵌入 + 歷史案例比對
    """
    return Workflow(
        id="monthly-review",
        name=f"月度健康評估 — {turbine_id}",
        description=f"對 {turbine_id} 執行月度運轉資料分析、警報評估與健康報告",
        parameters={"turbine_id": turbine_id},
        steps=[
            _director_dispatch("月度健康評估", turbine_id),
            # ── 資料載入 + 清洗 ──
            WorkflowStep(
                name="載入月度 SCADA 資料",
                agent_ids=["scada-processor"],
                description=f"載入 {turbine_id} 本月運轉資料並清洗",
                duration=3.0,
                task_template="clean {turbine_id}",
                sub_messages=[
                    f"已載入 {turbine_id} 本月 SCADA 資料",
                    "資料清洗完成：去重、插值、異常過濾",
                ],
                progress_messages={
                    30: "載入 SCADA 資料...",
                    70: "執行資料清洗...",
                },
            ),
            # ── 警報事件處理 ──
            WorkflowStep(
                name="警報事件分析",
                agent_ids=["quality-checker"],
                description=f"處理 {turbine_id} 本月警報事件清單",
                duration=3.0,
                task_template="alarm {turbine_id}",
                sub_messages=[
                    "警報事件已轉為時間序列特徵",
                    "警報頻率與嚴重度統計完成",
                ],
                progress_messages={
                    30: "解析警報事件清單...",
                    60: "計算警報頻率統計...",
                    90: "生成 MTBF 指標...",
                },
            ),
            # ── 平行：故障分析 + NBM 健康分數 ──
            WorkflowStep(
                name="故障分析 + 健康評分",
                agent_ids=["fault-diagnostician", "power-curve-expert"],
                description=f"平行執行 {turbine_id} 故障分類與 NBM 健康評分",
                duration=5.0,
                step_type=StepType.PARALLEL,
                task_template="diagnose {turbine_id}",
                collaborator_ids=["quality-checker"],
                sub_messages=[
                    "功率曲線偏差分析完成",
                    "故障分類結果產出",
                    "NBM 健康分數已計算",
                ],
                progress_messages={
                    20: "執行功率曲線偏差分析...",
                    50: "ML 故障分類中...",
                    80: "計算 NBM 健康分數...",
                },
            ),
            # ── 運維月報 RAG 嵌入 + 案例比對 ──
            WorkflowStep(
                name="運維月報分析",
                agent_ids=["rag-architect"],
                description="嵌入運維月報 PDF 並搜索歷史相似案例",
                duration=3.0,
                task_template="搜索運維相關歷史案例",
                sub_messages=[
                    "運維月報已嵌入知識庫",
                    "找到相似歷史案例供參考",
                ],
                progress_messages={
                    40: "嵌入運維月報至向量資料庫...",
                    80: "搜索相似歷史案例...",
                },
            ),
            # ── RUL 更新 ──
            WorkflowStep(
                name="RUL 壽命預測更新",
                agent_ids=["predictive-modeler"],
                description=f"結合最新資料更新 {turbine_id} 的 RUL 預測",
                duration=4.0,
                task_template="predict RUL {turbine_id}",
                sub_messages=[
                    "RUL 預測已更新",
                    "退化趨勢已納入最新警報頻率",
                ],
                progress_messages={
                    30: "載入退化模型...",
                    60: "擬合最新退化曲線...",
                    90: "計算更新後的 RUL 區間...",
                },
            ),
            # ── 月度報告生成 ──
            WorkflowStep(
                name="生成月度健康報告",
                agent_ids=["paper-writer"],
                description="彙整所有月度分析結果，生成健康評估報告",
                duration=3.0,
                task_template="生成月度健康報告",
                sub_messages=[
                    "月度健康報告已生成",
                    "包含：運轉摘要、警報統計、健康分數、RUL、維護建議",
                ],
                progress_messages={
                    25: "整理運轉資料摘要...",
                    50: "撰寫警報分析與健康評分...",
                    75: "插入趨勢圖表...",
                    90: "撰寫維護建議...",
                },
            ),
            _director_review("月度健康評估"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# NBM / RUL 單項
# ═══════════════════════════════════════════════════════════════


def create_train_nbm_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /train-nbm NBM 功率曲線訓練工作流程。"""
    return Workflow(
        id="train-nbm",
        name=f"NBM 功率曲線訓練 — {turbine_id}",
        description=f"訓練 {turbine_id} 的 NBM 功率曲線模型",
        parameters={"turbine_id": turbine_id},
        steps=[
            _director_dispatch("NBM 訓練", turbine_id),
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
            _director_review("NBM 訓練"),
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
            _director_dispatch("RUL 預測", turbine_id),
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
            _director_review("RUL 預測"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# 文獻搜索
# ═══════════════════════════════════════════════════════════════


def create_lit_search_workflow(topic: str = "wind turbine fault diagnosis LLM") -> Workflow:
    """建立 /lit-search 文獻搜索工作流程。"""
    return Workflow(
        id="lit-search",
        name=f"文獻搜索 — {topic}",
        description=f"針對「{topic}」執行系統性文獻搜索",
        parameters={"topic": topic},
        steps=[
            WorkflowStep(
                name="總監分派",
                agent_ids=["project-director"],
                description=f"確認文獻搜索範圍：{topic}",
                duration=2.0,
                task_template="分派任務：文獻搜索 {topic}",
                task_parameters={"topic": topic},
                sub_messages=[f"📋 搜索主題確認：{topic}", "已分派至研究團隊"],
                progress_messages={50: "確認搜索策略..."},
            ),
            WorkflowStep(
                name="確認搜索策略",
                agent_ids=["research-lead"],
                description=f"規劃「{topic}」的搜索關鍵字與資料庫",
                duration=2.0,
                task_template="規劃文獻搜索策略：{topic}",
                task_parameters={"topic": topic},
                sub_messages=[
                    "搜索資料庫：arXiv, IEEE Xplore, Scopus",
                    "關鍵字組合已確認",
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
                    "arXiv 搜索完成",
                    "IEEE Xplore 搜索完成",
                    "篩選後保留高相關性論文",
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
                    "研究缺口分析完成",
                ],
            ),
            _director_review("文獻搜索"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# 資料操作
# ═══════════════════════════════════════════════════════════════


def create_data_load_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /data:load 資料載入工作流程。"""
    return Workflow(
        id="data-load",
        name=f"資料載入 — {turbine_id}",
        description=f"智慧載入 {turbine_id} 的 SCADA 資料並執行初步分析",
        parameters={"turbine_id": turbine_id},
        steps=[
            _director_dispatch("資料載入", turbine_id),
            WorkflowStep(
                name="智慧資料偵測",
                agent_ids=["scada-processor"],
                description=f"自動辨識 {turbine_id} 的檔案格式與欄位結構",
                duration=3.0,
                task_template="load {turbine_id}",
                sub_messages=["自動偵測欄位映射完成"],
                progress_messages={
                    30: "偵測檔案格式...",
                    70: "欄位辨識中...",
                },
            ),
            WorkflowStep(
                name="資料品質檢查",
                agent_ids=["quality-checker"],
                description="驗證資料完整性與異常值",
                duration=4.0,
                task_template="quality check {turbine_id}",
                sub_messages=["品質檢查完成"],
                progress_messages={
                    25: "檢查缺失值...",
                    50: "驗證範圍合理性...",
                    75: "偵測異常值...",
                },
            ),
            WorkflowStep(
                name="特徵探索",
                agent_ids=["feature-engineer", "scada-processor"],
                description="自動分析特徵重要度與相關性",
                duration=5.0,
                step_type=StepType.PARALLEL,
                task_template="feature exploration {turbine_id}",
                sub_messages=["特徵重要度排序完成", "發現高相關欄位對"],
                progress_messages={
                    30: "計算相關性矩陣...",
                    60: "分析特徵重要度...",
                },
            ),
            _director_review("資料載入"),
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
            _director_dispatch("資料清洗", turbine_id),
            WorkflowStep(
                name="載入原始資料",
                agent_ids=["scada-processor"],
                description="從資料源載入原始 SCADA 資料",
                duration=2.0,
                task_template="load {turbine_id}",
                sub_messages=["原始資料已載入"],
                progress_messages={50: f"載入 {turbine_id} 的資料..."},
            ),
            WorkflowStep(
                name="自動清洗處理",
                agent_ids=["quality-checker", "scada-processor"],
                description="執行去重、插值、異常值過濾",
                duration=6.0,
                step_type=StepType.PARALLEL,
                task_template="clean {turbine_id}",
                sub_messages=["移除重複時間戳記", "小間隙插值完成", "異常值已過濾"],
                progress_messages={
                    20: "去重...",
                    40: "插值...",
                    60: "異常值過濾...",
                    80: "產出品質報告...",
                },
            ),
            _director_review("資料清洗"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# AI / ML
# ═══════════════════════════════════════════════════════════════


def create_ai_train_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /ai:train 模型訓練工作流程。"""
    return Workflow(
        id="ai-train",
        name=f"ML 模型訓練 — {turbine_id}",
        description="端到端訓練 ML 模型：NBM 功率曲線、故障分類器、RUL 退化模型",
        parameters={"turbine_id": turbine_id},
        steps=[
            _director_dispatch("ML 模型訓練", turbine_id),
            WorkflowStep(
                name="資料準備",
                agent_ids=["scada-processor", "feature-engineer"],
                description="載入、清洗並計算訓練特徵",
                duration=5.0,
                step_type=StepType.PARALLEL,
                task_template="load {turbine_id}",
                sub_messages=["資料載入完成", "特徵工程完成"],
                progress_messages={
                    25: "載入原始資料...",
                    50: "資料清洗...",
                    75: "計算特徵...",
                },
            ),
            WorkflowStep(
                name="模型訓練（平行）",
                agent_ids=["fault-diagnostician", "predictive-modeler"],
                description="同時訓練 NBM + 故障分類器 + RUL",
                duration=8.0,
                step_type=StepType.PARALLEL,
                task_template="diagnose {turbine_id}",
                sub_messages=["NBM 訓練完成", "故障分類器訓練完成", "RUL 模型擬合完成"],
                progress_messages={
                    20: "NBM: Gradient Boosting...",
                    40: "故障分類器: Random Forest...",
                    60: "RUL: 退化曲線擬合...",
                    80: "計算評估指標...",
                },
            ),
            WorkflowStep(
                name="結果評估",
                agent_ids=["experiment-tracker"],
                description="記錄實驗結果、比較模型效能",
                duration=3.0,
                task_template="evaluate models",
                sub_messages=["模型評估完成", "已記錄至實驗追蹤系統"],
                progress_messages={50: "彙整評估指標..."},
            ),
            _director_review("ML 模型訓練"),
        ],
    )


def create_ai_evaluate_workflow(turbine_id: str = "WT-01") -> Workflow:
    """建立 /ai:evaluate 模型評估工作流程。"""
    return Workflow(
        id="ai-evaluate",
        name=f"模型效能評估 — {turbine_id}",
        description="評估已訓練模型的效能",
        parameters={"turbine_id": turbine_id},
        steps=[
            _director_dispatch("模型評估", turbine_id),
            WorkflowStep(
                name="載入訓練結果",
                agent_ids=["experiment-tracker"],
                description="從實驗追蹤系統取得最近的訓練結果",
                duration=2.0,
                task_template="load experiment results",
                sub_messages=["已載入最新模型"],
                progress_messages={50: "讀取模型與訓練紀錄..."},
            ),
            WorkflowStep(
                name="效能分析",
                agent_ids=["fault-diagnostician", "predictive-modeler"],
                description="殘差分析、混淆矩陣、校準曲線",
                duration=5.0,
                step_type=StepType.PARALLEL,
                task_template="evaluate {turbine_id}",
                sub_messages=["NBM 殘差分析完成", "故障分類精準度已產出", "RUL 誤差分析完成"],
                progress_messages={
                    30: "計算 NBM 殘差...",
                    60: "分析故障分類...",
                    90: "評估 RUL 可靠度...",
                },
            ),
            WorkflowStep(
                name="報告產出",
                agent_ids=["paper-writer"],
                description="彙整評估結果，產出效能報告",
                duration=2.0,
                task_template="生成評估報告",
                sub_messages=["效能評估報告已產出"],
                progress_messages={50: "撰寫評估報告..."},
            ),
            _director_review("模型評估"),
        ],
    )


# ── 工作流程參數萃取 ─────────────────────────────────────────


def extract_workflow_params(command_name: str, parameters: dict) -> dict:
    """從指令參數萃取 workflow factory 所需的 kwargs。"""
    if command_name in (
        "diagnose",
        "monthly-review",
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
    "monthly-review": create_monthly_review_workflow,
    "train-nbm": create_train_nbm_workflow,
    "predict-rul": create_predict_rul_workflow,
    "lit-search": create_lit_search_workflow,
    "data:load": create_data_load_workflow,
    "data:clean": create_data_clean_workflow,
    "ai:train": create_ai_train_workflow,
    "ai:evaluate": create_ai_evaluate_workflow,
}
