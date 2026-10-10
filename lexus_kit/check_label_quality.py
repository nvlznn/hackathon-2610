"""
檢查 AI 標註品質（簡報可寫：「AI 標註與人工一致率 XX%」）。

步驟 1：抽樣，產生給人工填寫的表格
    python check_label_quality.py sample --labels data/labels.jsonl --n 200

    → data/review_sheet.csv
      用 Excel / Google Sheets 打開，只填三個 human_ 欄位（不要先看 AI 的答案）：
        human_relevant      是 / 否
        human_sentiment     正面 / 中立 / 負面
        human_stance        忠誠 / 猶豫 / 已轉外廠 / 未提及

步驟 2：填完後計算一致率
    python check_label_quality.py score --sheet data/review_sheet.csv --labels data/labels.jsonl
"""
import argparse
import json

import pandas as pd



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

def sample(args):
    rows = _read_jsonl(args.labels)
    df = pd.DataFrame(rows).sample(n=min(args.n, len(rows)), random_state=42)
    sheet = df[["id", "url", "title", "summary"]].copy()
    sheet["human_relevant"] = ""
    sheet["human_sentiment"] = ""
    sheet["human_stance"] = ""
    sheet.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"已產生 {len(sheet)} 筆待人工標註：{args.out}")


def score(args):
    try:
        sheet = pd.read_csv(args.sheet, encoding="utf-8-sig")
    except UnicodeDecodeError:  # Excel 存成一般 CSV（Big5）時
        sheet = pd.read_csv(args.sheet, encoding="cp950")
    ai = pd.DataFrame(_read_jsonl(args.labels))
    m = sheet.merge(ai, on="id", suffixes=("", "_ai"))
    m["ai_relevant"] = m["relevant"].map({True: "是", False: "否"})
    pairs = [("human_relevant", "ai_relevant", "是否相關"),
             ("human_sentiment", "sentiment", "情緒"),
             ("human_stance", "stance_to_dealer", "對原廠立場")]
    for h, a, name in pairs:
        sub = m[m[h].notna() & (m[h].astype(str).str.strip() != "")]
        if len(sub) == 0:
            continue
        acc = (sub[h].astype(str).str.strip() == sub[a].astype(str).str.strip()).mean()
        print(f"{name}：{len(sub)} 筆，一致率 {acc:.0%}")
        print(pd.crosstab(sub[h], sub[a], rownames=["人工"], colnames=["AI"]), "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s1 = sp.add_parser("sample")
    s1.add_argument("--labels", default="data/labels.jsonl")
    s1.add_argument("--n", type=int, default=200)
    s1.add_argument("--out", default="data/review_sheet.csv")
    s2 = sp.add_parser("score")
    s2.add_argument("--sheet", default="data/review_sheet.csv")
    s2.add_argument("--labels", default="data/labels.jsonl")
    args = ap.parse_args()
    sample(args) if args.cmd == "sample" else score(args)
