from fastapi import FastAPI, Query, HTTPException
import requests
from bs4 import BeautifulSoup
import time
import random
from typing import List
from pydantic import BaseModel
from fastapi.responses import RedirectResponse

app = FastAPI(
    title="B2B Job Scraper API",
    description="A safe, polite, and robust scraping API example for portfolio.",
    version="1.0.0"
)

@app.get("/")
def redirect_root():
    # Vercelのルーティングの都合で `/` がAPIに流れてきた場合、明示的に静的ファイルへリダイレクトします
    return RedirectResponse(url="/index.html")

# レスポンスのデータモデル定義
class JobData(BaseModel):
    company_name: str
    location: str
    job_title: str
    posted_date: str
    job_id: str

@app.get("/api/scrape", response_model=List[JobData])
def scrape_jobs(keyword: str = Query(..., description="検索キーワード（例: Python）")):
    """
    指定されたキーワードでダミー求人サイトをスクレイピングし、結果をJSONで返します。
    """
    
    # 【安全設計 1】礼儀正しいアクセス（サーバー負荷の最小化）
    # リクエスト前に2.0〜3.5秒のランダムなスリープを挟みます。
    # 固定秒数ではなくランダムにすることで、機械的なアクセスパターンを散らし、
    # 対象サーバーのレートリミットやWAF（Web Application Firewall）を刺激しない紳士的な設計です。
    sleep_time = random.uniform(2.0, 3.5)
    time.sleep(sleep_time)

    # 【安全設計 2】身元の明示（不審なアクセスとしてのブロック回避）
    # PythonデフォルトのUser-Agent（python-requests/x.x.x）はBotとして弾かれやすいため、
    # 一般的なモダンブラウザ（Chrome）を模したUser-Agentを設定しています。
    # 本番運用時は連絡先（メールアドレス等）をBot用UAに含めることも検討します。
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 対象のベースURL（ここではダミーサイトを想定）
    base_url = "https://example-job-board.com/search"

    try:
        # 【安全設計 5】Vercelのタイムアウト制限（10秒）の回避と文字化け対策
        # Vercel Hobbyプランの10秒制限による強制終了（504 Error）を防ぐため、
        # 余裕を持たせた短いタイムアウト（5.0秒）を設定し、アプリ側で安全にエラーハンドリングします。
        # また、日本語検索時の文字化け（URLエンコード漏れ）を防ぐため params にクエリを渡します。
        response = requests.get(base_url, params={"q": keyword}, headers=headers, timeout=5.0)
        response.raise_for_status() # 400番台、500番台のHTTPエラーを検知
    except requests.exceptions.Timeout:
        # 対象サイトからの応答がない場合は 504 Gateway Timeout を返す
        raise HTTPException(status_code=504, detail="Target website timeout. Please try again later.")
    except requests.exceptions.RequestException as e:
        # その他のネットワークエラー時は 502 Bad Gateway を返す
        raise HTTPException(status_code=502, detail=f"Bad Gateway: Failed to fetch data from target website. Error: {str(e)}")

    # HTMLのパース
    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []

    # ダミーのCSSセレクタ（※実際のサイトのHTML構造に合わせて変更します）
    job_cards = soup.select(".job-card")

    # 【安全設計 3】取得件数の上限（無限ループ・メモリ圧迫の防止）
    # 対象サイトの構造が予期せず巨大化していた場合や、ページネーションのバグによる
    # 無限ループを防ぐため、ハードコードで抽出上限（30件）を設けています。
    MAX_ITEMS = 30

    for idx, card in enumerate(job_cards):
        if idx >= MAX_ITEMS:
            break
            
        try:
            # 各要素の抽出（要素が存在しない場合のエラーハンドリング）
            company_name = card.select_one(".company-name")
            location = card.select_one(".location")
            job_title = card.select_one(".job-title")
            posted_date = card.select_one(".posted-date")
            
            jobs.append(JobData(
                company_name=company_name.text.strip() if company_name else "Unknown",
                location=location.text.strip() if location else "Unknown",
                job_title=job_title.text.strip() if job_title else "Unknown",
                posted_date=posted_date.text.strip() if posted_date else "Unknown",
                job_id=card.get("data-job-id", f"dummy-id-{idx}")
            ))
        except AttributeError as e:
            # 【安全設計 4】エラーハンドリング（アプリクラッシュの防止）
            # 対象サイトのHTML構造（クラス名など）が予告なく変更された場合でも、
            # プログラム全体を停止させず、適切な 500 エラーをクライアントに返します。
            raise HTTPException(
                status_code=500, 
                detail="Internal Server Error: Parsing HTML structure failed. The target website layout might have changed."
            )

    # -------------------------------------------------------------
    # ※ポートフォリオのデモ確認用（対象URLが存在しない場合のフォールバック）
    # 実際のリクエストでデータが0件だった場合、Vercel上での動作確認用に
    # ダミーのデータを返却するロジックを入れています。（不要なら削除可能）
    # -------------------------------------------------------------
    if not jobs:
        for i in range(min(5, MAX_ITEMS)):
            jobs.append(JobData(
                company_name=f"【ダミー】株式会社{keyword}ソリューションズ {i+1}",
                location="東京都渋谷区",
                job_title=f"{keyword} バックエンドエンジニア",
                posted_date="2026-05-24",
                job_id=f"job-{random.randint(1000, 9999)}"
            ))

    return jobs

# Vercel環境へのデプロイについて：
# Vercelは `api/` ディレクトリ内のファイルをサーバーレス関数としてルーティングします。
# この `api/index.py` にある `app` インスタンスがエンドポイントとして機能します。
