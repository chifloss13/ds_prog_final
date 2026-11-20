import json
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

URL = "https://github.com/orgs/google/repositories"
DB_NAME = "repos.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (class assignment scraper)"}


MAX_PAGES = None


def find_repos(obj, found):
    """JSONの中から、リポジトリ1件分の辞書を再帰的に探す"""
    if isinstance(obj, dict):
        if "name" in obj and "starsCount" in obj:
            found.append(obj)
        for v in obj.values():
            find_repos(v, found)
    elif isinstance(obj, list):
        for v in obj:
            find_repos(v, found)


def parse_page(html):
    """1ページ分のHTMLから (名前, 言語, スター数) のリストを返す"""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.select_one('script[data-target="react-app.embeddedData"]')
    if script is None or script.string is None:
        return []
    data = json.loads(script.string)

    found = []
    find_repos(data, found)

    results = []
    for repo in found:
        lang = repo.get("primaryLanguage")
        language = lang["name"] if lang else None   # 言語なしは None
        results.append((repo["name"], language, repo["starsCount"]))
    return results


def fetch_page(page):
    """1ページ分のHTMLを取得。429のときは待ってやり直す"""
    for attempt in range(5):
        res = requests.get(URL, params={"page": page}, headers=HEADERS, timeout=10)
        if res.status_code == 429:
            retry_after = res.headers.get("Retry-After", "")
            wait = int(retry_after) if retry_after.isdigit() else 0
            wait = max(wait, 60 * (attempt + 1))   # 最低60秒、回を重ねるごとに延ばす
            print(f"page {page}: 429 のため {wait} 秒待ちます（{attempt + 1}回目）")
            time.sleep(wait)
            continue
        res.raise_for_status()
        return res.text
    raise RuntimeError(f"page {page}: 429 が続いたため中断します")



def scrape_all(conn):
    """1ページ取得するごとにDBへ保存する。保存した件数の合計を返す"""
    seen = set()
    page = 1
    while True:
        repos = parse_page(fetch_page(page))

        # 取得できなかった、または既出のページなら終了
        new_repos = [r for r in repos if r[0] not in seen]
        if not new_repos:
            break
        for r in new_repos:
            seen.add(r[0])
        save(conn, new_repos)   # ここで1ページ分を保存
        print(f"page {page}: {len(new_repos)}件（累計 {len(seen)}件）")

        if MAX_PAGES is not None and page >= MAX_PAGES:
            break
        page += 1
        time.sleep(1)   
    return len(seen)


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            language TEXT,
            stars INTEGER NOT NULL
        )
        """
    )


def save(conn, repos):
    conn.executemany(
        "INSERT OR REPLACE INTO repositories (name, language, stars) VALUES (?, ?, ?)",
        repos,
    )
    conn.commit()


def show(conn):
    rows = conn.execute(
        "SELECT name, language, stars FROM repositories ORDER BY stars DESC"
    ).fetchall()
    for name, lang, stars in rows:
        print(f"{name:40} {str(lang):15} {stars}")
    print(f"合計 {len(rows)} 件")


def main():
    conn = sqlite3.connect(DB_NAME)
    init_db(conn)
    scrape_all(conn)
    show(conn)
    conn.close()


if __name__ == "__main__":
    main()