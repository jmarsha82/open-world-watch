const state = {
  articles: [],
  summary: {},
  history: [],
  sources: [],
  search: "",
  platform: "all"
};

const els = {
  sourceList: document.querySelector("#sourceList"),
  lastRun: document.querySelector("#lastRun"),
  runScan: document.querySelector("#runScan"),
  searchInput: document.querySelector("#searchInput"),
  platformFilter: document.querySelector("#platformFilter"),
  metricArticles: document.querySelector("#metricArticles"),
  metricPlatforms: document.querySelector("#metricPlatforms"),
  metricGames: document.querySelector("#metricGames"),
  metricPrices: document.querySelector("#metricPrices"),
  platformChart: document.querySelector("#platformChart"),
  gameChart: document.querySelector("#gameChart"),
  articleRows: document.querySelector("#articleRows"),
  rowCount: document.querySelector("#rowCount")
};

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

async function loadDashboard() {
  const [articles, summary, history, sources] = await Promise.all([
    getJson("/api/articles"),
    getJson("/api/summary"),
    getJson("/api/history"),
    getJson("/api/sources")
  ]);
  state.articles = articles;
  state.summary = summary;
  state.history = history;
  state.sources = sources;
  render();
}

function render() {
  renderSources();
  renderHistory();
  renderMetrics();
  renderChart(els.platformChart, state.summary.platform_counts || {});
  renderChart(els.gameChart, state.summary.game_counts || {});
  renderRows();
}

function renderSources() {
  els.sourceList.innerHTML = state.sources
    .map((source) => `<div class="source-chip">${escapeHtml(source.name)}</div>`)
    .join("");
}

function renderHistory() {
  const latest = state.history[0];
  if (!latest) {
    els.lastRun.textContent = "No scan recorded yet.";
    return;
  }
  const date = formatDate(latest.finished_at);
  els.lastRun.textContent = `${date}: ${latest.articles_found} new matches from ${latest.sources_checked} sources.`;
}

function renderMetrics() {
  els.metricArticles.textContent = String(state.summary.total_articles || 0);
  els.metricPlatforms.textContent = String(Object.keys(state.summary.platform_counts || {}).length);
  els.metricGames.textContent = String(Object.keys(state.summary.game_counts || {}).length);
  els.metricPrices.textContent = String(state.summary.price_signal_count || 0);
}

function renderChart(target, values) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1]).slice(0, 8);
  if (!entries.length) {
    target.innerHTML = `<div class="empty-state">Run a scan to populate this chart.</div>`;
    return;
  }
  const max = Math.max(...entries.map(([, value]) => value), 1);
  target.innerHTML = entries
    .map(([label, value]) => {
      const width = Math.max(4, Math.round((value / max) * 100));
      return `
        <div class="bar-row">
          <span>${escapeHtml(label)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
          <strong>${value}</strong>
        </div>
      `;
    })
    .join("");
}

function renderRows() {
  const rows = filteredArticles();
  els.rowCount.textContent = `${rows.length} result${rows.length === 1 ? "" : "s"}`;
  if (!rows.length) {
    els.articleRows.innerHTML = `<tr><td colspan="6" class="empty-state">No matching articles yet. Run a scan or widen your filters.</td></tr>`;
    return;
  }
  els.articleRows.innerHTML = rows
    .map((article) => `
      <tr>
        <td>
          <div class="article-cell">
            ${articleImage(article)}
            <div>
              <a class="article-link" href="${escapeAttribute(article.url)}" target="_blank" rel="noreferrer">
                ${escapeHtml(article.title)}
              </a>
              <div class="muted">${escapeHtml(trimSummary(article.summary))}</div>
            </div>
          </div>
        </td>
        <td>${tags(article.platforms)}</td>
        <td>${tags(article.games.length ? article.games : ["Unclassified"])}</td>
        <td>${tags(article.prices.length ? article.prices : ["None"])}</td>
        <td>
          <strong>${escapeHtml(article.source)}</strong>
          <div class="muted">Source linked in title</div>
        </td>
        <td>${escapeHtml(formatDate(article.published))}</td>
      </tr>
    `)
    .join("");
}

function filteredArticles() {
  const query = state.search.trim().toLowerCase();
  return state.articles.filter((article) => {
    const platformMatch = state.platform === "all" || article.platforms.includes(state.platform);
    const text = [
      article.title,
      article.source,
      article.summary,
      ...(article.games || []),
      ...(article.tags || []),
      ...(article.prices || [])
    ].join(" ").toLowerCase();
    return platformMatch && (!query || text.includes(query));
  });
}

function tags(values) {
  return `<div class="tag-list">${values.map((value) => `<span class="tag">${escapeHtml(value)}</span>`).join("")}</div>`;
}

function articleImage(article) {
  if (!article.image_url) return `<div class="article-image-placeholder" aria-hidden="true"></div>`;
  return `
    <img
      class="article-image"
      src="${escapeAttribute(article.image_url)}"
      alt=""
      loading="lazy"
      referrerpolicy="no-referrer"
    />
  `;
}

function trimSummary(value) {
  if (!value) return "No summary supplied by source feed.";
  return value.length > 150 ? `${value.slice(0, 147)}...` : value;
}

function formatDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

els.searchInput.addEventListener("input", (event) => {
  state.search = event.target.value;
  renderRows();
});

els.platformFilter.addEventListener("change", (event) => {
  state.platform = event.target.value;
  renderRows();
});

els.runScan.addEventListener("click", async () => {
  els.runScan.disabled = true;
  els.runScan.textContent = "Scanning...";
  try {
    await fetch("/api/run-scan", { method: "POST" });
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  } finally {
    els.runScan.disabled = false;
    els.runScan.innerHTML = `<span class="button-icon">↻</span>Run scan now`;
  }
});

loadDashboard().catch((error) => {
  console.error(error);
  els.articleRows.innerHTML = `<tr><td colspan="6" class="empty-state">Unable to load dashboard data.</td></tr>`;
});
