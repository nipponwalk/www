# Municipal-Bulletin

This repository provides a database of municipal bulletins. Article data is stored in CSV format under the `csv/` folder.

## Search Page

The contents of the `docs/` folder are published via GitHub Pages. You can access the search page at `docs/index.html`. It loads an index (`docs/index.json`) and performs keyword searches. Article bodies are fetched from the CSV files on demand and displayed or downloaded in Markdown format.

[Bulletin Search Page](https://mitsuo-koikawa.github.io/Municipal-Bulletin)

An [advanced search page](https://mitsuo-koikawa.github.io/Municipal-Bulletin/advanced.html) is also available. It requires GitHub authentication and is limited to repository collaborators. Text you provide is analyzed with GitHub Models **Phi4** to find related articles. Access logs are kept on GitHub storage for 30 days.

## Updating the Index

CSV files are not automatically indexed. Previously, `.github/workflows/update-index.yml` ran automatically, but to reduce token usage for GitHub Models **Phi4**, indexing is now performed manually. Use `scripts/update_index.py` to generate the index; if it fails, a simplified fallback will be used.

### Manual Execution

```bash
pip install -r requirements.txt
python scripts/update_index.py
```

Commit the generated `docs/index.json` file.

## CSV Encoding Check

CSV file encoding is always validated by GitHub Actions (`.github/workflows/ensure-utf8.yml`). Files saved in encodings other than UTF-8 will be automatically converted to UTF-8 and committed to the repository.

## MCP Server

The `mcp_server/` directory contains an Azure Functions app that searches the CSV using the `docs/index.json` index. Send a query parameter `q` to the `/api/search` HTTP endpoint to get results in JSON. Specify `format=markdown` to include the article text as Markdown.

Deployment is performed by manually running `.github/workflows/deploy-mcp.yml`. Set the following secrets:

- `AZURE_CREDENTIALS` – service principal credentials
- `FUNCTION_APP_NAME` – name of the target Function App

## License

Source code in this repository is released under the [Apache License 2.0](./LICENSE).
Data in the `csv/` folder and elsewhere is provided under the [Creative Commons Attribution 4.0 International](./LICENSE-CC-BY-4.0.txt) license.
