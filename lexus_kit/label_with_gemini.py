"""
用 Gemini 為每篇貼文（含推文）做結構化標註。

用法：
    export GEMINI_API_KEY=你的金鑰
    python label_with_gemini.py --inp data/ptt_lexus.jsonl --out data/labels.jsonl
    python label_with_gemini.py --inp data/ptt_lexus.jsonl --out data/labels.jsonl --limit 30   # 先試 30 篇

輸出：
    data/labels.jsonl  每篇一列，含所有標註欄位
    data/labels.csv    同上，攤平成表格，給企劃夥伴用 Excel / Google Sheets 看

可中斷後續跑：已標註的 id 會跳過。
"""
import argparse
import json
import os
import random
import re
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from enum import Enum
from typing import List, Optional

import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 模型名稱請以 Google AI Studio 當下可用的為準（Flash-Lite 便宜，適合大量標註）
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")


class Topic(str, Enum):
    service = "服務體驗"
    parts_warranty = "零件保修"
    price = "保養維修價格"
    waiting = "等待與預約"
    technician = "技師專業與說明"
    advisor = "服務顧問態度"
    loaner = "代步車"
    warranty_rights = "保固與車主權益"
    quality = "車輛品質問題"
    used_car = "二手與殘值"
    purchase = "購車與業務"
    dealer_trust = "經銷商信任與糾紛"
    other = "其他"


class Stance(str, Enum):
    loyal = "忠誠"          # 明確表示會留在原廠
    hesitant = "猶豫"       # 在比較、考慮離開
    churned = "已轉外廠"     # 已經改去其他地方保養維修
    none = "未提及"


class Alternative(str, Enum):
    indie = "外面保養廠"
    chain = "連鎖保養"
    aftermarket = "副廠零件"
    diy = "自行保養"
    other_brand = "換其他品牌"
    none = "無"


class Speaker(str, Enum):
    owner = "現任車主"
    ex_owner = "前車主"
    prospect = "潛在買家"
    other = "非車主或不明"


class Label(BaseModel):
    relevant: bool = Field(description="是否實質討論 Lexus 售後：保養、維修、零件、保固、服務廠、服務顧問、技師、代步車。只是一句帶過則為 false")
    dealer_trust_issue: bool = Field(description="是否涉及對經銷商或原廠體系的信任問題，例如糾紛、詐騙、處理態度、被當盤子")
    speaker: Speaker = Field(description="發文者身分")
    purchase_type: str = Field(description="發文者是車主時才判斷：新車、二手；否則填不明")
    car_models: List[str] = Field(description="提到的 Lexus 車型，例如 ES300h、NX350h；沒有則空陣列")
    car_age_years: Optional[float] = Field(description="車齡（年），文中看不出則為 null")
    mileage_km: Optional[int] = Field(description="里程數（公里），文中看不出則為 null")
    topics: List[Topic]
    sentiment: str = Field(description="對 Lexus 售後的整體情緒：正面、中立、負面")
    stance_to_dealer: Stance = Field(description="發文者對原廠保修的立場")
    experience_at: str = Field(description="文中描述的保養維修經驗發生在哪裡：原廠、外廠、兩者都有、不明")
    pain_points: List[str] = Field(description="對保養維修的具體不滿（不論原廠或外廠），每點 15 字以內，最多 3 點，例如：等待太久、價格偏高、說明不清楚；沒有則空陣列")
    alternatives: List[Alternative] = Field(description="提到的替代選項")
    key_concerns: List[str] = Field(description="最在意的點，每點 15 字以內，最多 3 點")
    churn_reasons: List[str] = Field(description="若有猶豫或離開原廠，原因為何，每點 15 字以內；沒有則空陣列")
    comment_consensus: str = Field(description="推文的主流意見，一句話；沒有推文則空字串")
    comments_churned: int = Field(description="推文中有幾則是網友說自己已改去非原廠保養維修")
    comments_loyal: int = Field(description="推文中有幾則是網友說自己一直回原廠保養維修")
    comment_churn_reasons: List[str] = Field(description="推文中網友說離開原廠的原因，每點 15 字以內，最多 3 點；沒有則空陣列")
    evidence_quote: str = Field(description="最能代表立場的一句原文，40 字以內")
    summary: str = Field(description="一句話摘要，40 字以內")


