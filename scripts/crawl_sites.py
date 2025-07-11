import os
import json
import requests
import subprocess
import re
import datetime
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUTPUT = os.path.join(BASE_DIR, 'docs', 'crawl_index.json')
PROMPT_PATH = os.path.join(BASE_DIR, '.github', 'models', 'summary.prompt.yaml')

SITES = [
    'https://github.blog'
]


def fetch_text(url: str) -> tuple[str, str]:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else url
    paragraphs = ' '.join(p.get_text(separator=' ', strip=True) for p in soup.find_all('p'))
    return title, paragraphs


def run_slm(text: str) -> tuple[str, list[str]]:
    env = os.environ.copy()
    token = os.getenv('GH_MODELS_TOKEN')
    if token:
        env['GH_TOKEN'] = token
    try:
        res = subprocess.run([
            'gh', 'models', 'run', PROMPT_PATH,
            '--var', f'text={text}'
        ], check=True, capture_output=True, text=True, env=env)
        out = res.stdout.strip()
        m = re.search(r'{.*}', out, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            summary = data.get('summary', '').strip()
            keywords = data.get('keywords') or data.get('tags') or []
            if isinstance(keywords, str):
                keywords = [t.strip() for t in re.split(r'[、,\s]+', keywords) if t.strip()]
            return summary, keywords
    except Exception as e:
        print('slm error', e)
    return '', []


def crawl_site(url: str) -> dict:
    title, text = fetch_text(url)
    summary, keywords = run_slm(text)
    return {
        'title': title,
        'url': url,
        'summary': summary,
        'keywords': keywords,
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
    }


def main():
    entries = []
    for url in SITES:
        try:
            entries.append(crawl_site(url))
        except Exception as e:
            print('crawl error', url, e)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f'Wrote {len(entries)} entries to {OUTPUT}')


if __name__ == '__main__':
    main()
