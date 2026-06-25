const state = {
  articles: [],
  summary: {},
  history: [],
  sources: [],
  queries: [],
  search: "",
  platform: "all",
  drilldown: null,
  view: "dashboard"
};

const els = {
  dashboardNav: document.querySelector("#dashboardNav"),
  sourcesNav: document.querySelector("#sourcesNav"),
  dashboardView: document.querySelector("#dashboardView"),
  sourcesView: document.querySelector("#sourcesView"),
  sourceDirectory: document.querySelector("#sourceDirectory"),
  sourceCount: document.querySelector("#sourceCount"),
  lastRun: document.querySelector("#lastRun"),
  runScan: document.querySelector("#runScan"),
  queryForm: document.querySelector("#queryForm"),
  queryInput: document.querySelector("#queryInput"),
  queryList: document.querySelector("#queryList"),
  searchInput: document.querySelector("#searchInput"),
  platformFilter: document.querySelector("#platformFilter"),
  metricArticles: document.querySelector("#metricArticles"),
  metricPlatforms: document.querySelector("#metricPlatforms"),
  metricGames: document.querySelector("#metricGames"),
  metricPrices: document.querySelector("#metricPrices"),
  platformChart: document.querySelector("#platformChart"),
  gameChart: document.querySelector("#gameChart"),
  articleRows: document.querySelector("#articleRows"),
  rowCount: document.querySelector("#rowCount"),
  articleFilterLabel: document.querySelector("#articleFilterLabel"),
  clearDrilldown: document.querySelector("#clearDrilldown")
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

async function runScan(query = "") {
  setRunButton(true);
  try {
    const options = { method: "POST" };
    if (query) {
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify({ query });
    }
    await fetch("/api/run-scan", options);
    await loadDashboard();
    showView("dashboard");
  } catch (error) {
    alert(error.message);
  } finally {
    setRunButton(false);
  }
}

function render() {
  renderView();
  renderQueries();
  renderSources();
  renderHistory();
  renderMetrics();
  renderChart(els.platformChart, state.summary.platform_counts || {}, "platform");
  renderChart(els.gameChart, state.summary.game_counts || {}, "game");
  renderRows();
}

function renderView() {
  els.dashboardView.classList.toggle("hidden", state.view !== "dashboard");
  els.sourcesView.classList.toggle("hidden", state.view !== "sources");
  els.dashboardNav.classList.toggle("active", state.view === "dashboard");
  els.sourcesNav.classList.toggle("active", state.view === "sources");
}

function renderSources() {
  els.sourceCount.textContent = `${state.sources.length} source${state.sources.length === 1 ? "" : "s"}`;
  els.sourceDirectory.innerHTML = state.sources
    .map((source) => {
      const homepage = source.homepage || homepageFromUrl(source.url);
      return `
        <article class="source-card">
          <a href="${escapeAttribute(homepage)}" target="_blank" rel="noreferrer">${escapeHtml(source.name)}</a>
          <span>${escapeHtml(hostname(homepage))}</span>
        </article>
      `;
    })
    .join("");
}

function renderQueries() {
  if (!state.queries.length) {
    els.queryList.innerHTML = `<div class="empty-query">No session queries yet.</div>`;
    return;
  }
  els.queryList.innerHTML = state.queries
    .map((query, index) => `
      <div class="saved-query">
        <input value="${escapeAttribute(query)}" data-query-index="${index}" />
        <button type="button" data-query-run="${index}">Run</button>
      </div>
    `)
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

function renderChart(target, values, kind) {
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
        <button class="bar-row chart-button" type="button" data-drilldown-kind="${kind}" data-drilldown-label="${escapeAttribute(label)}">
          <span>${escapeHtml(label)}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${width}%"></span></span>
          <strong>${value}</strong>
        </button>
      `;
    })
    .join("");
}

function renderRows() {
  const rows = filteredArticles();
  const drilldownText = drilldownLabel();
  els.articleFilterLabel.textContent = drilldownText || "Matched by game platform, open-world coverage, or new gaming-system signals.";
  els.clearDrilldown.hidden = !state.drilldown;
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
        <td>${tags(article.games && article.games.length ? article.games : ["No title detected"])}</td>
        <td>${tags(article.prices && article.prices.length ? article.prices : ["None"])}</td>
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
    const platformMatch = state.platform === "all" || (article.platforms || []).includes(state.platform);
    const drilldownMatch = matchesDrilldown(article);
    const text = [
      article.title,
      article.source,
      article.summary,
      ...((article.games || [])),
      ...((article.tags || [])),
      ...((article.prices || []))
    ].join(" ").toLowerCase();
    return platformMatch && drilldownMatch && (!query || text.includes(query));
  });
}

function matchesDrilldown(article) {
  if (!state.drilldown) return true;
  if (state.drilldown.kind === "platform") return (article.platforms || []).includes(state.drilldown.label);
  if (state.drilldown.kind === "game") return (article.games || []).includes(state.drilldown.label);
  return true;
}

function drilldownLabel() {
  if (!state.drilldown) return "";
  const noun = state.drilldown.kind === "platform" ? "platform" : "game cluster";
  return `Showing articles for ${noun}: ${state.drilldown.label}`;
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

function showView(view) {
  state.view = view;
  renderView();
}

function addSessionQuery(query) {
  const cleanQuery = query.trim();
  if (!cleanQuery) return "";
  const existingIndex = state.queries.findIndex((item) => item.toLowerCase() === cleanQuery.toLowerCase());
  if (existingIndex >= 0) return state.queries[existingIndex];
  state.queries.push(cleanQuery);
  renderQueries();
  return cleanQuery;
}

function setRunButton(isRunning) {
  els.runScan.disabled = isRunning;
  els.runScan.innerHTML = isRunning ? "Scanning..." : `<span class="button-icon">R</span>Run scan now`;
}

function homepageFromUrl(value) {
  try {
    const parsed = new URL(value);
    return `${parsed.protocol}//${parsed.hostname}/`;
  } catch {
    return value;
  }
}

function hostname(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return value;
  }
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

els.dashboardNav.addEventListener("click", () => showView("dashboard"));
els.sourcesNav.addEventListener("click", () => showView("sources"));

els.searchInput.addEventListener("input", (event) => {
  state.search = event.target.value;
  renderRows();
});

els.platformFilter.addEventListener("change", (event) => {
  state.platform = event.target.value;
  renderRows();
});

els.clearDrilldown.addEventListener("click", () => {
  state.drilldown = null;
  renderRows();
});

els.platformChart.addEventListener("click", handleChartClick);
els.gameChart.addEventListener("click", handleChartClick);

function handleChartClick(event) {
  const button = event.target.closest("[data-drilldown-kind]");
  if (!button) return;
  state.drilldown = {
    kind: button.dataset.drilldownKind,
    label: button.dataset.drilldownLabel
  };
  showView("dashboard");
  renderRows();
  document.querySelector(".table-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}

els.queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = addSessionQuery(els.queryInput.value);
  if (!query) return;
  els.queryInput.value = "";
  await runScan(query);
});

els.queryList.addEventListener("input", (event) => {
  const input = event.target.closest("[data-query-index]");
  if (!input) return;
  state.queries[Number(input.dataset.queryIndex)] = input.value;
});

els.queryList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-query-run]");
  if (!button) return;
  const index = Number(button.dataset.queryRun);
  const query = addSessionQuery(state.queries[index] || "");
  if (query) await runScan(query);
});

els.runScan.addEventListener("click", () => runScan());

loadDashboard().catch((error) => {
  console.error(error);
  els.articleRows.innerHTML = `<tr><td colspan="6" class="empty-state">Unable to load dashboard data.</td></tr>`;
});
