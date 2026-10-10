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
- 樣本數 < 5 的組別不下結論；簡報中的數字要附樣本數。
