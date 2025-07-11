import json
import os
import azure.functions as func
from typing import Any, List

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INDEX_PATH = os.path.join(BASE_DIR, 'docs', 'crawl_index.json')

try:
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        INDEX = json.load(f)
except Exception:
    INDEX = []


def validate_query(q: Any) -> str | None:
    if not isinstance(q, str):
        return None
    q = q.strip()
    return q if q else None


def search_entries(entries: List[dict], q: str) -> List[dict]:
    words = [w for w in q.lower().split() if w]
    results = []
    for e in entries:
        text = ' '.join([
            e.get('title', ''),
            e.get('summary', ''),
            ' '.join(e.get('keywords', []))
        ]).lower()
        if all(w in text for w in words):
            results.append(e)
    return results


def main(req: func.HttpRequest) -> func.HttpResponse:
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
    body = json.dumps(results[:20], ensure_ascii=False)
    return func.HttpResponse(body, mimetype='application/json')
