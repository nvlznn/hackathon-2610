"""
統計分析：把標註＋歸類後的資料，變成報告要用的表格、圖表和重點數字。

用法：
    python analyze.py --inp data/labels_categorized.jsonl --out out

產出（都在 out/ 資料夾）：
    summary.md                 重點數字一覽（先看這個）
    01_pain_by_location.csv    各類不滿：原廠 vs 外廠
    02_churn_drivers.csv       哪類不滿最常伴隨「猶豫／已轉外廠」
    03_comment_voices.csv      推文中說離開原廠的原因
    04_risk_by_age.csv         各車齡層的流失傾向
    05_risk_by_segment.csv     依車型、新車或二手的流失傾向
    06_monthly.csv             每月討論量與負面比例
    07_quotes.csv              每類不滿的代表性原文（給簡報引用）
    08_persona_candidates.csv  Persona 候選組合（車齡 × 購車方式 × 主要不滿）
    chart_*.png                簡報用圖表
"""
import argparse
import json
import os
import re
from collections import Counter

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 圖表樣式 ----
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
import logging
from matplotlib import font_manager
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
_CJK = ["Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC", "Noto Sans CJK JP", "Heiti TC",
        "Microsoft YaHei", "Arial Unicode MS"]
_have = {f.name for f in font_manager.fontManager.ttflist}
_fonts = [f for f in _CJK if f in _have] or ["sans-serif"]
if _fonts == ["sans-serif"]:
    print("提醒：找不到中文字型，圖表中文可能顯示成方塊")
plt.rcParams.update({
    "font.family": _fonts,
    "axes.unicode_minus": False,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
})

OWNERS = {"現任車主", "前車主"}
AT_RISK = {"猶豫", "已轉外廠"}
MODEL_FAMILY = re.compile(r"^(LBX|ES|NX|RX|UX|IS|LS|LM|GX|LX|RZ|RC|CT|GS)", re.I)
MIN_N = 5  # 樣本數小於這個的組別不下結論



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

def load(path):
    rows = _read_jsonl(path)
    df = pd.DataFrame(rows)
    for col in ["pain_points_cat", "churn_reasons_cat", "comment_churn_reasons_cat",
                "car_models", "alternatives", "pain_points", "churn_reasons"]:
        if col not in df:
            df[col] = [[] for _ in range(len(df))]
        df[col] = df[col].apply(lambda v: v if isinstance(v, list) else [])
    for col in ["comments_churned", "comments_loyal"]:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0).astype(int)
    df["published"] = pd.to_datetime(df.get("published"), errors="coerce")
    df["owner"] = df["speaker"].isin(OWNERS)
    df["at_risk"] = df["stance_to_dealer"].isin(AT_RISK)
    df["all_cats"] = df.apply(lambda r: sorted(set(r["pain_points_cat"]) | set(r["churn_reasons_cat"])), axis=1)
    df["family"] = df["car_models"].apply(family)
    df["age_band"] = df["car_age_years"].apply(age_band)
    return df


def family(models):
    fams = [m.group(1).upper() for x in models if (m := MODEL_FAMILY.match(str(x).replace(" ", "")))]
    return Counter(fams).most_common(1)[0][0] if fams else "不明"


