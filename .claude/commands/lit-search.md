# /lit-search - 系統性文獻搜索

當使用者呼叫此指令時，執行以下系統性文獻搜索與回顧工作流程。

## 步驟

### 1. 確認搜索主題和關鍵字
- 詢問使用者的研究主題（research topic）
- 與使用者共同擬定搜索關鍵字組合（keywords, Boolean operators）
- 確認搜索的時間範圍（例如近 5 年）
- 確認是否有特定排除條件（exclusion criteria）

### 2. 搜索 arXiv, IEEE Xplore, Scopus
- 在 arXiv 搜索預印本論文，特別關注 cs.AI, cs.LG, eess.SP 等相關類別
- 在 IEEE Xplore 搜索期刊與會議論文（風能、電力系統、PHM 相關）
- 在 Scopus 進行跨領域搜索，擴大涵蓋範圍
- 記錄每個資料庫的搜索策略與命中數量

### 3. 篩選相關論文
- 依據 title 和 abstract 進行第一輪篩選
- 移除重複論文（deduplication）
- 依據 inclusion/exclusion criteria 進行第二輪篩選
- 標記高影響力論文（high citation count, top venue）
- 回報篩選結果統計給使用者確認

### 4. 整理成文獻回顧表格
- 建立結構化的文獻回顧表格，包含以下欄位：
  - 論文標題（Title）
  - 作者（Authors）
  - 年份（Year）
  - 發表場域（Venue）
  - 研究方法（Methodology）
  - 主要貢獻（Key Contribution）
  - 資料集（Dataset）
  - 與本研究的相關性（Relevance）
- 依主題分群（thematic clustering）整理論文

### 5. 分析研究缺口
- 從文獻中歸納出目前研究的主要趨勢（research trends）
- 識別尚未被充分探討的研究缺口（research gaps）
- 提出潛在的研究方向建議
- 產出文獻回顧摘要報告，包含視覺化的研究地圖（research landscape）

## 呼叫的 Agents
- `wRes:literature-reviewer` - 文獻回顧專家
