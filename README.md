# STOCK Unified Workspace

This repository keeps the cognition system and evidence engine together while
preserving their ownership boundary:

- `investing-os/`: brain, cognition, workflow, plans, and user-facing artifacts.
- `stock_team/`: evidence collection, calculations, backtests, and dashboards.

## Runtime Boundary

Run `stock_team` commands from this repository root so `python -m stock_team.cli`
can import the package. By default, `stock_team` discovers the sibling
`investing-os` directory. Set `INVESTING_OS_HOME` only when intentionally using
another brain repository.

```powershell
$py = 'C:\Users\rriww\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m stock_team.cli --help
```

The original directories remain untouched during migration:

- `C:\Users\rriww\Documents\investing-os`
- `D:\gemini\lianghua\stock_team`

Do not delete them until the unified Stage 0 -> discussion -> Stage 1 ->
intraday dashboard flow has been validated with production data.

## Local Data

Credentials, broker positions, databases, historical caches, generated
`findings`, and live dashboard manifests are intentionally excluded from Git.
Copy or regenerate local runtime data when needed; never commit `.env`.

## Verification

```powershell
$py = 'C:\Users\rriww\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m pytest stock_team\tests\unit\core\test_cli.py -q
```
