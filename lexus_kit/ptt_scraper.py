"""
PTT 爬蟲：抓 PTT 汽車版（car）中與 Lexus 相關的文章與推文。

用法：
    python ptt_scraper.py --since 2023-10-01 --out data/ptt_lexus.jsonl

特性：
- 用 PTT 站內搜尋，多個關鍵字（品牌名、車型）
- 每篇文章抓：標題、作者、時間、內文、所有推文
- 可中斷後續跑：已抓過的網址會跳過
- 每次請求間隔約 0.8 秒，請勿調太快
"""
import argparse
import json
import os
import random
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE = "https://www.ptt.cc"
HEADERS = {"User-Agent": "Mozilla/5.0 (research project; Lexus aftersales study)"}
COOKIES = {"over18": "1"}

# 搜尋關鍵字：品牌 + 常見車型。車型關鍵字抓回來後，會再用 LEXUS_PATTERN 過濾一次。
QUERIES = [
    # 售後關鍵字放最前面：標題沒寫 Lexus 的保養文，會靠下面的 LEXUS_PATTERN 檢查內文與推文
    "保養", "維修", "保固", "原廠", "外廠", "異音", "待料", "召回", "電瓶", "服務廠",
    "北都", "國都",
    "Lexus", "LEXUS", "凌志", "雷克薩斯",
    "ES200", "ES250", "ES300h",
    "NX200", "NX250", "NX300", "NX350h", "NX450h",
    "RX300", "RX350", "RX450h", "RX500h",
    "UX200", "UX250h", "UX300h",
    "IS300", "LBX", "LM300h", "LM350h",
]
# Lexus 判斷規則：
# 1. 品牌名（不分大小寫）：lexus、凌志、雷克薩斯、LBX
# 2. 車型帶數字：ES300h、NX 350h、RZ450e（可以緊貼中文字）
# 3. 車型不帶數字但必須大寫且單獨出現：「我的NX保固」「開ES的」。
#    後面不能接 - 或數字，避免 Mazda RX-7、RX8；英文小寫的 is、es 不會誤判
LEXUS_PATTERN = re.compile(
    r"(?i:lexus|凌志|雷克薩斯|lbx)"
    r"|(?<![A-Za-z])(ES|NX|RX|UX|IS|LS|LM|GX|LX|RZ|RC)\s?\d{3}[hHe]?(?![A-Za-z0-9])"
    r"|(?<![A-Za-z0-9-])(ES|NX|RX|UX|LM|GX|LX|RZ)(?![A-Za-z0-9-])"
)


def mentions_lexus(art, min_comment_hits=2):
    """標題或內文提到 Lexus；或至少 2 則推文提到（例如 Toyota 保養文底下 Lexus 車主的經驗）。"""
    if LEXUS_PATTERN.search(art["title"] + "\n" + art["content"]):
        return "body"
    hits = sum(1 for c in art["comments"] if LEXUS_PATTERN.search(c["content"]))
    return "comments" if hits >= min_comment_hits else None


def get(url, session, tries=4):
    for i in range(tries):
        try:
            r = session.get(url, headers=HEADERS, cookies=COOKIES, timeout=20)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(0.6 + random.random() * 0.4)
            return r.text
        except requests.RequestException as e:
            wait = 2 ** i
            print(f"  ! {e} -> retry in {wait}s")
            time.sleep(wait)
    return None


def parse_search_page(html):
    """回傳 [(標題, 文章網址)]，以及是否還有下一頁。"""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for ent in soup.select("div.r-ent"):
        a = ent.select_one("div.title a")
        if not a:  # 已刪除的文章沒有連結
            continue
        items.append((a.get_text(strip=True), BASE + a["href"]))
    has_prev = any(
        "上頁" in a.get_text() and "disabled" not in (a.get("class") or [])
        for a in soup.select("div.btn-group-paging a")
    )
    return items, has_prev


def parse_article(html, url):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("#main-content")
    if main is None:
        return None

    meta = {}
    for m in main.select("div.article-metaline, div.article-metaline-right"):
        tag = m.select_one(".article-meta-tag")
        val = m.select_one(".article-meta-value")
        if tag and val:
            meta[tag.get_text(strip=True)] = val.get_text(strip=True)

    comments = []
    for p in main.select("div.push"):
        tag = p.select_one(".push-tag")
        user = p.select_one(".push-userid")
        content = p.select_one(".push-content")
        t = p.select_one(".push-ipdatetime")
        if not (tag and user and content):
            continue
        comments.append({
            "tag": tag.get_text(strip=True),          # 推 / 噓 / →
            "user": user.get_text(strip=True),
            "content": content.get_text(strip=True).lstrip(":").strip(),
            "time": t.get_text(strip=True) if t else "",
        })

    # 內文 = 去掉 meta 與推文後的文字，並切掉簽名檔之後的系統訊息
    for el in main.select("div.article-metaline, div.article-metaline-right, div.push"):
        el.decompose()
    body = main.get_text("\n")
    body = body.split("\n--\n")[0].split("※ 發信站")[0].strip()

    published = None
    if "時間" in meta:
        try:
            published = datetime.strptime(meta["時間"], "%a %b %d %H:%M:%S %Y").isoformat()
        except ValueError:
            published = None

    return {
        "id": "ptt_" + url.removesuffix(".html").split("/")[-1],
        "source": "PTT",
        "board": url.split("/bbs/")[1].split("/")[0],
        "url": url,
        "title": meta.get("標題", ""),
        "author": meta.get("作者", ""),
        "published": published,
        "content": body,
        "comments": comments,
    }


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["url"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="car")
    ap.add_argument("--since", default="2023-10-01", help="只保留這天之後的文章")
    ap.add_argument("--out", default="data/ptt_lexus.jsonl")
    ap.add_argument("--max-pages", type=int, default=500, help="每個關鍵字最多翻幾頁搜尋結果")
    args = ap.parse_args()

    since = datetime.fromisoformat(args.since)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    done = load_done(args.out)
    print(f"已抓過 {len(done)} 篇，接續執行")

    session = requests.Session()
    with open(args.out, "a", encoding="utf-8") as out:
        for q in QUERIES:
            print(f"== 搜尋：{q}")
            old_streak = 0
            for page in range(1, args.max_pages + 1):
                html = get(f"{BASE}/bbs/{args.board}/search?page={page}&q={q}", session)
                if not html:
                    break
                items, has_prev = parse_search_page(html)
                if not items:
                    break
                for title, url in items:
                    if url in done:
                        continue
                    art_html = get(url, session)
                    if not art_html:
                        continue
                    art = parse_article(art_html, url)
                    if not art:
                        continue
                    done.add(url)
                    # 時間過濾：連續 30 篇都太舊就換下一個關鍵字
                    if art["published"] and datetime.fromisoformat(art["published"]) < since:
                        old_streak += 1
                        continue
                    old_streak = 0
                    where = mentions_lexus(art)
                    if not where:
                        continue
                    art["found_by_query"] = q
                    art["lexus_mentioned_in"] = where  # body = 標題或內文；comments = 只在推文
                    out.write(json.dumps(art, ensure_ascii=False) + "\n")
                    out.flush()
                    print(f"  + {art['published'][:10] if art['published'] else '????'} {title[:40]}")
                if old_streak >= 30 or not has_prev:
                    break


if __name__ == "__main__":
    main()
