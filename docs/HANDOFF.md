# HANDOFF（Ino 回來說 "continue" 時，Claude 從這裡接）

更新：2026-10-10 下午。截止 2026-10-14 13:00。

## 已完成
- 階段 0、1：已 merge。
- 論壇收集（Claude 用 Claude in Chrome 在 Ino 的 Brave 收）：Mobile01 29 串、Dcard 22 篇、留言 1033 則。
  原始檔 `lexus_kit/data/captures/`，匯入結果 `data/forum_manual.jsonl`。Ino 已允許 mobile01.com、dcard.tw 的「本機網路存取」。
  方法：頁面內執行擷取腳本 → POST 到本機 127.0.0.1:8765 的接收器（scratchpad 的 recv.py，已關閉）。
- 階段 3 前半（分支 `feat/multi-source`，**尚未 merge**）：import_captures 修正 Dcard 發文時間；51 篇已用 Gemini（gemini-3.5-flash-lite）標註，labels.jsonl 共 1640 篇。
  GEMINI_API_KEY 在 ~/.zshrc（Claude 的 shell 要先 `source ~/.zshrc`）。
- 階段 2（新流程）：
  - T-103 已 merge：Codex 獨立標註 60 篇 → `data/codex_labels.csv`。規則抽在 `tasks/T-103_rules.md`。
  - T-104 已 merge：`check_label_quality.py disagree` 與 `score --codex --disagree --md`。
    `data/disagreements.csv`（16 列，待 Ino 裁決）、`out/label_quality.md`（三組一致率已算出，裁決統計待填）。
  - `codex exec` 一定要加 `< /dev/null`，否則會卡在等 stdin。

## 階段 2 已完成（2026-10-10）
- Ino 確認 review_sheet 人工欄位為本人判斷（有看原文），並裁決 16 列分歧；皆已 commit。
- `out/label_quality.md`：三組一致率（各 n=60）＋裁決統計＋「Gemini 錯誤類型分析」（`<!-- manual -->` 以下為手寫，重跑 score --md 會保留）。
- 重點：Gemini vs 人工 相關 88%／情緒 83%／立場 90%；Codex vs 人工 93%／92%／90%。分歧裁決偏向 Codex（相關 4:1、情緒 7:2、立場 3:4）。

## 接下來：階段 3 後半（在 `feat/multi-source` 上做，做完才 merge）
1. 派 Codex（T-105）改 label_with_gemini.py：--model、--fewshot、--ids、輸出 confidence/reason；不得改既有欄位定義。
2. `data/fewshot.md`：依 label_quality.md 的錯誤類型 A、B、D 從裁決／人工答案挑 3–5 則（相關性過寬的購車文、他牌文推文稱讚 Lexus、接手二手車詢問外廠＝猶豫）。
3. relevant=True 全部用較強 Gemini 模型＋few-shot 重標 → labels_v2.jsonl；在人工 60 篇上比 v1/v2；較好就取代並重跑 categorize + analyze。
4. confidence=低 → data/low_confidence.csv。
5. Ino 同時：讀 07_quotes.csv 價格類原文，回答「貴」還是「不透明」。
- 之後照 RUNBOOK 階段 4 起。

## 規則提醒
- 一律用中文和 Ino 溝通；階段完成、可 /clear 時要明確說。
- 數字只能來自 lexus_kit/out/；AI 答案永遠不能填進 human_* 或稱為人工。
