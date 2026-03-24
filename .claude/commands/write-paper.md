# /write-paper - 論文撰寫工作流

當使用者呼叫此指令時，執行以下學術論文撰寫工作流程。每個章節需經使用者確認後，方可進入下一章節。

## 步驟

### 1. 確認論文主題和目標期刊
- 詢問使用者的論文主題（paper topic）和核心貢獻（main contribution）
- 確認目標期刊或會議（target venue），例如 Applied Energy, Renewable Energy, Wind Energy 等
- 取得目標期刊的格式要求（formatting guidelines）和字數限制
- 確認論文類型（research article, review paper, short communication）

### 2. 文獻完整性檢查
- 使用 wRes:literature-reviewer 檢查現有文獻收集是否完整
- 確認所有關鍵的 baseline methods 和 state-of-the-art 方法都已涵蓋
- 若有缺漏，建議補充搜索的方向
- 整理 reference list 初稿

### 3. 建立論文骨架
- 依據目標期刊格式，建立完整的論文結構：
  - **Abstract** - 研究摘要（背景、方法、結果、結論）
  - **Introduction** - 研究背景與動機、研究問題、主要貢獻
  - **Related Work** - 相關文獻回顧與定位
  - **Methodology** - 提出的方法詳述
  - **Experiments** - 實驗設計、資料集、評估指標
  - **Results** - 實驗結果呈現
  - **Discussion** - 結果討論、限制與未來工作
  - **Conclusion** - 總結
- 每個章節列出要點大綱，提交使用者審核

### 4. 逐章撰寫
- 使用 wRes:paper-writer 逐章撰寫論文內容
- **每完成一個章節，必須暫停等待使用者確認後再繼續下一章**
- 撰寫順序建議：Methodology → Experiments → Results → Introduction → Related Work → Discussion → Conclusion → Abstract
- 確保章節間的邏輯連貫性和術語一致性

### 5. 圖表策略設計
- 使用 wRes:data-storyteller 規劃論文所需的圖表
- 設計 figure 清單（architecture diagram, result comparison charts, ablation study plots）
- 設計 table 清單（dataset statistics, hyperparameters, comparison results）
- 確保圖表風格統一，符合目標期刊要求
- 撰寫圖表說明文字（captions）

### 6. 整合 iWrite 系列做學術潤飾
- 使用 iWrite agents 進行學術英文潤飾
- 檢查文法、用字精確性和學術寫作風格
- 確保 tense 使用正確（Methods 用 past tense, general facts 用 present tense）
- 檢查 citation 格式是否符合目標期刊要求
- 最終校對（proofreading）並產出定稿

## 呼叫的 Agents
- `wRes:paper-writer` - 論文撰寫專家
- `wRes:literature-reviewer` - 文獻回顧專家
- `wRes:data-storyteller` - 資料視覺化與敘事專家
- iWrite agents - 學術英文潤飾系列工具
