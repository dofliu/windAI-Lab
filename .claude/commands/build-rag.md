# /build-rag - 建構 RAG 維護知識庫

當使用者呼叫此指令時，執行以下 Retrieval-Augmented Generation（RAG）維護知識庫建構工作流程。

## 步驟

### 1. 確認知識來源
- 詢問使用者要納入的知識來源類型：
  - 維護手冊（maintenance manuals）
  - 故障報告（fault reports / incident logs）
  - 標準文件（IEC standards, OEM specifications）
  - SCADA 歷史告警紀錄
  - 其他技術文件
- 確認文件格式（PDF, Word, Excel, plain text 等）
- 確認語言（中文、英文、或混合）

### 2. 收集並整理文件
- 掃描指定目錄，列出所有可用文件
- 對文件進行分類與標註（document classification & tagging）
- 建立文件清單（document inventory），包含檔名、類型、頁數、語言
- 識別並處理重複或過時的文件
- 回報文件收集統計，讓使用者確認

### 3. 決定分塊策略和 Embedding 模型
- 使用 wAI:rag-architect 設計最佳的 chunking strategy：
  - Chunk size 和 overlap 參數
  - 分塊方式（fixed-size, semantic, recursive, document-structure-aware）
  - 針對表格和圖片的特殊處理策略
- 使用 wAI:llm-specialist 選擇合適的 embedding model：
  - 考量多語言支援需求
  - 評估 domain-specific vs. general-purpose embeddings
  - 確認 vector dimension 和 similarity metric

### 4. 執行 Indexing
- 對所有文件執行 text extraction 和 preprocessing
- 依照決定的策略進行 chunking
- 生成 embeddings 並寫入 vector database
- 建立 metadata index（文件來源、章節、設備型號等）
- 回報 indexing 進度和統計數據（total chunks, avg chunk size 等）

### 5. 品質測試
- **Retrieval Accuracy Test**：使用預先設計的測試問題，驗證 retrieval 結果的準確性
- **Hallucination Test**：檢查 LLM 回答是否忠於 retrieved context，偵測幻覺現象
- **Edge Case Test**：測試跨文件查詢、多語言查詢、模糊查詢等情境
- 計算量化指標（precision, recall, MRR, faithfulness score）
- 根據測試結果調整 chunking 或 retrieval 參數

### 6. 產出 RAG KB 規格文件
- 生成完整的 RAG Knowledge Base 規格文件，包含：
  - 知識庫概述（KB Overview）
  - 文件來源清單（Source Documents）
  - 分塊策略與參數（Chunking Configuration）
  - Embedding 模型規格（Embedding Model Specs）
  - Vector Database 設定（DB Configuration）
  - 品質測試報告（Quality Test Report）
  - 維護與更新指引（Maintenance & Update Guide）

## 呼叫的 Agents
- `wAI:rag-architect` - RAG 架構設計專家
- `wAI:llm-specialist` - LLM 技術專家
- Domain experts（依知識領域動態派遣）