PROMPT = """你是汽車售後服務的研究員。以下是一篇台灣網路論壇的貼文與推文。
請判斷它是否在討論 Lexus 的售後服務（保養、維修、零件、保固、服務廠、車主權益），並依欄位標註。
規則：
- 只根據文中內容判斷，看不出來就填「不明」、null 或空陣列，不要猜。
- 回文中引用別人的文字已經移除，只根據回文者自己寫的內容判斷。
- relevant：內文「或推文」中有具體的售後內容就算 true，例如保養維修經驗、具體保養費用金額、
  零件通病或待料、保固或配件保固爭議、服務廠比較。文章主題是購車或新車菜單也一樣，只要推文有這類具體內容就算。
  只有泛泛一句「保養便宜」「很省心」、或完全沒有售後內容的品牌定位、新聞、購車金流糾紛，填 false。
- dealer_trust_issue：對經銷商或原廠體系的信任問題（糾紛、詐騙、處理態度、怕被當盤子）填 true，購車或售後皆可。
- 「原廠」包含 Lexus 授權經銷商的服務廠，例如北都汽車、國都汽車。
  在不同授權經銷商之間比較或換一家，不算離開原廠；只有改去非授權的保養廠、連鎖店或自行保養才算。
- stance_to_dealer（發文者對原廠保養維修的立場）：
  - 只有發文者是現任車主或前車主、且談到自己的保養維修去處時，才填忠誠、猶豫或已轉外廠。
  - 潛在買家、非車主一律填「未提及」。
  - 對購車過程或經銷商糾紛的不滿，不算保養維修立場，填「未提及」，改用 dealer_trust_issue 表達。
  - 「已轉外廠」：明確說自己已改去非原廠保養維修。
  - 「猶豫」：正在比較原廠與外廠、詢問外廠、抱怨原廠保養並考慮離開。
  - 「忠誠」：明確說會繼續或一直在原廠保養維修。
- experience_at：判斷文中描述的保養維修經驗發生地點。
  提到經銷商名稱（北都、國都等）、服務專員、預約進廠、代步車、保固內維修、原廠，通常是「原廠」；
  提到外面的保養廠、連鎖店、自己換，是「外廠」；完全看不出來填「不明」，不要猜。
- pain_points：只要有對保養維修的具體不滿就填，不需要表明要離開原廠，例如「保養等很久」「不便宜」。
- alternatives：只填「保養維修的替代地點或方式」。購車時比較其他品牌不算。
  「換其他品牌」只用在車主因售後經驗表示下次不買 Lexus。
- 推文代表其他網友意見：發文者立場以內文為主；推文的主流意見寫在 comment_consensus，
  推文中自述已改去外廠或一直回原廠的則數，分別寫在 comments_churned、comments_loyal。

標題：{title}
時間：{published}
內文：
{content}

推文（前 {n} 則）：
{comments}
"""


def strip_quotes(text):
    """移除 PTT 回文中引用原文的部分（「※ 引述」那行與「: 」開頭的行）。"""
    keep = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("※ 引述") or s.startswith(": ") or s == ":":
            continue
        keep.append(line)
    return "\n".join(keep).strip()


def build_prompt(post, max_chars=3500, max_comments=80):
    comments = post.get("comments", [])[:max_comments]
    ctext = "\n".join(f"{c['tag']} {c['content']}" for c in comments)
    return PROMPT.format(
        title=post.get("title", ""),
        published=post.get("published", ""),
        content=strip_quotes(post.get("content", ""))[:max_chars],
        n=len(comments),
        comments=ctext[:4000],
    )


OWNERS = {"現任車主", "前車主"}
AFTERSALES_QUERIES = {"保養", "維修", "保固", "原廠", "外廠", "異音", "待料", "召回", "電瓶",
                      "服務廠", "北都", "國都", "原廠保養", "保養廠", "保養費", "延長保固", "保固到期"}


def enforce_rules(d):
    """模型偶爾不守規則的地方，用程式強制修正。"""
    if d.get("speaker") not in OWNERS:
        d["stance_to_dealer"] = "未提及"
        d["purchase_type"] = "不明"
        d["churn_reasons"] = []
        d["alternatives"] = [a for a in d.get("alternatives", []) if a != "換其他品牌"]
    alts = [a for a in d.get("alternatives", []) if a != "無"]
    d["alternatives"] = alts or ["無"]
    return d


class RateLimiter:
    """讓所有執行緒加起來不超過每分鐘 rpm 次請求。"""
    def __init__(self, rpm):
        self.interval = 60.0 / rpm if rpm else 0
        self.lock = threading.Lock()
        self.next_time = 0.0

    def wait(self):
        if not self.interval:
            return
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next_time)
            self.next_time = t + self.interval
        time.sleep(max(0, t - now))


LIMITER = RateLimiter(0)


