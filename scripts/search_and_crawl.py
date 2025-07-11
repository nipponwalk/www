import os
import yaml
import json
import requests
import datetime
import re
import subprocess
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONCEPT_PATH = os.path.join(BASE_DIR, '.github', 'models', 'search_concepts.yaml')
PROMPT_PATH = os.path.join(BASE_DIR, '.github', 'models', 'summary.prompt.yaml')
OUTPUT = os.path.join(BASE_DIR, 'data', 'web_summary.json')

SEARCH_URL = 'https://duckduckgo.com/html/'


def load_concepts() -> list[str]:
    if not os.path.exists(CONCEPT_PATH):
        return []
    with open(CONCEPT_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    concepts = data.get('concepts') or []
    if isinstance(concepts, str):
        concepts = [concepts]
    return [str(c) for c in concepts]


def search_web(query: str) -> list[str]:
    params = {'q': query}
    resp = requests.get(SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = []
    for a in soup.select('a.result__a'):
        href = a.get('href')
        if href:
            links.append(href)
        if len(links) == 3:
            break
    return links


def fetch_text(url: str) -> tuple[str, str]:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    title = soup.title.string.strip() if soup.title else url
    paragraphs = ' '.join(p.get_text(separator=' ', strip=True) for p in soup.find_all('p'))
    return title, paragraphs


def run_slm(text: str) -> tuple[str, list[str]]:
    env = os.environ.copy()
    token = os.getenv('GH_MODELS_TOKEN')
    if token:
        env['GH_TOKEN'] = token
    try:
        result = subprocess.run([
            'gh', 'models', 'run', PROMPT_PATH,
            '--var', f'text={text}',
            '--model', 'phi-2'
        ], check=True, capture_output=True, text=True, env=env)
        out = result.stdout.strip()
        m = re.search(r'{.*}', out, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            summary = data.get('summary', '').strip()
            keywords = data.get('keywords') or []
            if isinstance(keywords, str):
                keywords = [t.strip() for t in re.split(r'[、,\s]+', keywords) if t.strip()]
            return summary, keywords
    except Exception as e:
        print('slm error', e)
    return '', []


def crawl_concept(concept: str) -> list[dict]:
    entries = []
    try:
        urls = search_web(concept)
    except Exception as e:
        print('search error', concept, e)
        return entries
    for url in urls:
        try:
            title, text = fetch_text(url)
            summary, keywords = run_slm(text)
            entries.append({
                'concept': concept,
                'title': title,
                'url': url,
                'summary': summary,
                'keywords': keywords,
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            })
        except Exception as e:
            print('crawl error', url, e)
    return entries


def main():
    concepts = load_concepts()
    all_entries = []
    for concept in concepts:
        all_entries.extend(crawl_concept(concept))
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)
    print(f'Wrote {len(all_entries)} entries to {OUTPUT}')


if __name__ == '__main__':
    main()
