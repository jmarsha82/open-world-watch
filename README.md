# Open World Watch

Open World Watch is a local weekly news-tracking app for gaming articles that mention `Open World` with either `PS5` or `Nintendo Switch 2`.

It collects source-linked articles from configurable gaming-news RSS feeds, groups the findings by platform, inferred game title, source, tags, and price signals, then presents a dashboard plus CSV export.

## Features

- Weekly or one-shot scraper for gaming news sources.
- Matches `Open World + PS5` and `Open World + Nintendo Switch 2`.
- Keeps source URLs in both the dashboard and CSV.
- Groups articles by platform, source, inferred game/title cluster, tags, and detected prices.
- Exports `data/articles.csv`.
- Runs as a local web app with no login credentials.
- Uses only the Python standard library.

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

The starter list includes IGN, GameSpot, Polygon, Eurogamer, Nintendo Life, Push Square, Gematsu, Video Games Chronicle, Rock Paper Shotgun, and GamesRadar.

## Matching Rules

An article is included when it contains:

- `Open World` or `open-world`
- at least one platform family:
  - `PS5`, `PlayStation 5`, or `PlayStation five`
  - `Nintendo Switch 2` or `Switch 2`

This means the app does not require both platforms in one article. If an article mentions both, both platform tags are preserved.

## Tests

Run the unit tests:

```powershell
python -m unittest discover -s tests
```

Run tests with the built-in coverage gate:

```powershell
python tests\check_coverage.py
```

The coverage gate expects at least 90% line coverage.

## Notes

This app uses public RSS feeds and source links. It does not bypass paywalls, login prompts, robots restrictions, or access controls. If a site changes its feed format or disables RSS access, update or remove that source in `config/sources.json`.
