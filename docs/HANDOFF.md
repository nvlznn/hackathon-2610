# HANDOFF（Ino 回來說 "continue" 時，Claude 從這裡接）

更新：2026-10-10 晚上。截止 2026-10-14 13:00。

## 已完成
- 階段 0–3 全部 merge 進 main。
- 資料：PTT 1589、Mobile01 29、Dcard 22 篇（共 1640）；relevant 358 篇（PTT 312／Mobile01 27／Dcard 19）。
- 標註品質：`out/label_quality.md`。Gemini vs 人工：相關 88%／情緒 83%／立場 90%（各 n=60）。
- 階段 3 決定（Ino）：**不做第二段重標**。原因是 Gemini 免費方案額度不足（Pro 額度 0、3.8-flash 每天 20 次）。沿用 v1，簡報限制頁寫一致率。工具已就緒，見 label_quality.md 最後一節。
- Ino 的價格判斷已寫進 `docs/insights.md`：不滿的是「不透明、被當盤子」，不是「貴」（質性觀察，約 6 篇，不可當比例）。
- analyze.py：趨勢圖只用 PTT；summary 新增「各來源比較」與各來源資料期間。

## 階段 4 要先處理的問題（寫 insights.md 時決定）
1. **合併比例被人工挑選的串拉高**：車主流失傾向合併後是 28.1%（61/217），但 PTT 23.5%（43/183）、Mobile01 63.6%（14/22）、Dcard 33.3%（4/12）。Mobile01／Dcard 是人工挑選的討論串。建議關鍵比例以 PTT 為主，或並列 PTT-only 與合併數字。要和 Ino 確認。
2. **「價格與收費」類混進非保養收費**（Ino 發現）：07_quotes 該類 5 句中有 3 句是事故估價、購車價、老車維修費。引用這類篇數時要說明，或只引用 Ino 讀過的保養價格原文。
3. 流失驅動因素排序變了：保固與權益 56.2%（9/16）、價格與收費 52.3%（45/86）、服務態度 50.0%（9/18）。保固與權益 n=16，偏小。
4. Gemini 免費額度也會卡住階段 5（生成溝通訊息）。flash-lite 仍可用，否則請 Ino 開付費方案。

## 接下來
- 照 RUNBOOK 階段 4（凍結洞察）。

## 規則提醒
- 一律用中文和 Ino 溝通；階段完成、可 /clear 時要明確說。
- 數字只能來自 lexus_kit/out/；AI 答案永遠不能填進 human_* 或稱為人工。
- `codex exec` 一定要加 `< /dev/null`；GEMINI_API_KEY 在 ~/.zshrc（先 `source ~/.zshrc`）。
