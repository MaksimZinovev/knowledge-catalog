# Knowledge Catalog

[Knowledge Catalog](https://cloud.google.com/products/knowledge-catalog) (formerly Dataplex), is an AI-powered data catalog and metadata management platform. It provides a dynamic knowledge graph of all your data, structured and unstructured, to provide semantics and business context to AI agents

This repository features tools, agents, and samples that demonstrate Knowledge Catalog features, and building context management, enrichment and retrieval solutions.

## Fork changes (this repo)

Forked from [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog) to fix the OKF **visualizer** for real-world bundles (see [okf/VIZ-FILTERING.md](okf/VIZ-FILTERING.md)):

1. **Broken HTML fixed** — concept docs containing `<script>` in their markdown body truncated the embedded bundle JSON (blank graph, `SyntaxError`). The generator now escapes `</` → `<\/`, HTML-parser-safe.
2. **Noise filtered** — bundles previously graphed `node_modules/**/*.md` and similar artifacts as concepts (hundreds of noise nodes). Now skipped via a hardcoded dir set + the bundle's own `.gitignore`.
3. **User control** — optional `viz.config.json` at the bundle root: `"useGitignore": false` to opt out, `exclude: [...]` for extra patterns. Sample: [okf/samples/viz.config.json](okf/samples/viz.config.json).

No behavior change for clean, minimal bundles; filtering only removes files that were never meant to be graphed.

## Getting Started

[![Open in Cloud Shell](http://gstatic.com/cloudssh/images/open-btn.svg)](https://console.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fknowledge-catalog.git)


## Contributing

See the contributing [instructions](CONTRIBUTING.md) to get started contributed.


## License

All solutions within this repository are provided under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license. Please see [LICENSE](LICENSE.md) for more detailed terms and conditions.


## Disclaimer

This repository and its contents are not an official Google product.
