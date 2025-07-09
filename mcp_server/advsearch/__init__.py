import json
import os
import re
import pandas as pd
import subprocess
import requests
import datetime
import azure.functions as func

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INDEX_PATH = os.path.join(BASE_DIR, 'docs', 'index.json')
CSV_DIR = os.path.join(BASE_DIR, 'csv')
PROMPT_PATH = os.path.join(BASE_DIR, '.github', 'models', 'extract.prompt.yaml')
REPO = os.getenv('REPO', 'Mitsuo-Koikawa/Municipal-Bulletin')

with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    INDEX = json.load(f)

SYNONYMS = {
    '移住': ['移住', '住み替え', '移転'],
    '空き家': ['空き家', '空家']
}

def github_user(token: str):
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
    r = requests.get('https://api.github.com/user', headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

def run_phi4(text: str):
    token = os.getenv('GH_MODELS_TOKEN')
    if not token:
        return []
    env = os.environ.copy()
    env['GH_TOKEN'] = token
    try:
        res = subprocess.run([
            'gh', 'models', 'run', PROMPT_PATH,
            '--var', f'text={text}'
        ], check=True, capture_output=True, text=True, env=env)
        out = res.stdout.strip()
        m = re.search(r'\{.*\}', out, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            tags = data.get('keywords') or data.get('tags') or []
            if isinstance(tags, str):
                tags = [t.strip() for t in re.split(r'[、,\s]+', tags) if t.strip()]
            return tags
    except Exception as e:
        print('phi4 error', e)
    return []

def expand_groups(words):
    return [SYNONYMS.get(w, [w]) for w in words]

def includes_any(text: str, arr):
    return any(a in text for a in arr)

def entry_matches(entry, groups):
    text = ' '.join([
        entry.get('article_title', ''),
        entry.get('summary', ''),
        ' '.join(entry.get('tags', [])),
        entry.get('category', '')
    ])
    return all(includes_any(text, g) for g in groups)

def search_entries(entries, q):
    words = run_phi4(q.strip())
    if not words:
        return []
    groups = expand_groups(words)
    return [e for e in entries if entry_matches(e, groups)]

def fetch_article(entry):
    path = os.path.join(BASE_DIR, entry['source'])
    df = pd.read_csv(path)
    row = df.iloc[entry['row'] - 1]
    return row.get('記事本文', '')

def create_markdown(entry, article):
    return f"# {entry['article_title']}\n\n- 自治体: {entry['municipality']}\n- 日付: {entry['date']}\n- 号: {entry['issue_title']}\n- カテゴリ: {entry['category']}\n\n{article}"

def build_markdown(results):
    out = ''
    for e in results:
        article = fetch_article(e)
        out += create_markdown(e, article) + '\n\n'
    return out.strip()

def append_log(user: str, query: str):
    gist = os.getenv('LOG_GIST_ID')
    token = os.getenv('GH_TOKEN')
    if not gist or not token:
        return
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
    url = f'https://api.github.com/gists/{gist}'
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return
        data = resp.json()
        content = data['files'].get('access.log', {}).get('content', '')
        content += json.dumps({'time': datetime.datetime.utcnow().isoformat(), 'user': user, 'query': query}, ensure_ascii=False) + '\n'
        patch = {'files': {'access.log': {'content': content}}}
        requests.patch(url, headers=headers, json=patch)
    except Exception as e:
        print('log error', e)

def is_collaborator(username: str) -> bool:
    token = os.getenv('GH_TOKEN')
    if not token:
        return False
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
    url = f'https://api.github.com/repos/{REPO}/collaborators/{username}'
    r = requests.get(url, headers=headers)
    return r.status_code == 204

def main(req: func.HttpRequest) -> func.HttpResponse:
    auth = req.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return func.HttpResponse('unauthorized', status_code=401)
    token = auth.split(' ', 1)[1]
    user = github_user(token)
    if not user:
        return func.HttpResponse('unauthorized', status_code=401)
    if not is_collaborator(user.get('login')):
        return func.HttpResponse('forbidden', status_code=403)

    if req.params.get('check'):
        return func.HttpResponse(status_code=204)

    q = req.params.get('q') or req.get_json().get('q') if req.get_body() else None
    if not q:
        return func.HttpResponse('missing query', status_code=400)

    results = search_entries(INDEX, q)
    limited = results[:20]
    format_md = req.params.get('format') == 'markdown'
    append_log(user.get('login'), q)

    if format_md:
        md = build_markdown(limited)
        return func.HttpResponse(md, mimetype='text/markdown')
    else:
        body = json.dumps(limited, ensure_ascii=False)
        return func.HttpResponse(body, mimetype='application/json')
