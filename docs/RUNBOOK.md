# RUNBOOK — 從現在到交件

> Ino 對 Claude 說「執行階段 N」，Claude 照本頁該階段做。每階段都有：目標、Claude 要做的事、Ino 同時要做的事、完成條件。
> 每個階段開始前 `/clear`；狀態只存在檔案裡。所有數字只能來自 `lexus_kit/out/`，溝通內容只能引用 `lexus_kit/knowledge/`。
> 截止：2026/10/14（三）13:00。目標：10/13 晚上交第一版，之後只做修改。

優先順序（時間不夠時由下往上砍）：簡報 > 影片 > 溝通訊息範例 > Demo > 多來源資料。

---

## 階段 0｜整理（5 分鐘）
- Claude：刪除 `tasks/T-000*`，保留 `tasks/` 資料夾（放 `.gitkeep`），commit `chore: add tasks dir and runbook`，push。
- 完成條件：`git status` 乾淨。

## 階段 1｜修資料品質（約 45 分鐘）
目標：現有 PTT 分析結果可以放心放進簡報。
- Claude 開 `fix/data-quality`，寫一張任務卡派給 Codex：
  1. `analyze.py`：`07_quotes.csv` 只挑 `sentiment == 負面` 且 `relevant == True` 的原文；每類最多 5 則，依推文數排序。
  2. 所有圖表註腳與 `summary.md` 改成依 `source` 動態寫出資料來源與 n，不再寫死「PTT 汽車版」。
  3. 圖表中文字型在 macOS 能正常顯示（不能出現方框）。
  4. 驗收：`python analyze.py` 成功；`07_quotes.csv` 沒有正面句子；summary 的數字與修改前一致（除了 quotes）。
- Claude 審 diff、跑驗收、開幾張圖確認，merge。
- **Ino 同時做**：安裝書籤（`lexus_kit/collector/README.md` 第 1 步），開始收 Dcard／Mobile01（第 2、3 步）。目標：Mobile01 40 串、Dcard 30 篇。第一串 Mobile01 存完，確認右下角提示的則數和頁面一致；不一致就告訴 Claude。
- 完成條件：merge 進 main；Ino 已收到至少 20 篇。

## 階段 2｜標註品質：雙 AI 交叉標註 + 人工裁決（約 50 分鐘）
目標：拿到可以放進簡報、經得起追問的標註品質數字，並把人工時間花在最難的案例。
1. Claude 派 Codex（任務卡 T-103）：只讀 `data/review_sheet.csv` 的 id 與 `data/ptt_lexus.jsonl` 原文，依 `label_with_gemini.py` 的規則獨立標 `relevant／sentiment／stance`，輸出 `data/codex_labels.csv`。**不得讀 `labels.jsonl`、`labels.csv`、review_sheet 的人工欄位。**
2. Claude 比對 Gemini 與 Codex，產生 `data/disagreements.csv`（兩者任一欄不同的列，附原文連結與兩邊答案）。
3. **Ino 人工**：
   - 先確認 `review_sheet.csv` 的人工欄位是自己填的；若有任何格不是本人判斷，從 `review_sheet.csv.bak` 還原重填。
   - 判斷時要點開原文，不能只看 `summary`（那是 Gemini 寫的，會讓一致率虛高）；至少 `relevant = 是` 的列與 `disagreements.csv` 的列要看原文。
   - 在 `disagreements.csv` 填 `adjudicated` 欄（最終答案）。
4. Claude 執行 `check_label_quality.py score`，寫 `out/label_quality.md`，分開列出、各附 n：
   - Gemini vs 人工、Codex vs 人工（人工一致率）
   - Gemini vs Codex（雙 AI 一致率）
   - 分歧案例數與人工裁決結果；Gemini 錯在哪幾類（作為階段 3 的範例來源）
- 完成條件：`out/label_quality.md` 存在且三組數字齊全。任一欄人工一致率 < 70% 時，在簡報限制頁寫明，並在階段 3 用範例改善。
- 鐵則：AI 的答案永遠不能填進 `human_*` 欄位或被稱為人工標註。

## 階段 3｜多來源資料（收集量達標後，約 30 分鐘）
- Claude 開 `feat/multi-source`：
  1. `python import_captures.py` → `data/forum_manual.jsonl`，回報各來源篇數與警告。
  2. `python label_with_gemini.py --inp data/forum_manual.jsonl --out data/labels.jsonl`（只標新的）。
  3. `python categorize.py apply && python analyze.py`。
  4. 回報：各來源篇數、relevant 篇數；五個關鍵發現有沒有改變（列前後數字）；樣本數 < 5 的組別。
