# Open World Watch

Open World Watch is a local weekly news-tracking app for gaming articles about open-world games, major game platforms, PC releases, Xbox coverage, and new gaming-system news.

It collects source-linked articles from configurable gaming-news RSS feeds, groups the findings by platform, inferred game title, source, tags, and price signals, then presents a dashboard plus CSV export.

## Features

- Weekly or one-shot scraper for gaming news sources.
- Matches open-world coverage across tracked platforms.
- Tracks PC games, Xbox games, PlayStation, Nintendo Switch, Nintendo Switch 2, Steam Deck, and new gaming-system or hardware news.
- Keeps source URLs in both the dashboard and CSV.
- Groups articles by platform, source, inferred game/title cluster, tags, and detected prices.
- Exports `data/articles.csv`.
- Runs as a local web app with no login credentials.
- Uses `defusedxml` for safer RSS/Atom XML parsing.

## Quick Start

```powershell
cd C:\Users\jmars\CodeRepos\open-world-watch
python -m open_world_watch.app --once
python -m open_world_watch.app --weekly
```

Open the dashboard at:

```text
http://127.0.0.1:8765
```

The `--weekly` flag keeps the app running and starts a scan every seven days. You can also click **Run scan now** in the dashboard.

## Windows Weekly Task

For a more durable weekly schedule, create a Windows Task Scheduler job that runs:

```powershell
python -m open_world_watch.app --once
```

Use this project folder as the task's working directory:

```text
C:\Users\jmars\CodeRepos\open-world-watch
```

Then run the dashboard separately whenever you want to review results:

```powershell
python -m open_world_watch.app
```

## Data Files

Generated files live in `data/`:

- `articles.json`: full stored dataset.
- `articles.csv`: spreadsheet-friendly export.
- `scan_history.json`: latest weekly scan history.

The CSV includes:

- article id
- title
- source URL
- source name
- published date
- summary
- matched terms
- platforms
- inferred games
- price signals
- tags
- collected timestamp

## Sources

Edit `config/sources.json` to add or remove RSS sources.

The starter list includes IGN, GameSpot, Polygon, Eurogamer, Nintendo Life, Push Square, Gematsu, Video Games Chronicle, Rock Paper Shotgun, GamesRadar, PC Gamer, VG247, Siliconera, TheGamer, Destructoid, Kotaku, Game Informer, GamesIndustry.biz, Xbox Wire, and PlayStation Blog.

## Matching Rules

An article is included when it contains at least one tracked platform and either open-world language or gaming-system news language.

- Open-world language:
  - `Open World` or `open-world`
- Gaming-system news language:
  - new console, gaming system, next-gen hardware, handheld device, console reveal, hardware launch, or successor
- Platform families:
  - `PS5`, `PlayStation 5`, broader `PlayStation`, or other PS generation mentions
  - `Nintendo Switch 2`, `Switch 2`, `Nintendo Switch`, or `Switch`
  - `Xbox Series X|S`, broader `Xbox`, or `Game Pass`
  - `PC`, `Windows PC`, `Steam`, `Epic Games Store`, `GOG`, or `Steam Deck`

This means the app does not require multiple platforms in one article. If an article mentions several, all platform tags are preserved.

## Tests

All unit tests live under the unified `tests/` directory:

- `tests/test_analyzer.py`
- `tests/test_app.py`
- `tests/test_scraper.py`
- `tests/test_storage.py`
- `tests/check_coverage.py`

Run the unit tests:

```powershell
python -m pytest
```

Run tests with the built-in coverage gate:

```powershell
python tests\check_coverage.py
```

The coverage gate expects at least 90% line coverage.

Run the same local static checks used by CI:

```powershell
python -m ruff check open_world_watch tests
python -m bandit -r open_world_watch -q
```

## GitHub Pipeline

The repository includes `.github/workflows/ci.yml`, which runs on pushes and pull requests to `main` and `dev`, and can also be started manually.

- `Unit Tests / Python 3.11` and `Unit Tests / Python 3.12`: install the app, run `python -m pytest`, then run `python tests/check_coverage.py`.
- `Code Scanning / Quality`: runs Ruff static analysis over `open_world_watch` and `tests`.
- `Code Scanning / Security`: runs Bandit against application code. On public repositories, it also runs GitHub CodeQL for Python and uses Dependency Review on pull requests.

The CodeQL and Dependency Review steps are gated to public repositories because GitHub code scanning features are free for public repositories and may require GitHub Advanced Security on private repositories.

Dependabot is configured in `.github/dependabot.yml` to open weekly update pull requests for GitHub Actions and Python package dependencies.

## Notes

This app uses public RSS feeds and source links. It does not bypass paywalls, login prompts, robots restrictions, or access controls. If a site changes its feed format or disables RSS access, update or remove that source in `config/sources.json`.
