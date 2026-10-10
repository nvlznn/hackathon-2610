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

建立 Gemini 與 Codex 分歧表：
    python check_label_quality.py disagree --labels data/labels.jsonl --codex data/codex_labels.csv --out data/disagreements.csv
"""
import argparse
from datetime import date
import json
from pathlib import Path

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
    sheet = _read_csv_fallback(args.sheet)
    ai = pd.DataFrame(_read_jsonl(args.labels))
    m = sheet.merge(ai, on="id", suffixes=("", "_ai"))
    m["ai_relevant"] = m["relevant"].map({True: "是", False: "否"})
    pairs = [("human_relevant", "ai_relevant", "是否相關"),
             ("human_sentiment", "sentiment", "情緒"),
             ("human_stance", "stance_to_dealer", "對原廠立場")]
    # Preserve the original score output exactly when no extended option is used.
    if not any((args.codex, args.disagree, args.md)):
        for h, a, name in pairs:
            sub = m[m[h].notna() & (m[h].astype(str).str.strip() != "")]
            if len(sub) == 0:
                continue
            acc = (sub[h].astype(str).str.strip() == sub[a].astype(str).str.strip()).mean()
            print(f"{name}：{len(sub)} 筆，一致率 {acc:.0%}")
            print(pd.crosstab(sub[h], sub[a], rownames=["人工"], colnames=["AI"]), "\n")
        return

    codex = _load_codex(args.codex) if args.codex else None
    all_m = m
    if codex is not None:
        all_m = m.merge(codex, on="id", how="inner")
        all_m["codex_relevant"] = all_m["relevant_codex"].map({"是": "是", "否": "否", "true": "是", "false": "否"})
        all_m["codex_sentiment"] = all_m["sentiment_codex"]
        all_m["codex_stance"] = all_m["stance"]
    report_rows = []
    for h, a, name in pairs:
        sub = m[m[h].notna() & (m[h].astype(str).str.strip() != "")]
        gi = _accuracy(sub, h, a)
        print(f"{name} Gemini vs 人工：{_pct_n(gi)}")
        report_rows.append((name, "Gemini vs 人工", gi))
        if codex is not None:
            cs = all_m[all_m[h].notna() & (all_m[h].astype(str).str.strip() != "")]
            ci = _accuracy(cs, h, "codex_" + ("relevant" if name == "是否相關" else "sentiment" if name == "情緒" else "stance"))
            ga = _accuracy(all_m, a, "codex_" + ("relevant" if name == "是否相關" else "sentiment" if name == "情緒" else "stance"))
            print(f"{name} Codex vs 人工：{_pct_n(ci)}")
            print(f"{name} Gemini vs Codex：{_pct_n(ga)}")
            report_rows.extend([(name, "Codex vs 人工", ci), (name, "Gemini vs Codex", ga)])
        if len(sub):
            print(pd.crosstab(sub[h], sub[a], rownames=["人工"], colnames=["Gemini"]), "\n")

    adjudication = _adjudication_stats(args.disagree) if args.disagree else None
    if adjudication is not None:
        for field, counts in adjudication.items():
            print(f"{field} 裁決：與 Gemini 相同 {counts[0]}、與 Codex 相同 {counts[1]}、兩者皆不同 {counts[2]}")
    if args.md:
        _write_report(args.md, args, pairs, report_rows, m, adjudication, codex)


def _read_csv_fallback(path):
    try:
        return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp950", keep_default_na=False)


def _load_codex(path):
    df = _read_csv_fallback(path)
    df = df.rename(columns={"relevant": "relevant_codex", "sentiment": "sentiment_codex"})
    return df


def _clean(series):
    return series.astype(str).str.strip()


def _accuracy(df, left, right):
    if len(df) == 0:
        return (None, 0)
    return ((_clean(df[left]) == _clean(df[right])).mean(), len(df))


def _pct_n(result):
    return "無資料（n=0）" if result[0] is None else f"{result[0]:.0%}（n={result[1]}）"


FIELDS = [("是否相關", "relevant", "relevant_codex", "adjudicated_relevant"),
          ("情緒", "sentiment", "sentiment_codex", "adjudicated_sentiment"),
          ("對原廠立場", "stance_to_dealer", "stance", "adjudicated_stance")]


def disagree(args):
    out = Path(args.out)
    if out.exists():
        existing = _read_csv_fallback(out)
        adjudicated = [c for c in existing.columns if c.startswith("adjudicated_")]
        if adjudicated and existing[adjudicated].apply(lambda col: col.astype(str).str.strip().ne("")).any().any():
            print(f"警告：{out} 含有已填寫的裁決欄位，為保護人工裁決不予覆蓋。")
            return
    gemini = pd.DataFrame(_read_jsonl(args.labels))
    codex = _load_codex(args.codex)
    # Codex is the authoritative row set; preserve its ordering.
    joined = codex.merge(gemini, on="id", how="left", suffixes=("_codex", "_gemini"))
    rows, counts = [], {name: 0 for name, *_ in FIELDS}
    for _, row in joined.iterrows():
        gr_val = row.get("relevant_gemini", row.get("relevant"))
        gr = "是" if gr_val is True else "否" if gr_val is False else ""
        vals = [gr, row.get("sentiment_gemini", row.get("sentiment", "")), row.get("stance_to_dealer_gemini", row.get("stance_to_dealer", ""))]
        cvs = [row.get("relevant_codex", ""), row.get("sentiment_codex", ""), row.get("stance", "")]
        diffs = [name for (name, *_), x, y in zip(FIELDS, vals, cvs) if str(x).strip() != str(y).strip()]
        if not diffs:
            continue
        for name in diffs:
            counts[name] += 1
        rows.append({"id": row["id"], "url": row.get("url", ""), "title": row.get("title", ""),
                     "diff_fields": "、".join(diffs), "gemini_relevant": gr,
                     "codex_relevant": cvs[0], "gemini_sentiment": vals[1], "codex_sentiment": cvs[1],
                     "gemini_stance": vals[2], "codex_stance": cvs[2], "codex_note": row.get("note", ""),
                     "adjudicated_relevant": "", "adjudicated_sentiment": "", "adjudicated_stance": ""})
    columns = ["id", "url", "title", "diff_fields", "gemini_relevant", "codex_relevant", "gemini_sentiment", "codex_sentiment", "gemini_stance", "codex_stance", "codex_note", "adjudicated_relevant", "adjudicated_sentiment", "adjudicated_stance"]
    pd.DataFrame(rows, columns=columns).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"分歧列數：{len(rows)}")
    for name, n in counts.items():
        print(f"{name} 分歧數：{n}")


def _adjudication_stats(path):
    d = _read_csv_fallback(path)
    stats = {}
    for name, gcol, ccol, acol in [("是否相關", "gemini_relevant", "codex_relevant", "adjudicated_relevant"),
                                    ("情緒", "gemini_sentiment", "codex_sentiment", "adjudicated_sentiment"),
                                    ("對原廠立場", "gemini_stance", "codex_stance", "adjudicated_stance")]:
        if acol not in d: continue
        # 只統計這個欄位真的有分歧的列；兩者一致的列裁決必然同時等於兩邊，不該重複計入
        sub = d[(d[acol].astype(str).str.strip() != "") & (_clean(d[gcol]) != _clean(d[ccol]))]
        g, c, a = _clean(sub[gcol]), _clean(sub[ccol]), _clean(sub[acol])
        stats[name] = (int((a == g).sum()), int((a == c).sum()), int(((a != g) & (a != c)).sum()))
    return stats


def _write_report(path, args, pairs, rows, scored, adjudication, codex):
    lines = ["# 標註品質報告", "", f"產生日期：{date.today().isoformat()}", "",
             "## 資料說明", "", f"- Gemini：`{args.labels}`（全部 {len(_read_jsonl(args.labels))} 篇，本報告只比對下列 {len(scored)} 篇）",
             f"- 人工：`{args.sheet}`，n={len(scored)}"]
    if codex is not None: lines.append(f"- Codex：`{args.codex}`，n={len(codex)}")
    lines += ["", "## 三組一致率", "", "| 欄位 | 比較組 | 一致率 |", "|---|---|---|"]
    lines += [f"| {field} | {group} | {_pct_n(result)} |" for field, group, result in rows]
    lines += ["", "## Gemini vs 人工混淆表", ""]
    for h, a, name in pairs:
        sub = scored[scored[h].astype(str).str.strip() != ""]
        table = pd.crosstab(sub[h], sub[a], rownames=["人工"], colnames=["Gemini"])
        headers = ["人工"] + [str(c) for c in table.columns]
        md_table = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        md_table += ["| " + " | ".join([str(idx)] + [str(v) for v in vals]) + " |" for idx, vals in table.iterrows()]
        lines += [f"### {name}", "", "\n".join(md_table), ""]
    if adjudication is not None:
        lines += ["## 分歧裁決統計", "", "| 欄位 | 與 Gemini 相同 | 與 Codex 相同 | 兩者皆不同 |", "|---|---:|---:|---:|"]
        lines += [f"| {field} | {v[0]} | {v[1]} | {v[2]} |" for field, v in adjudication.items()]
    # 保留報告中 <!-- manual --> 以下的人工撰寫段落，重跑時不覆蓋
    out, manual = Path(path), ""
    if out.exists():
        old = out.read_text(encoding="utf-8")
        if MANUAL_MARK in old:
            manual = "\n" + old[old.index(MANUAL_MARK):]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n" + manual, encoding="utf-8")


MANUAL_MARK = "<!-- manual -->"


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
    s2.add_argument("--codex")
    s2.add_argument("--disagree")
    s2.add_argument("--md")
    s3 = sp.add_parser("disagree")
    s3.add_argument("--labels", default="data/labels.jsonl")
    s3.add_argument("--codex", default="data/codex_labels.csv")
    s3.add_argument("--out", default="data/disagreements.csv")
    args = ap.parse_args()
    if args.cmd == "sample": sample(args)
    elif args.cmd == "disagree": disagree(args)
    else: score(args)