- 兩段式標註（品質優先，在 merge 前做）：
  1. 派 Codex 修改 `label_with_gemini.py`：新增 `--model`（覆蓋 `GEMINI_MODEL`）、`--fewshot <檔案>`（把範例附在 prompt 規則後）、輸出新增 `confidence`（高／中／低）與 `reason` 欄位；`--ids <檔案>` 只重標指定 id。不得改動既有欄位定義。
  2. 範例：從 `disagreements.csv` 的人工裁決挑 3–5 則最具代表性的（含原文片段與正確答案），存 `data/fewshot.md`。
  3. 對所有 `relevant = True` 的文章（含新來源），用帳號可用的較強 Gemini 模型 + few-shot 重標，輸出 `data/labels_v2.jsonl`；其餘文章維持第一段結果。
  4. 抽 20 篇比較 v1／v2；若 v2 在人工裁決過的案例上更準，就以 v2 取代並重跑 categorize + analyze，在 `out/label_quality.md` 記錄改善幅度。
  5. `confidence = 低` 的文章列成 `data/low_confidence.csv`；不進入代表原文與 Persona 依據，簡報寫明處理方式。
- merge。
- **Ino 同時做**：讀 `07_quotes.csv` 價格類 15 篇原文，回答 Claude：車主不滿的是「貴」還是「不透明、被當盤子」？舉 2–3 句原文為證。
- 完成條件：`out/summary.md` 含三個來源；Ino 的價格判斷已寫進 `docs/insights.md`。

## 階段 4｜凍結洞察（約 30 分鐘，之後不再改）
目標：一份所有產出共用的「事實來源」，簡報、影片、Demo 都從這裡取。
- Claude 寫 `docs/insights.md`：
  1. 五個關鍵發現（每個附數字、n、對應圖表檔名、代表原文 1 句含連結）。
  2. 三個 Persona（名稱、特徵、數據依據、流失風險、觸發時機、溝通目標、主要接觸點）。預設：保固後精算型（主要）、二手入主型、新車守護型；Ino 可改。
  3. 風險因子 → CRM 可觀察指標對照表，例如：保固將屆 = 交車日 + 4 年 − 今天 < 90 天；價格敏感 = 上次保養金額高於同車型同里程 P75；二手 = 非原始購車人；疏離 = 距上次回廠 > 8 個月；失去權益 = 準時定保次數中斷、Elite 等級下降。
  4. 限制：網路聲量不等於全體車主、相關不等於因果、Mobile01／Dcard 為人工擷取樣本、小樣本組別。
- 同時寫 `lexus_kit/personas.json`（給程式用，內容與 insights.md 一致）。
- **Ino**：讀過、改到同意，回覆「凍結」。之後要改洞察必須先改這份檔案。
- 完成條件：Ino 說「凍結」，commit `docs: freeze insights`。

## 階段 5｜溝通訊息生成（約 1 小時）
目標：產出 2 要的「AI 生成內容範例」，而且每句都有官方依據。
- `generate_messages.py` 不在 repo 裡（Dylan 那邊可能有）。先問 Ino 能不能拿到；拿不到就由 Codex 新寫。
- Claude 開 `feat/messages`，派 Codex：
  1. 輸入：`personas.json`、`knowledge/*.md`。輸出：`out/messages.csv`，每 Persona × 接觸點（LINE、App 推播、簡訊、服務專員話術）各 2 則。
  2. 用 Gemini 的結構化輸出：`{persona, touchpoint, trigger, message, citations:[手冊頁碼], claims:[訊息中的事實句]}`。
  3. 自動檢查（不用 LLM）：citations 的頁碼必須在 knowledge 中出現；訊息中的每個數字（金額、年限、里程、百分比）都必須能在 knowledge 原文找到；不得出現「最便宜」「保證」等未經授權的承諾詞。輸出欄位 `check = 通過／不通過 + 原因`。
  4. 語氣：Lexus 品牌語氣（尊重、不推銷、以車主為中心），LINE 訊息 120 字內。
  5. 驗收：跑完、至少 70% 通過檢查。
