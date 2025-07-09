function debug() {
  console.debug.apply(console, arguments);
}

async function loadIndex() {
  debug('Loading index.json');
  const res = await fetch('index.json');
  const data = await res.json();
  debug('Index loaded');
  return data;
}

function createMarkdown(entry, article) {
  debug('Creating markdown for', entry.id);
  return `# ${entry.article_title}\n\n- 自治体: ${entry.municipality}\n- 日付: ${entry.date}\n- 号: ${entry.issue_title}\n- カテゴリ: ${entry.category}\n\n${article}`;
}

function githubApiUrl(path) {
  const clean = path.replace(/^\.\.\//, '');
  return 'https://api.github.com/repos/Mitsuo-Koikawa/Municipal-Bulletin/contents/' +
    clean.split('/').map(encodeURIComponent).join('/') + '?ref=main';
}

async function fetchArticle(entry) {
  debug('Fetching article from', entry.source, 'row', entry.row);
  const apiUrl = githubApiUrl(entry.source);
  const res = await fetch(apiUrl);
  const info = await res.json();
  let text;
  if (info.download_url) {
    const raw = await fetch(info.download_url);
    const buf = await raw.arrayBuffer();
    text = new TextDecoder('utf-8').decode(buf);
  } else if (info.content) {
    const binary = atob(info.content.replace(/\n/g, ''));
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    text = new TextDecoder('utf-8').decode(bytes);
  } else {
    throw new Error('Failed to load CSV');
  }
  const parsed = Papa.parse(text, {header:true});
  const row = parsed.data[entry.row - 1];
  const body = row && row['記事本文'] || '';
  debug('Fetched article length', body.length);
  return body;
}

function download(name, content) {
  const blob = new Blob([content], {type: 'text/markdown'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

const SYNONYMS = {
  '移住': ['移住', '住み替え', '移転'],
  '空き家': ['空き家', '空家']
};

function parseQuery(q) {
  debug('Parsing query', q);
  let order = null;
  if(q.includes('新しい順')) order = 'desc';
  if(q.includes('古い順')) order = 'asc';
  q = q.replace(/新しい順.*|古い順.*|の記事.*|を.*$/g, '');
  const words = q.split(/[\s,とや]+/).filter(Boolean);
  const result = { keywords: words, order };
  debug('Parsed query', result);
  return result;
}

function expandGroups(words) {
  return words.map(w => SYNONYMS[w] || [w]);
}

function includesAny(text, arr) {
  return arr.some(a => text.includes(a));
}

function entryMatches(entry, groups) {
  const text = [entry.article_title, entry.summary, entry.tags && entry.tags.join(' '), entry.category].join(' ');
  return groups.every(g => includesAny(text, g));
}

function toDate(str) {
  return new Date(str.replace(/\./g, '-'));
}

async function search(entries, q) {
  const {keywords, order} = parseQuery(q.trim());
  if(!keywords.length) {
    debug('No keywords provided');
    return [];
  }
  debug('Searching for', keywords, 'order:', order);
  const groups = expandGroups(keywords);
  let results = entries.filter(e => entryMatches(e, groups));
  debug('Entries matched', results.length);
  if(order) {
    debug('Sorting results');
    results.sort((a,b) => order === 'desc' ? toDate(b.date) - toDate(a.date) : toDate(a.date) - toDate(b.date));
  }
  return results;
}

async function fetchCombinedMarkdown(results) {
  debug('Building combined markdown for', results.length, 'results');
  let out = '';
  for(const e of results) {
    debug('Processing entry', e.id);
    const article = await fetchArticle(e);
    out += createMarkdown(e, article) + '\n\n';
  }
  const trimmed = out.trim();
  debug('Combined markdown length', trimmed.length);
  return trimmed;
}

window.addEventListener('DOMContentLoaded', async () => {
  debug('DOM loaded');
  const entries = await loadIndex();
  const downloadBtn = document.getElementById('downloadBtn');
  const spinner = document.getElementById('spinner');
  document.getElementById('searchBtn').addEventListener('click', async () => {
    debug('Search button clicked');
    if (spinner) spinner.style.display = 'inline-block';
    const q = document.getElementById('query').value;
    debug('Query:', q);
    const results = await search(entries, q);
    debug('Results count', results.length);
    const container = document.getElementById('results');
    container.innerHTML = '';
    if (downloadBtn) downloadBtn.style.display = 'none';
    if(!results.length) {
      container.textContent = '見つかりませんでした';
      if (spinner) spinner.style.display = 'none';
      return;
    }
    const limited = results.slice(0, 20);
    debug('Fetching markdown for', limited.length, 'entries');
    const md = await fetchCombinedMarkdown(limited);
    debug('Markdown ready');
    const pre = document.createElement('pre');
    pre.className = 'markdown';
    pre.textContent = md;
    container.appendChild(pre);
    if (downloadBtn) {
      downloadBtn.style.display = 'inline';
      downloadBtn.onclick = () => download('results.md', md);
    }
    if (spinner) spinner.style.display = 'none';
  });
});
