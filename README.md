# WindAI Lab — 風力發電 AI 研究協作系統

多代理協作平台，結合虛擬辦公室介面與真實 SCADA 資料分析，專為風力發電研究設計。

## 快速啟動

```bash
# 1. 後端
cd D:\Dropbox\Project_CodingSimulation\researchTopic\windAILab
pip install -r requirements.txt
uvicorn src.api.main:app --reload

# 2. 前端（另一個終端）
cd frontend
npm install
npm run dev
```

- 前端：http://localhost:5173
- 後端 API：http://localhost:8000
- API 文件：http://localhost:8000/docs

## 可用指令

在前端指令列輸入：

| 指令 | 說明 | 範例 |
|------|------|------|
| `/diagnose-real WT-01` | 真實 SCADA 資料故障診斷 | `/diagnose-real WT-03` |
| `/diagnose WT-07` | 模擬故障診斷流程 | `/diagnose WT-07` |
| `/lit-search 主題` | 模擬文獻搜索 | `/lit-search wind turbine LLM` |

風機 ID 對應：WT-01 ~ WT-06 = Kelmarsh_1 ~ Kelmarsh_6

## 專案結構

```
windAILab/
├── .claude/                    # Claude Code 設定
│   ├── agents/                 # 8 個 AI 代理定義
│   ├── commands/               # 5 個 slash 指令
│   ├── hooks/                  # 自動化 hooks（待建）
│   └── rules/                  # coding rules（待建）
├── frontend/                   # React 虛擬辦公室
│   └── src/components/         # UI 元件
├── src/
│   ├── api/                    # FastAPI 後端
│   ├── agents/orchestrator/    # 代理協調引擎
│   ├── data_pipeline/          # 資料載入與清洗
│   ├── features/               # 特徵工程
│   └── models/evaluation/      # 異常偵測與健康評估
├── data/external/              # Kelmarsh SCADA 資料集
├── docs/templates/             # 5 個文件模板
├── CLAUDE.md                   # 系統行為規範
├── requirements.txt            # Python 依賴
└── pyproject.toml              # 專案設定
```

## 資料來源

Kelmarsh Wind Farm SCADA Dataset (CC-BY-4.0)
- 6 x Senvion MM92 (2050 kW, 92m rotor)
- 10-minute intervals, 2016 data
- Source: https://zenodo.org/records/5841834

## 技術棧

- **後端**: Python, FastAPI, WebSocket, pandas, scikit-learn
- **前端**: React 18, TypeScript, Vite, Tailwind CSS
- **通訊**: WebSocket 即時狀態推播