- 第二道檢查（角色審查）：Claude 開一個沒看過生成過程的 subagent，扮演「Lexus 台灣售後服務部門主管」，只給它 `personas.json`、`knowledge/` 與通過自動檢查的訊息，逐則評分（1–5）：
  1. 會不會讓車主覺得被推銷或被監控？
  2. 有沒有回應該 Persona 的核心痛點（例如價格不透明）？
  3. 以品牌立場，你敢不敢真的發出去？哪一句要改？
  結果寫 `out/messages_review.csv`。三項都 ≥ 4 分才算合格；不合格的依建議改寫後重跑兩道檢查，最多兩輪。
- Claude 從「自動檢查通過且角色審查合格」的訊息中，挑每個 Persona 最好的 1–2 則，寫進 `docs/insights.md` 的「訊息範例」段。
- 完成條件：`out/messages.csv` 存在，有挑好的範例。

## 階段 6｜Demo（約 2.5 小時，可砍）
目標：決賽要能操作的雛型；初賽用於影片與截圖。只做四頁 Streamlit（`demo/app.py`）。
- Claude 先給 Ino 頁面規劃與任務卡，Ino 回「OK」才派 Codex。一頁一張卡、一頁一個分支。
1. **輿情儀表板**：讀 `out/*.csv`，顯示五個關鍵發現、流失驅動因素圖、來源分布、代表原文（可點連結）。
2. **車主風險雷達**：`demo/data/crm_mock.csv`（固定 seed 產生 500 位「模擬」車主，頁面上明確標示模擬資料）。風險分數 = 階段 4 對照表的透明規則加權，權重取自 `out/02_churn_drivers.csv` 的倍數；每位車主顯示前三個風險原因、對應 Persona、建議接觸時機。可依 Persona、風險等級篩選。
3. **溝通工作台**：選一位車主 → 依 Persona 與觸發時機即時生成訊息（呼叫階段 5 的生成函式）→ 顯示引用頁碼與自動檢查結果 → 服務專員可編輯、核准或退回（存進 session，不真的發送）。
4. **AI 保養報價說明**：輸入或選擇一張範例報價單（項目 + 金額）→ AI 逐項用白話解釋為什麼要做，並標出這項是否屬於保證範圍、可以累積的權益（Points 1.5%、準時定保累計延長保證）。**不得編造保養週期或價格**；手冊沒寫的項目要標示「需接原廠保養週期資料」。
- 驗收：`streamlit run demo/app.py` 四頁都能操作、沒有錯誤；沒有 API key 時第 3、4 頁顯示預先產生的範例而不是當掉。
- **Ino**：每頁完成後親自點過一輪，回報要改的地方（每頁最多一輪修改）。
- 完成條件：四頁可操作，或時間到時把未完成的頁面改用流程圖呈現。

## 階段 7｜架構圖（約 30 分鐘）
- Claude 用 Mermaid 畫兩張，輸出成 PNG 到 `docs/figures/`：
  1. **AI 網路輿情洞察系統架構**（產出 1）：資料來源（PTT 爬蟲、Mobile01／Dcard 人工擷取、正式版接授權輿情資料源）→ 清理去重 → Gemini 結構化標註 → 歸類 → 統計與 Persona → 儀表板；旁邊註明人工驗證一致率。
  2. **溝通計畫運作流程**（產出 2）：CRM 指標 → 風險評分 → Persona 判定 → 觸發時機 → 知識庫檢索 → Gemini 生成 → 自動檢查 → 服務專員審核 → 發送管道 → 成效回收（回廠率）→ 回饋調整權重。
- 完成條件：兩張 PNG，文字清楚、中文不亂碼。

## 階段 8｜簡報（約 3 小時）
- Claude 先出 15 頁大綱（每頁：標題、一句主訊息、要放的數字或圖檔、對應評分項）。Ino 確認後才寫內容。
- 建議頁面配置（對應官方七大架構）：
  1. 封面（作品名稱、一句話）
  2. 提案概述（問題 → 方案 → 成果，一頁看懂）
  3. 目標對象與痛點：流失的商業衝擊
  4. 資料與 AI 分析方法（來源、篇數、Gemini 標註、一致率）← 產出 1 要求說明 AI 技術
  5. 高風險議題與輿情趨勢（流失驅動因素、經銷商信任事件）
  6. 價格洞察深挖：不是貴，是不透明（原文佐證）
  7. 三個 Persona
  8. 解決方案架構：Listen → Score → Act → Learn
  9. 流失風險辨識機制：輿情因子 → CRM 指標 → 風險分數
  10. 溝通計畫：Persona × 觸發時機 × 接觸點
  11. AI 生成內容範例 + 報價說明（附手冊頁碼）
  12. AI 方案運作流程圖
  13. 獨特優勢與差異化（vs 現有 AI 客服、vs 一般輿情監測）
  14. 預期效益與落地評估（KPI：回廠率、保固後留存率、延長保證加購率；三階段導入；成本與風險）
  15. 補充資料（資料限制、方法細節、Demo 截圖或連結）
