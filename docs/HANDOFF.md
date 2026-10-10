# HANDOFF（Ino 回來說 "continue" 時，Claude 從這裡接）

更新：2026-10-10。截止 2026-10-14 13:00。

## 已完成
- 階段 0、1：merge 進 main（analyze.py 修好：quotes 只留負面且 relevant、註腳依 source 動態、中文字型）。
- T-102（collector 提速）已 merge：書籤改成佇列存 localStorage、Mobile01 自動捲動、存完 2 秒後跳下一篇。**尚未在真實網站測過**。舊書籤要用新的 `lexus_kit/collector/bookmarklet.txt` 覆蓋。
- `lexus_kit/data/review_sheet.csv`（60 筆，未被 git 追蹤）已產生，等 Ino 人工填 `human_relevant/human_sentiment/human_stance` 後存回原檔名（CSV UTF-8）。

## 使用者決定（不可更動）
- Ino 授權 Claude 做所有決定，目標只有「結果品質最好」；階段結束時給摘要（Claude 不能自己 /exit、/clear）。
- 人工標註 60 筆由 Ino 親自做。**Codex 不得冒充人工標註**；Codex 另外獨立標同 60 筆（不給看 Gemini 答案）→ 報告寫「雙 AI 一致率」，與「人工一致率」分開寫、各附 n。Claude 已明確拒絕把 AI 標註寫成人工。
- 不規避反爬；Mobile01 回 403。

## 等待中
1. Ino 正在重啟 Claude Code 以載入 Claude in Chrome 擴充功能（已安裝並 /chrome）。回來說 "continue" 後：
   - 先用 ToolSearch 確認 `mcp__claude-in-chrome__*` 工具存在；不存在就回報，不要重試很多次。
   - 存在：`tabs_context_mcp` → 新分頁，在 Mobile01 Lexus 討論區／站內搜尋「Lexus 保養」、Dcard 搜尋（關鍵字見 collector/README.md）按書籤收集（目標 Mobile01 40 串、Dcard 30 篇；時間緊就降到 20／15）。遇 Cloudflare、登入牆、權限提示就停下交給 Ino，不繞過。下載檔在 ~/Downloads（lexus_cap_*.json），之後 `python import_captures.py` 讀取（檢查 --src 預設路徑）。
2. Ino 的 review_sheet.csv 回傳。

## 接下來 Claude 要做（不等論壇資料，PTT 1589 篇為主）
- 派 Codex 獨立標註 60 筆（任務卡 T-103：讀 review_sheet 的 id → 原文在 data/labels.jsonl 以外的原始資料 data/ptt_lexus.jsonl；輸出 data/codex_labels.csv；不得讀 labels.jsonl 的答案欄），再算雙 AI 一致率。
- Ino 表格回來 → `check_label_quality.py score` → 寫 `out/label_quality.md`。
- 階段 3（多來源 import/label/categorize/analyze）→ 階段 4 凍結洞察（Claude 自行決定 Persona，docs/insights.md + lexus_kit/personas.json）→ 5 訊息生成 → 7 架構圖 → 8 簡報大綱與 check_numbers.py → 6 Demo（能做多少做多少）→ 9 影片腳本 → 10 交件檢查表。
- Ino 非做不可：人工標註、錄影旁白上傳 YouTube、套官方 pptx 模板匯出 PDF、官網交件。
- 一次只派一個 Codex 任務；Codex 不跑 git；Claude 審 diff 後 merge。commit 結尾加 Co-Authored-By 行。

## 備註
- venv：`cd lexus_kit && source .venv/bin/activate`；GEMINI_API_KEY 只放環境變數。
- 數字只能來自 lexus_kit/out/；溝通內容只能引用 lexus_kit/knowledge/（目前只有 lexus_owner_handbook.md，官網保修頁若缺要向 Ino 要或手動整理）。
