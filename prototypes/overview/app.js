/*
 * THROWAWAY PROTOTYPE
 * Three Overview variants, switchable via ?variant=, on the only prototype route.
 */

const variants = [
  { key: "A", name: "Update progress" },
  { key: "B", name: "Update sources" },
  { key: "C", name: "Review updates" },
];

const themes = [
  ["system", "System"],
  ["light", "Light"],
  ["dark", "Dark"],
  ["amoled", "AMOLED"],
  ["solarized-light", "Solarized light"],
  ["solarized-dark", "Solarized dark"],
  ["github-light", "GitHub light"],
  ["github-dark", "GitHub dark"],
  ["norse", "Norse"],
  ["nord", "Nord"],
  ["gruvbox-light", "Gruvbox light"],
  ["gruvbox-dark", "Gruvbox dark"],
  ["dracula", "Dracula"],
  ["catppuccin-latte", "Catppuccin Latte"],
  ["catppuccin-mocha", "Catppuccin Mocha"],
  ["sepia", "Sepia"],
  ["midnight", "Midnight"],
  ["high-contrast", "High contrast"],
];

const icons = {
  overview: "⌂",
  updates: "↻",
  catalog: "⌕",
  activity: "◴",
  health: "◇",
  settings: "⚙",
};

function esc(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function currentVariant() {
  const requested = new URLSearchParams(location.search).get("variant")?.toUpperCase();
  return variants.some(({ key }) => key === requested) ? requested : "A";
}

function currentTheme() {
  const requested = new URLSearchParams(location.search).get("theme")?.toLowerCase();
  return themes.some(([key]) => key === requested) ? requested : "system";
}

function applyTheme(key = currentTheme()) {
  if (key === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.dataset.theme = key;
}

function setTheme(key) {
  const safeKey = themes.some(([candidate]) => candidate === key) ? key : "system";
  const url = new URL(location.href);
  if (safeKey === "system") url.searchParams.delete("theme");
  else url.searchParams.set("theme", safeKey);
  history.replaceState({}, "", url);
  applyTheme(safeKey);
}

function setVariant(key) {
  const url = new URL(location.href);
  url.searchParams.set("variant", key);
  history.replaceState({}, "", url);
  render(window.snapshot, key);
}

function cycle(direction) {
  const index = variants.findIndex(({ key }) => key === currentVariant());
  setVariant(variants[(index + direction + variants.length) % variants.length].key);
}

function mark() {
  return `
    <span class="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 40 40" role="img">
        <path d="M10 17a11 11 0 0 1 18-5l3-3v10H21l3-3a6 6 0 0 0-9 2Z" />
        <path d="M30 23a11 11 0 0 1-18 5l-3 3V21h10l-3 3a6 6 0 0 0 9-2Z" />
      </svg>
    </span>`;
}

function nav(active = "overview") {
  const items = [
    ["overview", "Overview", ""],
    ["updates", "Updates", "12"],
    ["catalog", "Catalog", ""],
    ["activity", "Activity", ""],
    ["health", "System health", "1"],
    ["settings", "Settings", ""],
  ];
  return `
    <aside class="side-nav">
      <div class="brand">${mark()}<span>Updatarr</span></div>
      <nav aria-label="Primary">
        ${items
          .map(
            ([id, label, badge]) => `
              <button class="nav-item ${id === active ? "active" : ""}" type="button"${id === active ? ' aria-current="page"' : ""}>
                <span class="nav-icon" aria-hidden="true">${icons[id]}</span>
                <span>${label}</span>${badge ? `<b>${badge}</b>` : ""}
              </button>`,
          )
          .join("")}
      </nav>
      <div class="rail-foot"><span class="presence"></span> Local service</div>
    </aside>`;
}

function topbar(title = "Overview") {
  return `
    <header class="topbar">
      <div class="mobile-brand">${mark()}<strong>Updatarr</strong></div>
      <label class="search"><span aria-hidden="true">⌕</span><input placeholder="Search software" aria-label="Search software" /></label>
      <div class="top-actions"><span class="live-dot"></span><span id="stream-message" role="status" aria-live="polite">Live service</span><button type="button" aria-label="User menu">SO</button></div>
      <h1 class="sr-only">${esc(title)}</h1>
    </header>`;
}

function pill(state, label = state) {
  return `<span class="pill ${esc(state)}">${esc(label)}</span>`;
}

function planSteps(items) {
  return `<ol class="plan-steps" aria-label="Update plan progress">
    ${items
      .map(
        (item, index) => `<li class="${esc(item.state)}">
          <span class="step-index">${index + 1}</span>
          <span><b>${esc(item.step)}</b><small>${esc(item.detail)}</small></span>
        </li>`,
      )
      .join("")}
  </ol>`;
}

function updateTable(updates, compact = false) {
  return `<div class="table-wrap"><table class="update-table ${compact ? "compact" : ""}">
    <thead><tr><th>Software</th><th>Version</th><th>Source</th><th>Download</th><th>Status</th></tr></thead>
    <tbody>${updates
      .map(
        (item) => `<tr>
          <td><b>${esc(item.name)}</b><small>${esc(item.risk === "reboot" ? "Restart recommended" : item.status)}</small></td>
          <td><span class="version-old">${esc(item.from)}</span><span class="version-arrow">→</span><strong>${esc(item.to)}</strong></td>
          <td>${esc(item.source)}</td><td>${esc(item.size)}</td>
          <td>${pill(item.risk, item.risk === "normal" ? "Ready to review" : item.risk === "reboot" ? "Reboot needed" : "Blocked")}</td>
        </tr>`,
      )
      .join("")}</tbody>
  </table></div>`;
}

function variantA(data) {
  return `<div class="app-shell variant-a">${nav()}<div class="page">${topbar()}
    <main id="main" tabindex="-1">
      <section class="page-heading"><div><p>System overview</p><h2>Updates are ready for review</h2><span>Last checked ${esc(data.scan.completed_at)} · ${esc(data.scan.duration_seconds)} seconds</span></div><button class="primary" type="button">Check again</button></section>
      <section class="rail-panel"><div class="section-title"><div><h3>Next update plan</h3><p>One blocked update must wait until the system update finishes.</p></div>${pill("review", "Review needed")}</div>${planSteps(data.plan_steps)}</section>
      <section class="metric-line" aria-label="Update summary">
        <div><strong>${data.summary.ready_to_review}</strong><span>Ready to review</span></div><div><strong>${data.summary.system_updates}</strong><span>System updates</span></div><div><strong>${data.summary.separate_updates}</strong><span>Separate updates</span></div><div><strong>${data.summary.postponed}</strong><span>Postponed</span></div>
      </section>
      <section class="content-section"><div class="section-title"><div><h3>What will change</h3><p>System packages update together. Blocked updates stay visible but are not included.</p></div><button class="quiet" type="button">Review all ${data.summary.ready_to_review}</button></div>${updateTable(data.updates)}</section>
    </main></div>${mobileNav("overview")}</div>`;
}

function sourceCard(source) {
  const labels = { healthy: "Source working", review: "Review needed", current: "Up to date", blocked: "Blocked" };
  return `<article class="source-card ${esc(source.state)}">
    <div class="source-glyph">${esc(source.name.slice(0, 2).toUpperCase())}</div>
    <div><div class="source-line"><h3>${esc(source.name)}</h3>${pill(source.state, labels[source.state] ?? source.state)}</div><p>${esc(source.detail)}</p></div>
    <strong class="source-count">${source.updates_found}<small>updates</small></strong>
  </article>`;
}

function variantB(data) {
  return `<div class="app-shell variant-b">${nav()}<div class="page">${topbar("Update sources")}
    <main id="main" tabindex="-1">
      <section class="board-heading"><div><p>Update sources</p><h2>Every update source in one place</h2></div><div class="scan-stamp"><span class="live-dot"></span><b>Up to date</b><small>${esc(data.scan.completed_at)}</small></div></section>
      <section class="source-board" aria-label="Update sources">${data.update_sources.map(sourceCard).join("")}</section>
      <section class="split-board">
        <div class="native-focus"><div class="section-title"><div><h3>System updates</h3><p>8 repository packages must update together.</p></div>${pill("review", "Update together")}</div><div class="native-number"><strong>8</strong><span>packages</span></div><div class="dependency-map"><span>Core</span><i></i><span>Extra</span><i></i><span>EOS</span></div><button class="primary" type="button">Review system updates</button></div>
        <div class="attention-list"><div class="section-title"><div><h3>Needs attention</h3><p>Resolve these before updating.</p></div></div><article><span class="warning-icon">!</span><div><b>AUR update must wait</b><p>example-git can be reviewed after the system update.</p></div></article><article><span class="pause-icon">Ⅱ</span><div><b>3 updates postponed</b><p>Still visible, but not included in updates ready to review.</p></div></article></div>
      </section>
    </main></div>${mobileNav("overview")}</div>`;
}

function variantC(data) {
  return `<div class="app-shell variant-c">${nav("updates")}<div class="page">${topbar("Review updates")}
    <main id="main" tabindex="-1" class="review-layout">
      <section class="queue-pane"><div class="page-heading"><div><p>Review updates</p><h2>${data.summary.ready_to_review} updates ready to review</h2><span>${data.summary.updates_found} updates found · grouped by how they can be installed</span></div><button class="quiet" type="button">Filters · 2</button></div>
        <div class="group-label"><span class="group-check">8</span><div><b>System updates</b><small>Arch + EndeavourOS · must update together</small></div>${pill("review", "Selected")}</div>
        ${updateTable(data.updates.slice(0, 2), true)}
        <div class="group-label independent"><span class="group-check">4</span><div><b>Updates managed separately</b><small>3 ready to review · 1 blocked</small></div>${pill("healthy", "3 ready")}</div>
        ${updateTable(data.updates.slice(2), true)}
      </section>
      <aside class="review-pane"><div><p>Proposed update plan</p><h2>Review before anything changes</h2></div>${planSteps(data.plan_steps.slice(0, 4))}<dl><div><dt>Download</dt><dd>241 MiB</dd></div><div><dt>Disk change</dt><dd>Unknown</dd></div><div><dt>Reboot</dt><dd>Recommended</dd></div><div><dt>Confirm on this computer</dt><dd>Required</dd></div></dl><div class="block-note"><b>1 update is blocked and not included</b><span>The AUR update can be reviewed after the system update.</span></div><button class="primary wide" type="button">Review ${data.summary.ready_to_review} updates</button><button class="quiet wide" type="button">Save this plan for later</button></aside>
    </main></div>${mobileNav("updates")}</div>`;
}

function mobileNav(active) {
  const items = [
    ["overview", icons.overview, "Overview"],
    ["updates", icons.updates, "Updates"],
    ["activity", icons.activity, "Activity"],
    ["more", "•••", "More"],
  ];
  return `<nav class="mobile-nav" aria-label="Mobile primary">${items
    .map(
      ([id, icon, label]) =>
        `<button type="button" class="${id === active ? "active" : ""}"${id === active ? ' aria-current="page"' : ""}>${icon}<span>${label}</span></button>`,
    )
    .join("")}</nav>`;
}

function switcher(key) {
  const current = variants.find((variant) => variant.key === key);
  const selectedTheme = currentTheme();
  return `<div class="prototype-tools" aria-label="Prototype review controls">
    <div class="prototype-switcher" role="group" aria-label="Prototype variant ${esc(key)} of ${variants.length}">
      <button id="previous-variant" type="button" aria-label="Previous variant">←</button>
      <span role="status" aria-live="polite"><b>${esc(key)}</b> ${esc(current.name)}<small>Throwaway prototype</small></span>
      <button id="next-variant" type="button" aria-label="Next variant">→</button>
    </div>
    <label class="prototype-theme"><span>Preview theme</span><select aria-label="Preview theme">${themes.map(([themeKey, label]) => `<option value="${themeKey}"${themeKey === selectedTheme ? " selected" : ""}>${label}</option>`).join("")}</select></label>
  </div>`;
}

function render(data, key = currentVariant()) {
  const app = document.querySelector("#app");
  const renderer = key === "B" ? variantB : key === "C" ? variantC : variantA;
  app.innerHTML = renderer(data) + switcher(key);
  document.querySelector("#previous-variant").addEventListener("click", () => cycle(-1));
  document.querySelector("#next-variant").addEventListener("click", () => cycle(1));
  document.querySelector(".prototype-theme select").addEventListener("change", (event) => setTheme(event.target.value));
}

async function boot() {
  applyTheme();
  const response = await fetch("/api/v1/status", { credentials: "same-origin" });
  if (!response.ok) throw new Error(`Status request failed: ${response.status}`);
  window.snapshot = await response.json();
  render(window.snapshot);

  const events = new EventSource("/api/v1/events");
  events.addEventListener("scan-progress", (event) => {
    const update = JSON.parse(event.data);
    const target = document.querySelector("#stream-message");
    if (target) target.textContent = update.message;
  });
}

window.addEventListener("popstate", () => {
  applyTheme();
  render(window.snapshot, currentVariant());
});
window.addEventListener("keydown", (event) => {
  const tag = document.activeElement?.tagName;
  if (["INPUT", "TEXTAREA"].includes(tag) || document.activeElement?.isContentEditable) return;
  if (event.key === "ArrowLeft") cycle(-1);
  if (event.key === "ArrowRight") cycle(1);
});

boot().catch((error) => {
  document.querySelector("#app").innerHTML = `<main class="fatal"><h1>Prototype failed to load</h1><p>${esc(error.message)}</p></main>`;
});