- **Ino**：把內容套進官方 .pptx 模板（官網「報名資料下載」），匯出 PDF。
- Claude 檢查：
  1. 開一個沒看過寫作過程的 subagent，只給它 `docs/brief.md` 和 PDF 文字，依初賽四項評分逐項打分（1–10）並列出前五個缺口。
  2. 寫 `scripts/check_numbers.py`：抽出 PDF 中所有數字，比對 `out/` 與 `knowledge/`，列出找不到來源的數字。
  3. 紅隊評審：再開一個獨立 subagent，扮演「和泰集團評審（售後業務主管 + 資料科學主管）」，讀完簡報後提出最難回答的 5 個問題（例：網路聲量能代表全體車主嗎？沒有 CRM 資料憑什麼說能落地？成本多少？和現有 AI 客服差在哪？誤判風險怎麼控制？）。Claude 把每題的回答寫進 `docs/qa_prep.md`，並確認簡報或補充資料裡找得到答案依據；找不到就補。
  4. 依三份報告修改，最多兩輪。
- AI 使用揭露（寫在第 15 頁補充資料，一小段）：
  - 解決方案中的 AI（主頁已詳述）：Gemini 結構化標註、雙 AI 交叉標註 + 人工裁決、Gemini 生成溝通內容 + 出處自動檢查 + 角色審查、服務專員人工核准。
  - 開發過程：團隊以 Claude Code 與 Codex 輔助撰寫程式與文件草稿；Persona、洞察結論、溝通策略、標註裁決由團隊判斷與確認。這也代表 Lexus 導入與維護此系統的人力成本低。
  - 標示：AI 生成內容標「AI 生成範例」、CRM 標「模擬資料」、Mobile01／Dcard 標「人工輔助擷取樣本」。

- 完成條件：PDF ≤ 15 頁，數字檢查全數有來源。

## 階段 9｜影片（約 2 小時）
- Claude 寫 `docs/video_script.md`：約 900 字、3 分鐘以內，每段標出畫面。
  - 0:00–0:20 鉤子：一位保固剛到期的車主正在 PTT 問「外面保養廠推薦？」
  - 0:20–0:55 洞察：三個數字 + 一個 Persona
  - 0:55–2:20 Demo：四頁依序操作（沒做完的頁用流程圖代替）
  - 2:20–2:50 效益與落地
  - 2:50–3:00 結語與作品名稱
- **Ino**：錄畫面（QuickTime 或 OBS）、錄旁白、剪輯。上傳 YouTube，設為「不公開」，標題 `Lexus_<作品名稱>_2026 和泰 AI 黑客松`。用無痕視窗確認連結能看。
- 完成條件：影片 ≤ 3:00，連結在無痕視窗可播放。

## 階段 10｜交件（30 分鐘）
- Claude 產出交件檢查表並逐項打勾：
  - [ ] PDF ≤ 15 頁，七大架構都在
  - [ ] 影片 ≤ 3 分鐘、不公開、標題格式正確、無痕視窗可看
  - [ ] 作品名稱在簡報、影片、標題三處一致
  - [ ] 簡報沒有放 API 金鑰、個資、主辦單位原始資料全文
  - [ ] repo 是 private
- **Ino**：隊長登入官網 → 右上角頭像 →「投稿紀錄」→「前往修改」→ 上傳 PDF 與影片連結 →「請求更新」。確認收到通知信。
- 截止前可以無限次重新上傳，以最後一次為準。系統出問題時，截圖寄 ht-hackathon@bhuntr.com（必須在 13:00 前）。
- 完成條件：收到成功通知信。

---

## 卡住時
- 超出範圍：「記到 `docs/TODO.md`，先不做」。
- Codex 改壞：Claude 用 `git restore` 或丟掉分支，換做法重派。
- 進度落後超過 1 小時：Claude 主動提出要砍什麼（依頁首的優先順序）。
