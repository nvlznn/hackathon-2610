"""
Mobile01 測試：確認能不能用程式抓 Lexus 版，並把網頁存下來，讓我們依實際結構寫正式爬蟲。

用法：
    python probe_mobile01.py

會產生：
    probe/report.txt      每個網址的結果（狀態碼、大小、是否被擋）
    probe/*.html          抓到的網頁原始碼
把整個 probe 資料夾壓縮後傳給 Claude。
"""
import os
import re
import time

import requests

URLS = {
    "list_p1": "https://www.mobile01.com/topiclist.php?f=346",
    "list_p2": "https://www.mobile01.com/topiclist.php?f=346&p=2",
}
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"),
    "Accept-Language": "zh-TW,zh;q=0.9",
}


def blocked(html, status):
    signs = ["cf-challenge", "Just a moment", "Attention Required", "captcha", "Access denied"]
    return status != 200 or any(s.lower() in html.lower() for s in signs)


def main():
    os.makedirs("probe", exist_ok=True)
    s = requests.Session()
    lines = []
    first_topic = None
    for name, url in URLS.items():
        try:
            r = s.get(url, headers=HEADERS, timeout=20)
            html = r.text
            is_blocked = blocked(html, r.status_code)
            open(f"probe/{name}.html", "w", encoding="utf-8").write(html)
            lines.append(f"{name}\t{r.status_code}\t{len(html)} bytes\t被擋={is_blocked}\t{url}")
            if not first_topic:
                m = re.search(r'href="(topicdetail\.php\?f=346&(?:amp;)?t=\d+)"', html)
                if m:
                    first_topic = "https://www.mobile01.com/" + m.group(1).replace("&amp;", "&")
        except requests.RequestException as e:
            lines.append(f"{name}\tERROR\t{e}\t{url}")
        time.sleep(2)

    if first_topic:
        for name, url in [("topic_p1", first_topic), ("topic_p2", first_topic + "&p=2")]:
            try:
                r = s.get(url, headers=HEADERS, timeout=20)
                open(f"probe/{name}.html", "w", encoding="utf-8").write(r.text)
                lines.append(f"{name}\t{r.status_code}\t{len(r.text)} bytes\t被擋={blocked(r.text, r.status_code)}\t{url}")
            except requests.RequestException as e:
                lines.append(f"{name}\tERROR\t{e}\t{url}")
            time.sleep(2)
    else:
        lines.append("找不到文章連結：列表頁可能被擋，或網頁結構不同")

    open("probe/report.txt", "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    print("\n完成。請把 probe 資料夾壓縮後傳給 Claude。")


if __name__ == "__main__":
    main()
