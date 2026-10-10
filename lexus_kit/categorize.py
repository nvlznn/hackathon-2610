"""
把 AI 標註出來的「自由文字」不滿與流失原因，歸進固定的幾個大類，才能統計。

步驟 1：讓 Gemini 看過所有說法，建議怎麼分類（給 B 參考）
    python categorize.py suggest --labels data/labels.jsonl

步驟 2：B 打開 categories.json，增刪或改名大類（每類附一句說明）

步驟 3：把每一筆說法歸進大類，輸出加上分類欄位的新檔
    python categorize.py apply --labels data/labels.jsonl --out data/labels_categorized.jsonl

歸類結果會快取在 data/phrase_map.json：改了分類想重跑，刪掉這個檔再執行 apply。
"""
import argparse
import json
import os
import time
from collections import Counter
from typing import List

from google import genai
from google.genai import types
from pydantic import BaseModel

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
TEXT_FIELDS = ["pain_points", "churn_reasons", "comment_churn_reasons"]

DEFAULT_CATEGORIES = {
    "價格與收費": "保養維修太貴、價格不透明、被多收費、被當盤子",
    "等待與預約": "等太久、預約不到、進廠時間長",
    "零件與待料": "零件要等、待料久、缺料",
    "維修品質": "修不好、反覆進廠、維修出錯、技術不足",
    "說明與溝通": "說明不清楚、沒告知、溝通不良",
    "服務態度": "服務專員或人員態度差、不耐煩、推銷",
    "信任與誠信": "經銷商糾紛、不老實、不信任、誠信問題",
    "保固與權益": "保固不認、權益爭議、延長保固問題",
    "便利性": "據點太少太遠、時間不方便、沒有代步車",
    "其他": "無法歸入以上類別",
}



def _read_jsonl(path):
    """讀 jsonl，跳過寫到一半的行（標註程式還在跑時，最後一行可能不完整）。"""
    rows = []
    for l in open(path, encoding="utf-8"):
        if not l.strip():
            continue
        try:
            rows.append(json.loads(l))
        except json.JSONDecodeError:
            pass
    return rows

def load_labels(path):
    return _read_jsonl(path)


def all_phrases(rows):
    c = Counter()
    for r in rows:  # 包含不相關文章：它們的推文裡也可能有車主說離開原廠的原因
        for f in TEXT_FIELDS:
            for p in r.get(f) or []:
                p = p.strip()
                if p:
                    c[p] += 1
    return c


def call_json(client, prompt, schema, tries=6):
    for i in range(tries):
        try:
            resp = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema, temperature=0,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)))
            return json.loads(resp.text)
        except Exception as e:
            wait = 30 if "429" in str(e) else 5 * (2 ** i)
            print(f"  ! {str(e)[:120]} -> {wait}s 後重試")
            time.sleep(wait)
    raise RuntimeError("Gemini 呼叫多次失敗")


class Suggestion(BaseModel):
    name: str
    description: str
    examples: List[str]


def suggest(args):
    phrases = all_phrases(load_labels(args.labels))
    top = [p for p, _ in phrases.most_common(400)]
    print(f"共 {len(phrases)} 種不同說法，取最常見的 {len(top)} 種給 Gemini 建議分類")
    prompt = ("以下是車主對 Lexus 保養維修的不滿與離開原廠的原因（每行一則）。"
              "請建議 8 到 12 個互不重疊的大類，每類給名稱、一句說明、3 個例子。"
              "大類要對 Lexus 售後部門有行動意義。\n\n" + "\n".join(top))
    client = genai.Client()
    sugg = call_json(client, prompt, list[Suggestion])
    print("\n=== Gemini 建議的分類 ===")
    for s in sugg:
        print(f"\n【{s['name']}】{s['description']}\n  例：{'、'.join(s['examples'])}")
    if not os.path.exists(args.categories):
        json.dump(DEFAULT_CATEGORIES, open(args.categories, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n已建立預設分類檔 {args.categories}，請 B 參考上面的建議修改後再執行 apply")


class Mapping(BaseModel):
    phrase: str
    category: str


def apply(args):
    if not os.path.exists(args.categories):
        json.dump(DEFAULT_CATEGORIES, open(args.categories, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"找不到分類檔，已用預設分類建立 {args.categories}")
    cats = json.load(open(args.categories, encoding="utf-8"))
    names = list(cats)
    rows = load_labels(args.labels)
    phrases = list(all_phrases(rows))
    cache = json.load(open(args.cache, encoding="utf-8")) if os.path.exists(args.cache) else {}
    todo = [p for p in phrases if p not in cache]
    print(f"共 {len(phrases)} 種說法，已歸類 {len(phrases) - len(todo)}，本次歸類 {len(todo)}")

    cat_desc = "\n".join(f"- {k}：{v}" for k, v in cats.items())
    client = genai.Client() if todo else None
    for i in range(0, len(todo), 60):
        batch = todo[i:i + 60]
        prompt = (f"把每一則說法歸入最合適的一個大類，category 必須是下列名稱之一：\n{cat_desc}\n\n"
                  "說法（每行一則，phrase 請原樣照抄）：\n" + "\n".join(batch))
        result = call_json(client, prompt, list[Mapping])
        got = {m["phrase"]: m["category"] for m in result}
        for p in batch:
            c = got.get(p, "其他")
            cache[p] = c if c in names else "其他"
        json.dump(cache, open(args.cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  {min(i + 60, len(todo))}/{len(todo)}")
        time.sleep(4.5)  # 免費方案每分鐘 15 次

    with open(args.out, "w", encoding="utf-8") as out:
        for r in rows:
            for f in TEXT_FIELDS:
                r[f + "_cat"] = sorted({cache.get(p.strip(), "其他") for p in (r.get(f) or []) if p.strip()})
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"完成：{args.out}")
    dist = Counter(cache.values())
    print("各類別的說法數：", dict(dist.most_common()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ["suggest", "apply"]:
        s = sp.add_parser(name)
        s.add_argument("--labels", default="data/labels.jsonl")
        s.add_argument("--categories", default="categories.json")
        if name == "apply":
            s.add_argument("--out", default="data/labels_categorized.jsonl")
            s.add_argument("--cache", default="data/phrase_map.json")
    args = ap.parse_args()
    suggest(args) if args.cmd == "suggest" else apply(args)
