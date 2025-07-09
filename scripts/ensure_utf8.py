import os
import glob
import chardet

CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'csv')


def detect_encoding(path: str) -> str:
    with open(path, 'rb') as f:
        data = f.read(4000)
    enc = chardet.detect(data).get('encoding') or 'utf-8'
    return enc


def convert_file(path: str) -> bool:
    enc = detect_encoding(path)
    if enc.lower().replace('-', '') in ['utf8', 'utf8sig']:
        return False
    with open(path, 'r', encoding=enc, errors='ignore') as f:
        text = f.read()
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    return True


if __name__ == '__main__':
    changed = False
    for file in glob.glob(os.path.join(CSV_DIR, '*.csv')):
        if convert_file(file):
            print(f'Converted {file} to UTF-8')
            changed = True
    if changed:
        print('Some files were converted to UTF-8.')
    else:
        print('All files are already UTF-8.')
