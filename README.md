# Municipal-Bulletin

English version available: [README-en.md](README-en.md)

地方自治体の広報誌データベースです。`csv/` フォルダに CSV 形式で記事データを保管しています。

## 検索ページ

`docs/` フォルダが GitHub Pages として公開され、`docs/index.html` から検索ページを利用できます。検索ページではインデックス (`docs/index.json`) を読み込み、キーワード検索を行います。記事の本文は必要に応じて CSV から取得し Markdown 形式で表示・ダウンロードできます。

[広報誌検索ページ](https://mitsuo-koikawa.github.io/Municipal-Bulletin)

GitHub アカウントで認証して利用する [高度な検索ページ](https://mitsuo-koikawa.github.io/Municipal-Bulletin/advanced.html) も用意しました。こちらでは入力した文章を GitHub Models の **Phi4** で解析し、インデックスから関連する記事を検索します。検索時のアクセスログは GitHub 上のストレージに30日間保存されます。リポジトリ Collaborator のみ利用可能です。

## インデックスの更新

CSV ファイルが追加・変更されても自動では更新されません。以前は `.github/workflows/update-index.yml` が自動実行されていましたが、GitHub Models の SLM **Phi4** を利用する際のトークン消費を抑えるため現在は手動実行としています。インデックスの生成には `scripts/update_index.py` を使用し、失敗した場合は簡易的な処理で代替します。

### 手動で実行する場合

```bash
pip install -r requirements.txt
python scripts/update_index.py
```

生成された `docs/index.json` をコミットしてください。

## CSV 文字コードの検証

CSV ファイルのエンコーディングは GitHub Actions (`.github/workflows/ensure-utf8.yml`) により常に検証されます。UTF-8 以外で保存されたファイルは自動的に UTF-8 に変換され、リポジトリへコミットされます。

## MCPサーバー

`mcp_server/` ディレクトリには、検索インデックス `docs/index.json` を利用して CSV を検索する Azure Functions アプリを用意しています。HTTP エンドポイント `/api/search` にクエリ `q` を渡すと検索結果を JSON で返し、`format=markdown` を指定すると記事本文を含む Markdown を生成します。

デプロイは `.github/workflows/deploy-mcp.yml` を手動実行して行います。実行するには以下の Secrets を設定してください。

- `AZURE_CREDENTIALS` – サービスプリンシパルの認証情報
- `FUNCTION_APP_NAME` – デプロイ先の Function App 名

## ライセンス

このリポジトリのソースコードは [Apache License 2.0](./LICENSE) の下で公開されています。
`csv/` フォルダをはじめとするデータは [Creative Commons Attribution 4.0 International](./LICENSE-CC-BY-4.0.txt)（<https://creativecommons.org/licenses/by/4.0/>）ライセンスで提供されます。

