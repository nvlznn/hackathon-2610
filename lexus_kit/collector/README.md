# Mobile01／Dcard 收集方式

這兩個網站擋程式自動抓取（Mobile01 回 403），所以改成「人在瀏覽器裡看、按書籤存」：
每次只存你正在看的那一頁，速度和一般瀏覽一樣，不繞過任何防護。

## 1. 安裝書籤（一次）
1. 打開 `bookmarklet.txt`，全選複製（整段 `javascript:...`）。
2. Chrome 書籤列按右鍵 →「新增網頁」→ 名稱填「存 Lexus」，貼到「新增網頁」對話框的網址欄（不是瀏覽器網址列）。
3. 第一次下載時 Chrome 若問「允許下載多個檔案」，選允許。

## 2. 找文章（列表頁按一次書籤 → 存連結）
- Dcard 搜尋：`https://www.dcard.tw/search?query=lexus 保養`，可換關鍵字：lexus 維修、lexus 原廠、lexus 外廠、lexus 保固、凌志 保養、北都、國都。
  捲到底讓結果載入多一點再按書籤。
- Mobile01：汽車 → 品牌 → Lexus 討論區，或用站內搜尋「Lexus 保養」。在列表頁按書籤。

## 3. 收集文章（列表按一次，逐篇按一次）
列表／搜尋頁按書籤後會下載連結備份，並把連結加入該網站的瀏覽器佇列。點開佇列中的文章後按一次書籤存檔；Mobile01 多頁串每頁都要再按一次，最後一頁或 Dcard 存完會提示並於 2 秒後前往下一篇，可按「停止自動跳轉」留在原頁。
提示會顯示已完成數／佇列數；新頁仍需你手動按書籤才會擷取。

若要檢視舊版匯入佇列：
```bash
cd lexus_kit
python import_captures.py --queue      # 產生 collector/queue.html（尚未讀的文章）
open collector/queue.html
```

建議量：Mobile01 40–60 串、Dcard 30–50 篇，優先選有提到保養、維修、保固、外廠的。

## 4. 匯入並標註
```bash
python import_captures.py                                              # → data/forum_manual.jsonl
python label_with_gemini.py --inp data/forum_manual.jsonl --out data/labels.jsonl   # 只會標新的
python categorize.py apply && python analyze.py
```
