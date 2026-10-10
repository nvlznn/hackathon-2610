"""把書籤存下的 Mobile01／Dcard 頁面合併成和 data/ptt_lexus.jsonl 相同的格式。

用法：
    python import_captures.py                 # 讀 ~/Downloads/lexus_cap_*.json → data/forum_manual.jsonl
    python import_captures.py --queue         # 另外產生 collector/queue.html（列表頁存下、但還沒讀的文章）

之後接回原本流程（標註會自動跳過已標過的 id）：
    python label_with_gemini.py --inp data/forum_manual.jsonl --out data/labels.jsonl
    python categorize.py apply && python analyze.py
"""
import argparse
import glob
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))


def load(pattern):
    out = []
    for f in sorted(glob.glob(pattern)):
        try:
            with open(f, encoding="utf-8") as fh:
                out.append(json.load(fh))
        except (json.JSONDecodeError, OSError) as e:
            print(f"跳過壞檔 {os.path.basename(f)}：{e}")
    return out


def iso_tpe(utc_iso):
    if not utc_iso:
        return ""
    dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
    return dt.astimezone(TPE).strftime("%Y-%m-%dT%H:%M:%S")


def m01_iso(s):
    return s.replace(" ", "T") + ":00" if s else ""


def build_mobile01(caps):
    threads = {}
    for c in caps:
        t = threads.setdefault(c["thread"], {"meta": c, "posts": {}, "pages": set()})
        t["pages"].add(c["page"])
        if c["page"] == 1:
            t["meta"] = c
        for p in c["posts"]:
            t["posts"][p["aid"]] = p
    rows, warn = [], []
    for tid, t in threads.items():
        posts = sorted(t["posts"].values(), key=lambda p: (p["floor"] is None, p["floor"] or 0))
        main = posts[0] if posts and posts[0].get("floor") == 1 else None
        if main is None:
            warn.append(f"Mobile01 t={tid} 缺第 1 頁（主文）")
        rest = posts[1:] if main else posts
        meta = t["meta"]
        rows.append({
            "id": f"m01_{tid}", "source": "Mobile01", "board": meta.get("board") or "",
            "url": f"https://www.mobile01.com/topicdetail.php?f={meta.get('board')}&t={tid}",
            "title": meta["title"], "author": (main or {}).get("user", ""),
            "published": m01_iso((main or {}).get("time", "")),
            "content": (main or {}).get("content", ""),
            "comments": [{"tag": "回覆", "user": p["user"], "content": p["content"], "time": p["time"]} for p in rest],
            "pages_captured": sorted(t["pages"]),
        })
    return rows, warn


def build_dcard(caps):
    best = {}
    for c in caps:
        if c["id"] not in best or len(c["comments"]) > len(best[c["id"]]["comments"]):
            best[c["id"]] = c
    return [{
        "id": f"dcard_{c['id']}", "source": "Dcard", "board": c.get("board") or "",
        "url": c["url"], "title": c["title"], "author": "", "published": iso_tpe(c.get("published")),
        "content": c["content"],
        "comments": [{"tag": "留言", "user": "", "content": x["content"], "time": iso_tpe(x["time"])} for x in c["comments"]],
    } for c in best.values()]


def write_queue(src, done_urls, path):
    items = {}
    for q in load(os.path.join(src, "lexus_queue_*.json")):
        for it in q["items"]:
            items.setdefault(it["url"], (q["site"], it["title"]))
    todo = [(u, s, t) for u, (s, t) in items.items() if u not in done_urls]
    lis = "\n".join(
        f'<li><a href="{html.escape(u)}" target="_blank" rel="noopener">[{s}] {html.escape(t)}</a></li>' for u, s, t in todo)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset='utf-8'><title>待讀清單</title>"
                f"<style>body{{font:15px sans-serif;max-width:860px;margin:24px auto;padding:0 16px}}a:visited{{color:#999}}li{{margin:6px 0}}</style>"
                f"<h1>待讀清單（{len(todo)} 篇）</h1><p>點開 → 按書籤 → 關分頁。Mobile01 有多頁的串，每頁都要按。</p><ol>{lis}</ol>")
    print(f"待讀清單：{len(todo)} 篇 → {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.expanduser("~/Downloads"))
    ap.add_argument("--out", default="data/forum_manual.jsonl")
    ap.add_argument("--queue", action="store_true")
    args = ap.parse_args()

    caps = load(os.path.join(args.src, "lexus_cap_*.json"))
    m01, warn = build_mobile01([c for c in caps if c.get("site") == "Mobile01"])
    dcard = build_dcard([c for c in caps if c.get("site") == "Dcard"])
    rows = m01 + dcard
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_c = sum(len(r["comments"]) for r in rows)
    print(f"Mobile01 {len(m01)} 串、Dcard {len(dcard)} 篇、留言 {n_c} 則 → {args.out}")
    empty = [r["id"] for r in rows if not r["content"].strip()]
    for w in warn + [f"{i} 主文是空的" for i in empty]:
        print("注意：", w)
    if args.queue:
        done = set()
        for c in caps:
            u = c["url"].split("&p=")[0] if c.get("site") == "Mobile01" else c["url"]
            done.add(u)
        write_queue(args.src, done, "collector/queue.html")


if __name__ == "__main__":
    main()
