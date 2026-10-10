# Mobile01／Dcard 收集方式

這兩個網站擋程式自動抓取（Mobile01 回 403），所以改成「人在瀏覽器裡看、按書籤存」：
每次只存你正在看的那一頁，速度和一般瀏覽一樣，不繞過任何防護。

## 1. 安裝書籤（一次）
1. 打開 `bookmarklet.txt`，全選複製（整段 `javascript:...`）。
2. Chrome 書籤列按右鍵 →「新增網頁」→ 名稱填「存 Lexus」，網址貼上剛剛那段。
3. 第一次下載時 Chrome 若問「允許下載多個檔案」，選允許。

## 2. 找文章（列表頁按一次書籤 → 存連結）
- Dcard 搜尋：`https://www.dcard.tw/search?query=lexus 保養`，可換關鍵字：lexus 維修、lexus 原廠、lexus 外廠、lexus 保固、凌志 保養、北都、國都。
  捲到底讓結果載入多一點再按書籤。
- Mobile01：汽車 → 品牌 → Lexus 討論區，或用站內搜尋「Lexus 保養」。在列表頁按書籤。

## 3. 讀文章（文章頁按一次書籤 → 存內容）
```bash
cd lexus_kit
python import_captures.py --queue      # 產生 collector/queue.html（尚未讀的文章）
open collector/queue.html
```
在清單裡一篇篇點開 → 按書籤 → 關分頁。Mobile01 有多頁的串，每一頁都要按。
Dcard 會自動捲動載入留言（約 10 秒），看到右下角提示再關分頁。

建議量：Mobile01 40–60 串、Dcard 30–50 篇，優先選有提到保養、維修、保固、外廠的。

## 4. 匯入並標註
```bash
python import_captures.py                                              # → data/forum_manual.jsonl
python label_with_gemini.py --inp data/forum_manual.jsonl --out data/labels.jsonl   # 只會標新的
python categorize.py apply && python analyze.py
```
注意：`analyze.py` 圖表註腳目前寫死「PTT 汽車版」，加入新來源後要改成依 `source` 分列。
