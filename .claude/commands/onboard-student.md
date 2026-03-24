# /onboard-student - 新研究生入職引導

當使用者呼叫此指令時，執行以下新研究生入職引導工作流程，協助新成員快速融入研究室。

## 步驟

### 1. 詢問學生背景
- 詢問學生的基本資訊：
  - 姓名與學位階段（碩士 / 博士）
  - 程式能力評估（Python 熟練度、是否有 ML/DL 經驗）
  - 領域知識背景（風能工程、電機工程、資訊工程、其他）
  - 過去的研究或專題經驗
  - 英文閱讀與寫作能力自評
- 根據背景資訊判斷學生的起始程度

### 2. 生成個人化學習路徑
- 使用 wRes:teaching-assistant 根據學生背景，客製化學習路徑
- 學習路徑分為三個階段：
  - **基礎期（第 1-4 週）**：補足先備知識、熟悉工具
  - **進階期（第 5-8 週）**：深入研究方法、複現經典論文
  - **研究期（第 9-12 週）**：開始獨立研究任務
- 每個階段列出具體的學習目標和里程碑（milestones）

### 3. 推薦必讀論文清單
- 依據學生的研究方向，推薦必讀論文，分為兩大類：
  - **風能基礎（Wind Energy Fundamentals）**：
    - 風力發電系統概論
    - SCADA 資料分析
    - 風機故障診斷與預測維護（PHM）
  - **AI 基礎（AI Fundamentals）**：
    - Machine Learning 經典方法
    - Deep Learning 核心架構（CNN, RNN, Transformer）
    - LLM 與 RAG 技術
- 每篇論文標註閱讀優先順序和預估閱讀時間

### 4. 開發環境設定指引
- 提供逐步設定指引，包含：
  - **Python 環境**：Anaconda/Miniconda 安裝、虛擬環境管理、常用套件（numpy, pandas, scikit-learn, PyTorch）
  - **Git 版本控制**：Git 安裝與設定、GitHub/GitLab 帳號、基本操作流程（clone, branch, commit, push, pull request）
  - **MLflow 實驗管理**：MLflow 安裝與設定、experiment tracking 基本用法、model registry 概念
  - **其他工具**：VS Code 設定、Jupyter Notebook、LaTeX 環境
- 確認學生成功完成所有環境設定

### 5. 建立研究室規範文件
- 介紹研究室的工作規範：
  - 程式碼管理規範（coding conventions, Git workflow）
  - 實驗記錄規範（experiment logging protocol）
  - 論文閱讀與報告規範（paper reading seminar format）
  - 會議與進度回報規範（weekly meeting, progress report）
  - 資料管理規範（data storage, naming conventions）
- 確認學生理解並同意遵守所有規範

### 6. 設定第一個練習任務
- 根據學生的背景和研究方向，指派一個入門練習任務，例如：
  - 使用 SCADA 資料進行基礎的 exploratory data analysis（EDA）
  - 複現一篇經典的風機故障偵測論文
  - 建構一個簡單的 RAG pipeline prototype
- 明確定義：
  - 任務目標（objective）
  - 預期產出（deliverables）
  - 截止日期（deadline）
  - 評估標準（evaluation criteria）
- 安排第一次 check-in 時間

## 呼叫的 Agents
- `wRes:teaching-assistant` - 教學助理
