import json
import os
import re
import pandas as pd
import azure.functions as func
from typing import List, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INDEX_PATH = os.path.join(BASE_DIR, 'docs', 'index.json')
CSV_DIR = os.path.join(BASE_DIR, 'csv')
MAX_QUERY_LENGTH = 100  # クエリ最大長
MAX_RESULTS = 20        # 最大返却件数

# INDEXのロード
try:
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        INDEX = json.load(f)
except Exception as e:
    INDEX = []
    # ログや通知処理を追加しても良い

SYNONYMS = {
    '移住': ['移住', '住み替え', '移転', '転入', '引越し'],
    '空き家': ['空き家', '空家', '空室', '空屋'],
    '子育て': ['子育て', '育児', '保育', '子ども', '児童'],
    '高齢者': ['高齢者', 'シニア', '老人', 'お年寄り', '高齢化'],
    '福祉': ['福祉', '社会福祉', '福祉サービス', '福祉施設'],
    '防災': ['防災', '災害', '地震', '避難', '防火', '防犯'],
    '健康': ['健康', '医療', '病院', '診療', '検診'],
    '教育': ['教育', '学校', '小学校', '中学校', '高校', '学習'],
    '環境': ['環境', 'エコ', 'リサイクル', 'ごみ', '廃棄物'],
    '交通': ['交通', 'バス', '電車', '公共交通', '道路'],
    '地域': ['地域', '自治会', '町内会', 'コミュニティ'],
    '観光': ['観光', '旅行', '観光地', '名所', '観光案内'],
    '産業': ['産業', '工業', '商業', '農業', '漁業'],
    '雇用': ['雇用', '就職', '求人', '仕事', '労働'],
    '税金': ['税金', '住民税', '固定資産税', '納税'],
    '行政': ['行政', '役所', '市役所', '町役場', '区役所'],
    '補助金': ['補助金', '助成金', '給付金', '支援金'],
    '文化': ['文化', '伝統', '祭り', 'イベント', '文化財'],
    'スポーツ': ['スポーツ', '運動', '体育', '部活動'],
    '住宅': ['住宅', '住まい', '家', '住居', 'マンション']
}

def validate_query(q: Any) -> Optional[str]:
    """クエリのバリデーション。問題なければstrを返す。"""
    if not isinstance(q, str):
        return None
    q = q.strip()
    if not q or len(q) > MAX_QUERY_LENGTH:
        return None
    # 禁止文字やSQLインジェクション対策（例として）
    if re.search(r'[<>"\'\\]', q):
        return None
    return q

def parse_query(q: str) -> Tuple[List[str], Optional[str]]:
    """クエリから検索ワードとソート順を抽出"""
    order = None
    if '新しい順' in q:
        order = 'desc'
    if '古い順' in q:
        order = 'asc'
    q = re.sub(r'新しい順.*|古い順.*|の記事.*|を.*$', '', q)
    words = [w for w in re.split(r'[\s,とや]+', q) if w]
    return words, order

def expand_groups(words: List[str]) -> List[List[str]]:
    """同義語展開"""
    return [SYNONYMS.get(w, [w]) for w in words]

def includes_any(text: str, arr: List[str]) -> bool:
    return any(a in text for a in arr)

def entry_matches(entry: dict, groups: List[List[str]]) -> bool:
    text = ' '.join([
        entry.get('article_title', ''),
        entry.get('summary', ''),
        ' '.join(entry.get('tags', [])),
        entry.get('category', '')
    ])
    return all(includes_any(text, g) for g in groups)

def to_date(s: str) -> pd.Timestamp:
    s = s.replace('.', '-')
    try:
        return pd.to_datetime(s)
    except Exception:
        return pd.Timestamp(0)

def search_entries(entries: List[dict], q: str) -> List[dict]:
    words, order = parse_query(q.strip())
    if not words:
        return []
    groups = expand_groups(words)
    results = [e for e in entries if entry_matches(e, groups)]
    if order:
        results.sort(key=lambda e: to_date(e['date']), reverse=(order == 'desc'))
    return results

def fetch_article(entry: dict) -> str:
    """CSVから記事本文を取得"""
    try:
        path = os.path.join(BASE_DIR, entry['source'])
        df = pd.read_csv(path)
        row = df.iloc[entry['row'] - 1]
        return row.get('記事本文', '')
    except Exception:
        return ''

def create_markdown(entry: dict, article: str) -> str:
    return f"# {entry['article_title']}\n\n- 自治体: {entry['municipality']}\n- 日付: {entry['date']}\n- 号: {entry['issue_title']}\n- カテゴリ: {entry['category']}\n\n{article}"

def build_markdown(results: List[dict]) -> str:
    out = ''
    for e in results:
        article = fetch_article(e)
        out += create_markdown(e, article) + '\n\n'
    return out.strip()

def main(req: func.HttpRequest) -> func.HttpResponse:
    """HTTPリクエストのエントリポイント"""
    try:
        q = req.params.get('q')
        if not q and req.get_body():
            try:
                q = req.get_json().get('q')
            except Exception:
                q = None
        q = validate_query(q)
        if not q:
            return func.HttpResponse('Invalid or missing query', status_code=400)
        results = search_entries(INDEX, q)
        format_md = req.params.get('format') == 'markdown'
        limited = results[:MAX_RESULTS]
        if format_md:
            md = build_markdown(limited)
            return func.HttpResponse(md, mimetype='text/markdown')
        else:
            body = json.dumps(limited, ensure_ascii=False)
            return func.HttpResponse(body, mimetype='application/json')
    except Exception as e:
        return func.HttpResponse(f'Internal server error: {str(e)}', status_code=500)
