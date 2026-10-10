# Lexus 流失風險洞察 — 2026 和泰 AI 黑客松

一句話：用 AI 聆聽台灣論壇上的 Lexus 售後討論，找出流失風險因子與 Persona，再對應到 CRM 指標，主動對高風險車主做有官方依據的溝通。

## 硬性規則（違反就會扣分或失格）
- 初賽截止 2026/10/14（三）13:00。交件：15 頁內 PDF 簡報 + 3 分鐘內 YouTube「不公開」影片。
- 影片標題固定：`Lexus_<作品名稱>_2026 和泰 AI 黑客松`
- 簡報必須包含七大架構：提案概述、目標對象與痛點、解決方案設計、AI 應用方法、獨特優勢與差異化、預期效益與落地評估、補充資料。
- 作品須未經公開發表：repo 保持 private，demo 不公開上線。
- 主辦單位寄的解題資源只放 `official/`（已 gitignore），不得外流。
- 不規避任何網站的反爬機制（403、Cloudflare、登入牆）。拿不到的來源改用官方 API 或人工整理樣本，並在簡報寫明限制。

## 事實來源
- 所有數字只能來自 `lexus_kit/out/`（由 `analyze.py` 產生）。不要手寫或估算數字。
- 溝通內容只能引用 `lexus_kit/knowledge/`（官方資料，每檔第一行是「來源：網址」）。
- 競賽規則與評分：`docs/brief.md`

## 指令
```bash
cd lexus_kit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt matplotlib
export GEMINI_API_KEY=...   # 只放環境變數，絕不寫進檔案
python analyze.py           # 不需 API，重產 out/
```

## 協作方式
- Git：用 `git switch` / `git restore`，每個任務一個分支，commit 用 Conventional Commits。
- Codex 負責實作任務；Claude 負責規劃、審查與寫作。互相審對方的產出。
- Claude 派工給 Codex 的方式（不透過 MCP）：
  1. 把任務寫成 `tasks/T-xxx.md`（目標、要改的檔案、驗收條件）
  2. `git switch -c feat/t-xxx`
  3. `codex exec --sandbox workspace-write "不要執行任何 git 指令。依 tasks/T-xxx.md 完成任務，完成後跑驗收條件裡的指令，並把變更摘要寫到 tasks/T-xxx.result.md"`
  4. Claude 讀 `T-xxx.result.md` 和 `git diff main...`，審查通過再 `git switch main && git merge --no-ff feat/t-xxx`
  - 一次只派一個 Codex 任務；超過 10 分鐘沒結束就回報給 Ino（macOS 沒有 `timeout` 指令，用 Bash 工具本身的 timeout）。
  - Codex 的沙盒不能寫 `.git`：開分支、commit、merge 一律由 Claude 做，Codex 只改檔案。派工時在指令裡寫明「不要執行任何 git 指令」。
  - `T-xxx.result.md` 必須包含：改了哪些檔案、驗收指令與輸出、未完成或有疑慮的地方。沒寫就退回重做。
## AI 分工與品質機制
- Gemini＝產品本身的 AI（標註、生成溝通內容）；Claude＝總指揮、寫作、審查；Codex＝實作，兼第二位獨立標註者。
- 重要產出一律交叉檢查，不讓產出者自己驗收：
  - 標註：Gemini 與 Codex 獨立標註 → 分歧由 Ino 看原文裁決。
  - 溝通訊息：程式檢查（數字與頁碼可在 knowledge 找到）+ 獨立 subagent 角色審查（Lexus 售後主管）。
  - 簡報：評分 subagent + 紅隊 subagent（和泰評審），兩者都不得看過寫作過程。
- AI 產出永遠不能被標示為人工判斷；AI 生成內容、模擬資料、人工輔助擷取樣本在簡報中都要明確標示。
- 執行計畫：`docs/RUNBOOK.md`。Ino 說「執行階段 N」時，照該階段的步驟做，完成條件全部達成才回報完成。
- 樣本數 < 5 的組別不下結論；簡報中的數字要附樣本數。