def age_band(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "不明"
    if pd.isna(v):
        return "不明"
    return "0–3 年" if v < 3 else "3–5 年" if v < 5 else "5–10 年" if v < 10 else "10 年以上"


def explode_counts(series):
    c = Counter(x for lst in series for x in lst)
    return pd.Series(c, dtype=int).sort_values(ascending=False)


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def save_bar_h(df, value_col, label_col, path, title, xlabel, color=BLUE, note=None, ref=None, ref_label=None):
    d = df.sort_values(value_col)
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(d) + 1.4))
    bars = ax.barh(d[label_col], d[value_col], color=color, height=0.6)
    for b, v in zip(bars, d[value_col]):
        ax.text(b.get_width(), b.get_y() + b.get_height() / 2, f" {v:g}", va="center", color=INK2, fontsize=10)
    if ref is not None:
        ax.axvline(ref, color=INK2, linestyle="--", linewidth=1)
        note = f"虛線：{ref_label}" + (f"；{note}" if note else "")
    ax.set_title(title, loc="left", color=INK, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if note:
        fig.text(0.01, 0.01, note, color=MUTED, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", default="data/labels_categorized.jsonl")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    O = lambda name: os.path.join(args.out, name)

    df = load(args.inp)
    rel = df[df["relevant"] == True]
    owners = rel[rel["owner"]]
    lines = ["# Lexus 售後輿情分析重點", ""]

    # ---- 0. 總覽 ----
    lines += [
        "## 資料總覽",
        f"- 標註文章總數：{len(df)}",
        f"- 實質討論 Lexus 售後（relevant）：{len(rel)} 篇（{pct(len(rel), len(df))}%）",
        f"- 其中發文者為車主：{len(owners)} 篇",
        f"- 涉及經銷商信任問題：{int(df['dealer_trust_issue'].fillna(False).sum())} 篇",
        f"- 資料期間：{df['published'].min():%Y-%m-%d} 至 {df['published'].max():%Y-%m-%d}",
        "",
    ]

    # ---- 1. 不滿類別：原廠 vs 外廠 ----
    pain = []
    for loc in ["原廠", "外廠"]:
        sub = rel[rel["experience_at"].isin([loc, "兩者都有"])]
        for cat, n in explode_counts(sub["pain_points_cat"]).items():
            pain.append({"類別": cat, "地點": loc, "篇數": int(n)})
    pain_all = explode_counts(rel["pain_points_cat"])
    t1 = pd.DataFrame(pain).pivot_table(index="類別", columns="地點", values="篇數", fill_value=0) if pain else pd.DataFrame()
    t1["全部"] = pain_all.reindex(t1.index).fillna(0).astype(int) if len(t1) else []
    if len(t1):
        t1 = t1.sort_values("全部", ascending=False)
        t1.to_csv(O("01_pain_by_location.csv"), encoding="utf-8-sig")
        loc_counts = rel["experience_at"].value_counts()
        lines += ["## 最常見的不滿（全部相關文章）"]
        lines += [f"- {c}：{int(n)} 篇" for c, n in pain_all.head(6).items()]
        lines += [f"- 經驗發生地點：" + "、".join(f"{k} {v} 篇" for k, v in loc_counts.items()), ""]
        if "原廠" in t1:
            d = t1.reset_index()[["類別", "原廠"]].rename(columns={"原廠": "篇數"})
            d = d[(d["篇數"] > 0) & (d["類別"] != "其他")]
            save_bar_h(d, "篇數", "類別", O("chart_1_pain_at_dealer.png"),
                       "原廠保養維修：車主最常抱怨什麼", "提及篇數",
                       note=f"資料：PTT 汽車版，經驗發生在原廠的相關文章 n={int(loc_counts.get('原廠', 0) + loc_counts.get('兩者都有', 0))}")

    # ---- 2. 流失驅動因素 ----
    base = owners
    risk_rate = base["at_risk"].mean() if len(base) else 0
    drv = []
    for cat in sorted({c for lst in base["all_cats"] for c in lst}):
        has = base[base["all_cats"].apply(lambda l: cat in l)]
        if len(has) == 0:
            continue
        r = has["at_risk"].mean()
        drv.append({"類別": cat, "提到的車主篇數": len(has), "其中猶豫或已轉外廠": int(has["at_risk"].sum()),
                    "流失傾向比例%": round(100 * r, 1),
                    "相對整體倍數": round(r / risk_rate, 2) if risk_rate else None,
                    "樣本足夠": len(has) >= MIN_N})
    t2 = pd.DataFrame(drv)
    if len(t2):
        t2 = t2.sort_values(["樣本足夠", "流失傾向比例%"], ascending=False)
        t2.to_csv(O("02_churn_drivers.csv"), index=False, encoding="utf-8-sig")
        lines += ["## 流失驅動因素（車主發文）",
                  f"- 車主發文中，猶豫或已轉外廠的比例：{pct(base['at_risk'].sum(), len(base))}%（{int(base['at_risk'].sum())}/{len(base)}）"]
        ok = t2[t2["樣本足夠"]]
        lines += [f"- {r['類別']}：{r['流失傾向比例%']}% 伴隨流失傾向（{r['其中猶豫或已轉外廠']}/{r['提到的車主篇數']}），為整體的 {r['相對整體倍數']} 倍"
                  for _, r in ok.head(5).iterrows()]
        lines += [f"- 註：提及少於 {MIN_N} 篇的類別不下結論", ""]
        ok_chart = ok[ok["類別"] != "其他"]
        if len(ok_chart):
            save_bar_h(ok_chart, "流失傾向比例%", "類別", O("chart_2_churn_drivers.png"),
                       "提到這類不滿的車主，多少已在猶豫或離開原廠", "伴隨流失傾向的比例（%）",
                       note=f"僅列提及 ≥{MIN_N} 篇的類別；資料：PTT 汽車版車主發文",
                       ref=round(100 * risk_rate, 1), ref_label=f"全體車主平均 {round(100 * risk_rate, 1)}%")

    # ---- 3. 推文心聲 ----
    churned, loyal = int(df["comments_churned"].sum()), int(df["comments_loyal"].sum())
    t3 = explode_counts(df["comment_churn_reasons_cat"]).rename("提及篇數")
    t3.to_csv(O("03_comment_voices.csv"), encoding="utf-8-sig", header=True)
    lines += ["## 推文中的車主心聲",
              f"- 推文自述「已改去外廠」：{churned} 則；自述「一直回原廠」：{loyal} 則",
              "- 推文中離開原廠的原因：" + "、".join(f"{k} {v}" for k, v in t3.head(5).items()), ""]

    # ---- 4. 車齡 ----
    order = ["0–3 年", "3–5 年", "5–10 年", "10 年以上", "不明"]
    t4 = owners.groupby("age_band").agg(車主篇數=("id", "size"), 猶豫或已轉外廠=("at_risk", "sum")).reindex(order).dropna()
    t4["流失傾向比例%"] = (100 * t4["猶豫或已轉外廠"] / t4["車主篇數"]).round(1)
    t4.to_csv(O("04_risk_by_age.csv"), encoding="utf-8-sig")
    known = t4.drop(index="不明", errors="ignore")
    known = known[known["車主篇數"] >= MIN_N]
    if len(known):
        d = known.reset_index().rename(columns={"age_band": "車齡"})
        fig, ax = plt.subplots(figsize=(7, 3.8))
        bars = ax.bar(d["車齡"], d["流失傾向比例%"], color=BLUE, width=0.55)
        for b, v, n in zip(bars, d["流失傾向比例%"], d["車主篇數"]):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:g}%\nn={n}", ha="center", va="bottom", color=INK2, fontsize=10)
        ax.set_title("各車齡車主中，猶豫或已轉外廠的比例", loc="left", color=INK, fontsize=13, fontweight="bold")
        ax.set_ylabel("比例（%）")
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_ylim(0, max(d["流失傾向比例%"].max() * 1.3, 10))
        fig.tight_layout()
        fig.savefig(O("chart_3_risk_by_age.png"), dpi=200)
        plt.close(fig)
    lines += ["## 車齡與流失傾向（車主發文，僅列車齡可判斷者）"]
    lines += [f"- {i}：{r['流失傾向比例%']}%（{int(r['猶豫或已轉外廠'])}/{int(r['車主篇數'])}）" for i, r in t4.iterrows()]
    lines += [""]

    # ---- 5. 車型、新車或二手 ----
    seg = []
    for col, name in [("family", "車型"), ("purchase_type", "購車方式")]:
        g = owners.groupby(col).agg(車主篇數=("id", "size"), 猶豫或已轉外廠=("at_risk", "sum")).reset_index()
        g.insert(0, "維度", name)
        g = g.rename(columns={col: "組別"})
        seg.append(g)
    t5 = pd.concat(seg)
    t5["流失傾向比例%"] = (100 * t5["猶豫或已轉外廠"] / t5["車主篇數"]).round(1)
    t5["樣本足夠"] = t5["車主篇數"] >= MIN_N
    t5.to_csv(O("05_risk_by_segment.csv"), index=False, encoding="utf-8-sig")
    pt = t5[(t5["維度"] == "購車方式") & (t5["組別"].isin(["新車", "二手"])) & t5["樣本足夠"]]
    if len(pt) == 2:
        pt = pt.set_index("組別").loc[["新車", "二手"]].reset_index()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        bars = ax.bar(pt["組別"], pt["流失傾向比例%"], color=BLUE, width=0.5)
        for b, v, n in zip(bars, pt["流失傾向比例%"], pt["車主篇數"]):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:g}%\nn={n}", ha="center", va="bottom", color=INK2, fontsize=10)
        ax.set_title("新車 vs 二手車主：猶豫或已轉外廠的比例", loc="left", color=INK, fontsize=13, fontweight="bold")
        ax.set_ylabel("比例（%）")
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_ylim(0, max(pt["流失傾向比例%"].max() * 1.35, 10))
        fig.tight_layout()
        fig.savefig(O("chart_5_new_vs_used.png"), dpi=200)
        plt.close(fig)
        lines.extend(["## 購車方式與流失傾向"] + [f"- {r['組別']}：{r['流失傾向比例%']}%（{int(r['猶豫或已轉外廠'])}/{int(r['車主篇數'])}）" for _, r in pt.iterrows()] + [""])

    # ---- 6. 每月趨勢 ----
    m = rel.dropna(subset=["published"]).copy()
    m["月份"] = m["published"].dt.to_period("M").astype(str)
    t6 = m.groupby("月份").agg(相關篇數=("id", "size"), 負面篇數=("sentiment", lambda s: (s == "負面").sum()))
    trust = df.dropna(subset=["published"]).copy()
    trust["月份"] = trust["published"].dt.to_period("M").astype(str)
    t6 = t6.join(trust[trust["dealer_trust_issue"] == True].groupby("月份").size().rename("經銷商信任篇數"), how="outer").fillna(0).astype(int)
    t6["負面比例%"] = (100 * t6["負面篇數"] / t6["相關篇數"].where(t6["相關篇數"] > 0)).astype(float).round(1)
    t6.to_csv(O("06_monthly.csv"), encoding="utf-8-sig")
    if len(t6) >= 3:
        q = t6.copy()
        q.index = pd.PeriodIndex(q.index, freq="M")
        q = q.resample("Q").sum(numeric_only=True)
        fig, ax = plt.subplots(figsize=(8, 3.6))
        ax.plot(q.index.astype(str), q["相關篇數"], color=BLUE, linewidth=2, marker="o", markersize=5)
        ax.set_title("每季 Lexus 售後相關討論篇數", loc="left", color=INK, fontsize=13, fontweight="bold")
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_ylim(bottom=0)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        fig.tight_layout()
        fig.savefig(O("chart_4_quarterly.png"), dpi=200)
        plt.close(fig)

    # ---- 7. 代表性原文 ----
    qs = []
    for cat in pain_all.index:
        sub = rel[rel["all_cats"].apply(lambda l: cat in l)].sort_values("n_comments", ascending=False)
        for _, r in sub.head(5).iterrows():
            qs.append({"類別": cat, "原文": r.get("evidence_quote", ""), "標題": r.get("title", ""),
                       "立場": r.get("stance_to_dealer", ""), "地點": r.get("experience_at", ""),
                       "推文數": r.get("n_comments", 0), "連結": r.get("url", "")})
    pd.DataFrame(qs).to_csv(O("07_quotes.csv"), index=False, encoding="utf-8-sig")

    # ---- 8. Persona 候選 ----
    p = owners.copy()
    p["主要不滿"] = p["all_cats"].apply(lambda l: l[0] if l else "未提及")
    t8 = p.groupby(["age_band", "purchase_type", "主要不滿"]).agg(
        車主篇數=("id", "size"), 猶豫或已轉外廠=("at_risk", "sum"),
        常見車型=("family", lambda s: "、".join(f"{k}({v})" for k, v in Counter(s).most_common(3)))).reset_index()
    t8["流失傾向比例%"] = (100 * t8["猶豫或已轉外廠"] / t8["車主篇數"]).round(1)
    t8 = t8.rename(columns={"age_band": "車齡", "purchase_type": "購車方式"}).sort_values(["車主篇數", "流失傾向比例%"], ascending=False)
    t8.to_csv(O("08_persona_candidates.csv"), index=False, encoding="utf-8-sig")
    lines += ["## 下一步",
              "- 打開 08_persona_candidates.csv，挑出篇數夠多、流失傾向高的組合，作為 Persona 的基礎",
              "- 打開 07_quotes.csv，為每個 Persona 挑 1–2 句代表性原文",
              f"- 樣本數小於 {MIN_N} 的數字只當參考，不要在簡報下結論"]

    open(O("summary.md"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    print(f"\n全部結果在 {args.out}/ 資料夾")


if __name__ == "__main__":
    main()
