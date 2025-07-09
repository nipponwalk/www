import os
import json
import glob
import pandas as pd
import subprocess
import re
from typing import List, Tuple

# Directory containing CSV files
CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'csv')
OUTPUT_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs', 'index.json')

PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.github', 'models', 'extract.prompt.yaml')

def fallback_summary(text: str) -> str:
    text = text.strip().replace('\n', ' ')
    return text[:120] + ("..." if len(text) > 120 else "")


def fallback_tags(text: str) -> List[str]:
    words = [w for w in text.replace('\n', ' ').split(' ') if len(w) > 3]
    seen = []
    for w in words:
        if w not in seen:
            seen.append(w)
        if len(seen) == 5:
            break
    return seen


def run_phi4(text: str) -> Tuple[str, List[str]]:
    text = text.strip().replace('\n', ' ')
    if not text:
        return "", []
    try:
        result = subprocess.run([
            'gh', 'models', 'run', PROMPT_PATH,
            '--var', f'text={text}'
        ], check=True, capture_output=True, text=True)
        out = result.stdout.strip()
        match = re.search(r'\{.*\}', out, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            summary = data.get('summary', '').strip()
            tags = data.get('keywords') or data.get('tags') or []
            if isinstance(tags, str):
                tags = [t.strip() for t in re.split(r'[、,\s]+', tags) if t.strip()]
            return summary, tags
    except Exception as e:
        print('gh models error', e)
    return "", []


def extract_summary_and_tags(text: str) -> Tuple[str, List[str]]:
    summary, tags = run_phi4(text)
    if summary or tags:
        return summary, tags
    return fallback_summary(text), fallback_tags(text)


def detect_encoding(path: str) -> str:
    with open(path, 'rb') as f:
        data = f.read(4000)
    try:
        import chardet
        enc = chardet.detect(data)
        return enc['encoding'] or 'utf-8'
    except Exception:
        return 'utf-8'


def load_csv(path: str) -> pd.DataFrame:
    enc = detect_encoding(path)
    return pd.read_csv(path, encoding=enc)


def build_index() -> list:
    entries = []
    for file in sorted(glob.glob(os.path.join(CSV_DIR, '*.csv'))):
        df = load_csv(file)
        for i, row in df.iterrows():
            article_text = str(row.get('記事本文', ''))
            summary, tags = extract_summary_and_tags(article_text)
            entry = {
                'id': f"{os.path.basename(file)}-{i}",
                'municipality': str(row.get('自治体名', '')),
                'date': str(row.get('公開年月', '')),
                'issue_title': str(row.get('発行号タイトル', '')),
                'article_title': str(row.get('記事タイトル', '')),
                'category': str(row.get('カテゴリ', '')),
                'summary': summary,
                'tags': tags,
                'source': os.path.relpath(file, os.path.dirname(OUTPUT_JSON)),
                'row': i + 1
            }
            entries.append(entry)
    return entries


def main():
    entries = build_index()
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(entries)} entries to {OUTPUT_JSON}")


if __name__ == '__main__':
    main()