def retry_delay(err, default):
    """從 429 錯誤訊息讀出建議等待秒數。"""
    m = re.search(r"retry in ([\d.]+)s", str(err))
    return float(m.group(1)) + 1 if m else default


def label_one(client, post, tries=6):
    for i in range(tries):
        LIMITER.wait()
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=build_prompt(post),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Label,
                    temperature=0,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            data = enforce_rules(json.loads(resp.text))
            return {"id": post["id"], "url": post["url"], "title": post["title"],
                    "published": post.get("published"), "source": post.get("source"),
                    "n_comments": len(post.get("comments", [])), **data}
        except Exception as e:  # 額度或暫時性錯誤：等一下再試
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                wait = retry_delay(e, 30)
                print(f"  ! {post['id']}: 額度暫時用完，{wait:.0f} 秒後重試")
            else:
                wait = 5 * (2 ** i)
                print(f"  ! {post['id']}: {msg[:200]} -> {wait}s 後重試")
            time.sleep(wait)
    print(f"  x {post['id']}: 重試多次仍失敗，先跳過（重跑時會再標）")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", default="data/ptt_lexus.jsonl")
    ap.add_argument("--out", default="data/labels.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="只標前 N 篇，先試跑用")
    ap.add_argument("--sample", type=int, default=0, help="隨機抽 N 篇來標（試跑用，比 --limit 更有代表性）")
    ap.add_argument("--aftersales-only", action="store_true",
                    help="只標用售後關鍵字（保養、維修、保固…）找到的文章")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--rpm", type=int, default=14,
                    help="每分鐘最多幾次請求。免費方案用預設 14；開啟付費後可設 0（不限速）")
    args = ap.parse_args()
    global LIMITER
    LIMITER = RateLimiter(args.rpm)

    posts = read_jsonl(args.inp)
    done = set()
    if os.path.exists(args.out):
        good = read_jsonl(args.out, repair=True)
        done = {r["id"] for r in good}
    todo = [p for p in posts if p["id"] not in done]
    if args.aftersales_only:
        todo = [p for p in todo if p.get("found_by_query") in AFTERSALES_QUERIES]
    if args.sample:
        random.Random(42).shuffle(todo)
        todo = todo[: args.sample]
    if args.limit:
        todo = todo[: args.limit]
    print(f"共 {len(posts)} 篇，已標 {len(done)}，本次標 {len(todo)}")

    client = genai.Client()  # 讀取環境變數 GEMINI_API_KEY
    ex = ThreadPoolExecutor(args.workers)
    out = open(args.out, "a", encoding="utf-8")
    pending = {ex.submit(label_one, client, p) for p in todo}
    k = 0
    try:
        while pending:
            # 每秒醒來一次，讓 Ctrl+C 在 Windows 上也能立刻生效
            finished, pending = wait(pending, timeout=1, return_when=FIRST_COMPLETED)
            for f in finished:
                k += 1
                r = f.result()
                if r:
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
                    out.flush()
                if k % 20 == 0:
                    print(f"  {k}/{len(todo)}")
    except KeyboardInterrupt:
        out.close()
        print(f"\n已中斷：本次標了 {k} 篇，結果已存檔。重跑同一個指令會從這裡接續。")
        ex.shutdown(wait=False, cancel_futures=True)
        os._exit(0)
    out.close()
    ex.shutdown()
    write_csv(args.out)


def read_jsonl(path, repair=False):
    """讀 jsonl；跳過寫到一半壞掉的行（例如強制關閉視窗時）。repair=True 會順便把壞行從檔案移除。"""
    good, bad = [], 0
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        try:
            good.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1
    if bad and repair:
        with open(path, "w", encoding="utf-8") as f:
            for r in good:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已移除 {bad} 行損壞的資料（通常是上次強制中斷造成），這些文章會重新標註")
    return good


def write_csv(jsonl_path):
    """攤平成 CSV 給 Excel 看。若 CSV 正在 Excel 開著，改存成另一個檔名。"""
    df = pd.DataFrame(read_jsonl(jsonl_path))
    for col in ["car_models", "topics", "alternatives", "key_concerns", "churn_reasons",
                "comment_churn_reasons", "pain_points"]:
        if col in df:
            df[col] = df[col].apply(lambda v: "、".join(v) if isinstance(v, list) else v)
    path = jsonl_path.replace(".jsonl", ".csv")
    try:
        df.to_csv(path, index=False, encoding="utf-8-sig")
    except PermissionError:
        path = path.replace(".csv", f"_{time.strftime('%H%M%S')}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print("（原本的 CSV 正在 Excel 開著，改存成新檔名）")
    print(f"完成，CSV：{path}")


if __name__ == "__main__":
    main()
