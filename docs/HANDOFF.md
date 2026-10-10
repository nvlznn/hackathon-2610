# HANDOFF（Ino 回來說 "continue" 時，Claude 從這裡接）

更新：2026-10-10 晚上。截止 2026-10-14 13:00。

## 已完成
- 階段 0–4 全部 merge 進 main。
- 資料：PTT 1589、Mobile01 29、Dcard 22 篇（共 1640）；relevant 358 篇（PTT 312／Mobile01 27／Dcard 19）。
- 標註品質：`out/label_quality.md`。Gemini vs 人工：相關 88%／情緒 83%／立場 90%（各 n=60）。沿用 v1，不做第二段重標（免費額度不足）。
- **階段 4 已凍結**：`docs/insights.md` + `lexus_kit/personas.json`。之後要改洞察，先改 insights.md 再往下同步。

## 階段 4 的決定（Ino 同意）
1. 主數字只用 PTT：`lexus_kit/out/ptt_only/`（重產指令寫在 insights.md 第 0 節）。合併三來源（`out/`）只當敏感度檢查。
2. 「保固與權益」不當主要驅動因素（PTT n=8）；保固改用車齡趨勢支撐。
3. 經銷商信任事件（2026-08，14 篇）在簡報不點名經銷商。
4. CRM 門檻（90 天、8 個月、P75、建議項目拒絕率 50%）是假設，已標〔假設〕。
5. 不重收 Mobile01／Dcard（兩站禁止自動擷取、時間不夠）。簡報寫「三個平台方向一致；比例以全版爬取的 PTT 計算」。
6. Persona 名稱照預設：保固後精算型（主要）、二手入主型、新車守護型。

## 接下來
- RUNBOOK 階段 5（溝通訊息生成）。先問 Ino 能不能拿到 Dylan 的 `generate_messages.py`。
- Gemini 免費額度：flash-lite 可用；其他模型額度不足，必要時請 Ino 開付費方案。
- Demo 的風險權重從 `personas.json` 的 `weight_ref` 讀 `out/ptt_only/` 的 CSV，不寫死數字。

## 規則提醒
- 一律用中文和 Ino 溝通；階段完成、可 /clear 時要明確說。
- 數字只能來自 lexus_kit/out/（主數字 out/ptt_only/）；AI 答案永遠不能填進 human_* 或稱為人工。
- 引用原文前先回 `data/ptt_lexus.jsonl`／`data/forum_manual.jsonl` 確認原文存在（evidence_quote 是 Gemini 擷取的）。
- `codex exec` 一定要加 `< /dev/null`；GEMINI_API_KEY 在 ~/.zshrc（先 `source ~/.zshrc`）。
