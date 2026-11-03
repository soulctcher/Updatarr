import {
  FormEvent,
  type ReactNode,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import packageMetadata from "../package.json";
import logoGlyph from "./assets/updatarr-loop.png";

const apiBase = new URL("./api/v1/", document.baseURI).pathname.replace(
  /\/$/,
  "",
);
const systemUpdateGroup = "system-update-group";
const supportedApiVersion = 1;
const incompatibleVersionMessage =
  "This page and the Updatarr service use different versions. Refresh after upgrading both.";
const [releaseVersion, releaseBuild = "development"] =
  packageMetadata.version.split("-", 2);
const buildLabel = releaseBuild.toUpperCase();

const themes = [
  ["system", "System"],
  ["light", "Light"],
  ["dark", "Dark"],
  ["amoled", "AMOLED"],
  ["solarized-light", "Solarized Light"],
  ["solarized-dark", "Solarized Dark"],
  ["github-light", "GitHub Light"],
  ["github-dark", "GitHub Dark"],
  ["norse", "Norse"],
  ["nord", "Nord"],
  ["gruvbox-light", "Gruvbox Light"],
  ["gruvbox-dark", "Gruvbox Dark"],
  ["dracula", "Dracula"],
  ["catppuccin-latte", "Catppuccin Latte"],
  ["catppuccin-mocha", "Catppuccin Mocha"],
  ["sepia", "Sepia"],
  ["midnight", "Midnight"],
  ["high-contrast", "High Contrast"],
] as const;

type Task = { id: string; state: string; progress: number; message: string };
type Source = {
  source_id: string;
  name: string;
  scope: string;
  state: string;
  state_label: string;
  message: string;
  software_count: number;
  update_count: number;
  evidence?: { disabled_remotes?: string[]; masks?: string[] };
};
type ChoiceCounts = { postponed: number; skipped: number; paused: number };
type Overview = {
  mode: string;
  snapshot: {
    snapshot_id: string;
    completed_at: string;
    generation: string;
  } | null;
  summary: {
    updates_found: number;
    ready_to_review: number;
    blocked: number;
    restart_needed: number;
    software_recorded: number;
  };
  saved_choices: ChoiceCounts;
  sources: Source[];
  task: Task | null;
};
type Software = {
  stable_id: string;
  source_id: string;
  scope: string;
  software_id: string;
  name: string;
  installed_version: string | null;
  origin: string | null;
  branch: string | null;
  ownership: string;
  source_documentation_url: string;
};
type Update = {
  stable_id: string;
  source_id: string;
  scope: string;
  software_id: string;
  name: string;
  installed_version: string | null;
  available_version: string;
  state: string;
  state_label: string;
  restart_needed: boolean | null;
  summary: string | null;
};
type PlanningIssue = {
  source_id: string;
  name: string;
  stable_ids: string[];
  message: string;
};
type CatalogItem = {
  catalog_id: string;
  source_id: string;
  source_name: string;
  scope: string;
  origin: string;
  software_id: string;
  name: string;
  version: string | null;
  summary: string | null;
  trust: string;
  architecture: string | null;
  branch: string | null;
  note: {
    text: string;
    source_name: string;
    source_url: string;
    observed_at: string;
  } | null;
};
type CatalogState = {
  source_id: string;
  scope: string;
  state: string;
  message: string;
};
type AurPreview = {
  package: string;
  source_url: string;
  content: string;
  content_hash: string;
  comparison_state: string;
  message: string;
  simulated: boolean;
};
type Advisory = {
  advisory_id: string;
  source_name: string;
  title: string;
  summary: string;
  source_url: string;
  published_at: string | null;
  simulated: boolean;
  content_hash: string;
  parse_status: string;
};
type Audit = {
  audit_id: number;
  occurred_at: string;
  kind: string;
  details: Record<string, unknown>;
};
type ImportedHistory = {
  event_id: string;
  source_id: string;
  scope: string;
  occurred_at: string;
  action: string;
  name: string;
  version_before: string | null;
  version_after: string | null;
  completeness: string;
  provenance: string;
};
type ImportBatch = {
  batch_id: string;
  source_id: string;
  scope: string;
  status: string;
  record_count: number;
  skipped_count: number;
  reason: string;
  observed_at: string;
};
type HistoryData = {
  items: Audit[];
  imported_items: ImportedHistory[];
  imported_total: number;
  import_batches: ImportBatch[];
  summary: {
    imported_events: number;
    updatarr_events: number;
    recorded_changes: number;
    download_bytes: number | null;
    download_data_label: string;
  };
};
type Policy = {
  policy_id: string;
  kind: string;
  source_id: string;
  scope: string;
  software_id: string | null;
  target_stable_id: string | null;
  version: string | null;
  expires_at: string | null;
  reason: string | null;
};
type SourceSetting = {
  source_id: string;
  scope: string;
  name: string;
  enabled: boolean;
};
type SelectionDecision = {
  allowed: boolean;
  message: string;
  blocked_reason: string | null;
};
type PlanStep = {
  step_id: string;
  operation: string;
  source_id: string;
  scope: string;
  package_ids: string[];
  permission: string;
  summary: string;
  expected_changes: [string, string | null, string][];
  safe_cancellation: string;
  live_enabled: boolean;
  blocker: string | null;
};
type UpdatePlan = {
  plan_id: string;
  digest: string;
  state: string;
  created_at: string;
  expires_at: string;
  steps: PlanStep[];
  warnings: string[];
  blockers: string[];
  unknowns: string[];
  requires_administrator: boolean;
};
type UpdateRun = {
  run_id: string;
  plan_id: string;
  state: string;
  progress: number;
  message: string;
  started_at: string;
  finished_at: string | null;
};
type SafetyCheck = {
  check_id: string;
  label: string;
  state: string;
  explanation: string;
};
type MaintenanceCandidate = {
  candidate_id: string;
  display_name: string;
  size_bytes: number;
  reason: string;
};
type SafetyItem = {
  capability_id: string;
  category: string;
  name: string;
  state: string;
  summary: string;
  next_step: string;
  restart_action: string;
  checks: SafetyCheck[];
  simulated: boolean;
  details?: {
    observed_sources?: Source[];
    preview?: {
      retention: string;
      candidates: MaintenanceCandidate[];
      total_bytes: number;
      removal_performed: boolean;
    };
  };
};
type View = "overview" | "software" | "updates" | "history" | "settings";

const viewNames: Record<View, string> = {
  overview: "Overview",
  software: "Software",
  updates: "Updates",
  history: "History",
  settings: "Settings",
};

function initialView(): View {
  const requested = new URL(window.location.href).searchParams.get("view");
  return requested && requested in viewNames ? (requested as View) : "overview";
}

async function readError(response: Response): Promise<string> {
  try {
    return (
      (await response.json()).detail ??
      "Updatarr could not complete that request."
    );
  } catch {
    return "Updatarr could not complete that request.";
  }
}
function Mark() {
  return (
    <span className="mark" aria-hidden="true">
      <img src={logoGlyph} alt="" />
    </span>
  );
}
function HelpButton({
  title,
  children,
  kind = "popover",
}: {
  title: string;
  children: ReactNode;
  kind?: "popover" | "wide";
}) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({
    left: 0,
    top: 0,
    maxWidth: 280,
    maxHeight: 300,
  });
  const helpId = useId();
  const closeTimer = useRef<number | null>(null);
  const popoverRef = useRef<HTMLSpanElement | null>(null);
  const showHelp = () => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    closeTimer.current = null;
    setOpen(true);
  };
  const showHelpAt = (x: number, y: number) => {
    const zoom = Number.parseFloat(getComputedStyle(document.body).zoom) || 1;
    const visualLeft = x + 14;
    setPosition({
      left: visualLeft / zoom,
      top: (y + 12) / zoom,
      maxWidth: Math.max(
        120 / zoom,
        (window.innerWidth - visualLeft - 12) / zoom,
      ),
      maxHeight: (window.innerHeight - 20) / zoom,
    });
    showHelp();
  };
  const hideHelpSoon = () => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => {
      setOpen(false);
      closeTimer.current = null;
    }, 800);
  };
  useEffect(
    () => () => {
      if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    },
    [],
  );
  useLayoutEffect(() => {
    const popover = popoverRef.current;
    if (!open || !popover) return;
    const zoom = Number.parseFloat(getComputedStyle(document.body).zoom) || 1;
    const bottomLimit = window.innerHeight / zoom - popover.offsetHeight - 10 / zoom;
    const nextTop = Math.max(10 / zoom, Math.min(position.top, bottomLimit));
    if (nextTop !== position.top) {
      setPosition((current) => ({ ...current, top: nextTop }));
    }
  }, [open, position.left, position.top]);
  return (
    <span
      className={`help-control${open ? " help-open" : ""}`}
      onBlurCapture={hideHelpSoon}
    >
      <button
        className="help-button"
        type="button"
        aria-label={`Information: ${title}`}
        aria-describedby={open ? helpId : undefined}
        onPointerEnter={(event) => showHelpAt(event.clientX, event.clientY)}
        onPointerLeave={hideHelpSoon}
        onFocus={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          showHelpAt(bounds.right, bounds.top);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            if (closeTimer.current !== null) {
              window.clearTimeout(closeTimer.current);
              closeTimer.current = null;
            }
            setOpen(false);
            event.currentTarget.blur();
          }
        }}
      >
        <span aria-hidden="true">i</span>
      </button>
      {open &&
        createPortal(
          <span
            className={`help-popover${kind === "wide" ? " help-popover-wide" : ""}`}
            id={helpId}
            ref={popoverRef}
            role="tooltip"
            style={position}
            onPointerEnter={showHelp}
            onPointerLeave={hideHelpSoon}
          >
            <b>{title}</b>
            <span className="help-copy">{children}</span>
          </span>,
          document.body,
        )}
    </span>
  );
}
function icon(view: View) {
  return view === "overview"
    ? "⌂"
    : view === "software"
      ? "▦"
      : view === "updates"
        ? "↻"
        : view === "history"
          ? "◷"
          : "⚙";
}
function formatTime(value?: string | null) {
  if (!value) return "Not checked yet";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Time unavailable"
    : date.toLocaleString();
}

const titleWordOverrides: Record<string, string> = {
  amoled: "AMOLED",
  api: "API",
  aur: "AUR",
  cpu: "CPU",
  csrf: "CSRF",
  dkms: "DKMS",
  fnm: "fnm",
  fwupd: "fwupd",
  github: "GitHub",
  gpu: "GPU",
  http: "HTTP",
  https: "HTTPS",
  id: "ID",
  kde: "KDE",
  npm: "npm",
  "node.js": "Node.js",
  rustup: "rustup",
  updatarr: "Updatarr",
  url: "URL",
  uv: "uv",
  xdg: "XDG",
};
const minorTitleWords = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "by",
  "for",
  "from",
  "in",
  "of",
  "on",
  "or",
  "the",
  "to",
  "via",
  "with",
]);
function titleCase(value: string) {
  const words = value.split(/\s+/);
  return words
    .map((word, index) => {
      const lower = word.toLowerCase();
      if (titleWordOverrides[lower]) return titleWordOverrides[lower];
      if (/^[A-Z0-9]+$/.test(word)) return word;
      if (index > 0 && index < words.length - 1 && minorTitleWords.has(lower)) {
        return lower;
      }
      return word
        .split("-")
        .map((part) => {
          const partOverride = titleWordOverrides[part.toLowerCase()];
          return partOverride ?? part.charAt(0).toUpperCase() + part.slice(1);
        })
        .join("-");
    })
    .join(" ");
}

function focusDetectedUpdateSource(sourceId: string) {
  const action = document.querySelector<HTMLInputElement>(
    `input[data-update-source="${sourceId}"]`,
  );
  if (!action) return;
  window.requestAnimationFrame(() => {
    action.focus({ preventScroll: true });
    action.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

export function App() {
  const [csrf, setCsrf] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [view, setView] = useState<View>(initialView);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [software, setSoftware] = useState<Software[]>([]);
  const [softwarePage, setSoftwarePage] = useState({
    total: 0,
    limit: 100,
    offset: 0,
  });
  const [updates, setUpdates] = useState<Update[]>([]);
  const [readyUpdateIds, setReadyUpdateIds] = useState<string[]>([]);
  const [planningIssues, setPlanningIssues] = useState<PlanningIssue[]>([]);
  const [history, setHistory] = useState<HistoryData | null>(null);
  const [advisories, setAdvisories] = useState<Advisory[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [sourceSettings, setSourceSettings] = useState<SourceSetting[]>([]);
  const [query, setQuery] = useState("");
  const [theme, setTheme] = useState("system");
  const [activity, setActivity] = useState("Ready to check");
  const [selected, setSelected] = useState<string[]>([]);
  const [selectionDecision, setSelectionDecision] =
    useState<SelectionDecision | null>(null);
  const [plan, setPlan] = useState<UpdatePlan | null>(null);
  const [run, setRun] = useState<UpdateRun | null>(null);
  const [safetyItems, setSafetyItems] = useState<SafetyItem[]>([]);
  const softwareRequest = useRef(0);
  const appliedSoftwareQuery = useRef("");
  const signedIn = csrf !== null;
  const pathLabel = useMemo(
    () => (view === "settings" ? "Settings" : viewNames[view]),
    [view],
  );

  useEffect(() => {
    if (theme === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
  }, [theme]);
  async function loadOverview() {
    const response = await fetch(`${apiBase}/overview`);
    if (response.ok) {
      const body: Overview = await response.json();
      setOverview(body);
      if (body.task?.message) setActivity(body.task.message);
    }
  }
  async function loadAdvisories() {
    const response = await fetch(`${apiBase}/advisories?limit=5`);
    if (response.ok) setAdvisories((await response.json()).items);
  }
  async function loadPolicies() {
    const response = await fetch(`${apiBase}/policies`);
    if (response.ok) setPolicies((await response.json()).items);
  }
  async function loadSettings() {
    const response = await fetch(`${apiBase}/settings/update-sources`);
    if (response.ok) setSourceSettings((await response.json()).items);
    await loadPolicies();
  }
  async function loadUpdates() {
    const response = await fetch(`${apiBase}/updates`);
    if (response.ok) {
      const body = await response.json();
      setUpdates(body.items);
      setReadyUpdateIds(body.readiness?.ready_stable_ids ?? []);
      setPlanningIssues(body.readiness?.issues ?? []);
      setSelected((current) =>
        current.filter((id) =>
          body.items.some((item: Update) => item.stable_id === id),
        ),
      );
    }
  }
  async function loadPlan() {
    const response = await fetch(`${apiBase}/plans/latest`);
    if (response.ok) {
      const body = await response.json();
      setPlan(body.plan);
      setRun(
        body.run && body.plan && body.run.plan_id === body.plan.plan_id
          ? body.run
          : null,
      );
    }
  }
  async function loadSafetyReadiness() {
    const response = await fetch(`${apiBase}/safety-readiness`);
    if (response.ok) setSafetyItems((await response.json()).items);
  }
  async function loadHistory() {
    const response = await fetch(`${apiBase}/history?limit=100`);
    if (response.ok) setHistory(await response.json());
  }
  async function loadView(
    target: View,
    filter = appliedSoftwareQuery.current,
    offset = 0,
  ) {
    if (target === "software") {
      const requestId = ++softwareRequest.current;
      const response = await fetch(
        `${apiBase}/inventory?limit=100&offset=${offset}&q=${encodeURIComponent(filter)}`,
      );
      if (response.ok && requestId === softwareRequest.current) {
        const body = await response.json();
        setSoftware(body.items);
        appliedSoftwareQuery.current = filter;
        setSoftwarePage({
          total: body.total,
          limit: body.limit,
          offset: body.offset,
        });
      }
    } else if (target === "updates")
      await Promise.all([
        loadUpdates(),
        loadPolicies(),
        loadPlan(),
        loadSafetyReadiness(),
      ]);
    else if (target === "history") await loadHistory();
    else if (target === "settings") await loadSettings();
  }
  async function refreshM2() {
    await Promise.all([
      loadOverview(),
      loadUpdates(),
      loadPolicies(),
      loadSettings(),
    ]);
  }
  useEffect(() => {
    fetch(`${apiBase}/session`).then(async (response) => {
      if (response.ok) {
        const body = await response.json();
        if (body.api_version !== supportedApiVersion) {
          setError(incompatibleVersionMessage);
          return;
        }
        setCsrf(body.csrf_token);
        setTheme(body.theme ?? "system");
        await Promise.all([loadOverview(), loadAdvisories()]);
      }
    });
  }, []);
  useEffect(() => {
    if (signedIn) void loadView(view);
  }, [view, signedIn]);
  useEffect(() => {
    if (!signedIn) return;
    const events = new EventSource(`${apiBase}/events`);
    const progress = (event: Event) => {
      const detail = JSON.parse((event as MessageEvent).data);
      setActivity(detail.message);
      setOverview((current) =>
        current ? { ...current, task: detail } : current,
      );
    };
    events.addEventListener("check-progress", progress);
    events.addEventListener("check-complete", (event) => {
      progress(event);
      void loadOverview();
      void loadView(view, appliedSoftwareQuery.current);
    });
    events.addEventListener("check-error", progress);
    events.addEventListener("check-cancelled", progress);
    events.addEventListener("reset", () => {
      void loadOverview();
      void loadView(view, appliedSoftwareQuery.current);
    });
    return () => events.close();
  }, [signedIn, view]);
  useEffect(() => {
    if (!signedIn || view !== "updates" || run?.state !== "running") return;
    const timer = window.setInterval(() => void loadPlan(), 300);
    return () => window.clearInterval(timer);
  }, [signedIn, view, run?.state]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${apiBase}/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const body = await response.json();
    if (body.api_version !== supportedApiVersion) {
      setError(incompatibleVersionMessage);
      return;
    }
    setCsrf(body.csrf_token);
    setTheme(body.theme ?? "system");
    setPassword("");
    await Promise.all([loadOverview(), loadAdvisories()]);
  }
  async function startCheck() {
    if (!csrf) return;
    setError("");
    const response = await fetch(`${apiBase}/checks`, {
      method: "POST",
      headers: { "X-CSRF-Token": csrf },
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const body = await response.json();
    setActivity(body.task.message);
    setOverview((current) =>
      current ? { ...current, task: body.task } : current,
    );
  }
  async function logout() {
    if (csrf)
      await fetch(`${apiBase}/session`, {
        method: "DELETE",
        headers: { "X-CSRF-Token": csrf },
      });
    setCsrf(null);
    setOverview(null);
    setView("overview");
  }
  async function chooseTheme(value: string) {
    const prior = theme;
    setTheme(value);
    if (!csrf) return;
    const response = await fetch(`${apiBase}/settings/appearance`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ theme: value }),
    });
    if (!response.ok) {
      setTheme(prior);
      setError(await readError(response));
    }
  }
  async function addChoice(update: Update, kind: string) {
    if (!csrf || !kind) return;
    const grouped =
      update.source_id === "native" &&
      (kind === "postpone" || kind === "pause_software");
    const expiresAt =
      kind === "postpone"
        ? new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
        : null;
    const response = await fetch(`${apiBase}/policies`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({
        kind,
        source_id: update.source_id,
        scope: update.scope,
        software_id: grouped ? systemUpdateGroup : update.software_id,
        target_stable_id: grouped ? null : update.stable_id,
        version: kind === "skip_version" ? update.available_version : null,
        expires_at: expiresAt,
        reason: grouped
          ? "Saved for the whole system update group"
          : "Saved from Review updates",
      }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    setSelectionDecision(null);
    await refreshM2();
  }
  async function removeChoice(policyId: string) {
    await removeChoices([policyId]);
  }
  async function removeChoices(policyIds: string[]) {
    if (!csrf) return;
    for (const policyId of [...new Set(policyIds)]) {
      const response = await fetch(
        `${apiBase}/policies/${encodeURIComponent(policyId)}`,
        { method: "DELETE", headers: { "X-CSRF-Token": csrf } },
      );
      if (!response.ok) {
        setError(await readError(response));
        return;
      }
    }
    await refreshM2();
  }
  async function checkSelection() {
    if (!csrf || !overview?.snapshot) return;
    const response = await fetch(`${apiBase}/update-selection/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({
        snapshot_id: overview.snapshot.snapshot_id,
        selected_stable_ids: selected,
      }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    setSelectionDecision(await response.json());
  }
  async function preparePlan(selectedIds = selected) {
    if (!csrf || !overview?.snapshot) return;
    const response = await fetch(`${apiBase}/plans`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({
        snapshot_id: overview.snapshot.snapshot_id,
        selected_stable_ids: selectedIds,
      }),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const body = await response.json();
    setPlan(body.plan);
    setRun(null);
    setActivity("Update plan ready to review");
  }
  async function approvePlan() {
    if (!csrf || !plan) return;
    const response = await fetch(
      `${apiBase}/plans/${encodeURIComponent(plan.plan_id)}/review`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ digest: plan.digest }),
      },
    );
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    setPlan((await response.json()).plan);
    setActivity("Waiting for confirmation on this computer");
  }
  async function toggleSource(setting: SourceSetting, enabled: boolean) {
    if (!csrf) return;
    const response = await fetch(
      `${apiBase}/settings/update-sources/${encodeURIComponent(setting.source_id)}/${encodeURIComponent(setting.scope)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ enabled }),
      },
    );
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    await refreshM2();
  }
  async function importHistory() {
    if (!csrf) return;
    const response = await fetch(`${apiBase}/history/import`, {
      method: "POST",
      headers: { "X-CSRF-Token": csrf },
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const body = await response.json();
    setActivity(
      body.added
        ? `${body.added} earlier changes added`
        : "History is already current",
    );
    await loadHistory();
  }
  function navigate(target: View) {
    setView(target);
    setError("");
    setSelectionDecision(null);
  }
  function showOverviewCheck() {
    navigate("overview");
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        const button = document.getElementById("check-software");
        button?.focus({ preventScroll: true });
        button?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
  }

  if (!signedIn)
    return (
      <main className="login-page">
        <form className="login-card" onSubmit={login}>
          <div className="brand-lockup">
            <Mark />
            <div>
              <b>Updatarr</b>
              <span>Controlled change, clearly shown</span>
            </div>
          </div>
          <div className="heading-with-help">
            <h1>Sign In</h1>
            <HelpButton title="About Sign In">
              <p>
                This build can prepare and safely demonstrate reviewed update
                plans. It cannot install or remove software.
              </p>
              <p>
                Use the password set for this Updatarr installation.
              </p>
            </HelpButton>
          </div>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button className="primary" type="submit">
            Sign in
          </button>
        </form>
      </main>
    );

  const views = Object.keys(viewNames) as View[];
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand-lockup">
          <Mark />
          <div>
            <b>Updatarr</b>
            <span>Update control</span>
          </div>
        </div>
        <nav aria-label="Main navigation">
          {views.map((item) => (
            <button
              key={item}
              aria-current={view === item ? "page" : undefined}
              className={view === item ? "active" : ""}
              onClick={() => navigate(item)}
            >
              <span className="nav-glyph" aria-hidden="true">
                {icon(item)}
              </span>
              {viewNames[item]}
            </button>
          ))}
        </nav>
        <div className="safe-mode">
          <b>Safe Preview Build</b>
          <span>Plans can be simulated; live software cannot change</span>
        </div>
        <div className="build-stamp">
          Version {releaseVersion} <span aria-hidden="true">·</span> Build{" "}
          {buildLabel}
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>{pathLabel}</span>
          <div>
            <span className="live-status" role="status" aria-live="polite">
              <span className="live-dot" />
              {activity}
            </span>
            <button className="quiet" onClick={logout}>
              Sign out
            </button>
          </div>
        </header>
        <main className="content">
          {error && (
            <p className="error page-error" role="alert">
              {error}
            </p>
          )}
          {view === "settings" ? (
            <Settings
              theme={theme}
              setTheme={chooseTheme}
              sources={sourceSettings}
              toggleSource={toggleSource}
              policies={policies}
              removeChoice={removeChoice}
            />
          ) : view === "history" ? (
            <History data={history} importHistory={importHistory} />
          ) : view === "software" ? (
            <SoftwarePage
              items={software}
              page={softwarePage}
              query={query}
              setQuery={setQuery}
              search={(value) => loadView("software", value, 0)}
              changePage={(offset) =>
                loadView("software", appliedSoftwareQuery.current, offset)
              }
            />
          ) : view === "updates" ? (
            <Updates
              items={updates}
              readyUpdateIds={readyUpdateIds}
              planningIssues={planningIssues}
              safetyItems={safetyItems}
              policies={policies}
              checkedAt={overview?.snapshot?.completed_at}
              selected={selected}
              setSelected={setSelected}
              decision={selectionDecision}
              checkSelection={checkSelection}
              preparePlan={() => preparePlan()}
              updateReadySoftware={(readyIds) => {
                setSelected(readyIds);
                void preparePlan(readyIds);
              }}
              checkAgain={startCheck}
              approvePlan={approvePlan}
              plan={plan}
              run={run}
              addChoice={addChoice}
              removeChoices={removeChoices}
              showOverviewCheck={showOverviewCheck}
            />
          ) : (
            <OverviewPage
              data={overview}
              advisories={advisories}
              startCheck={startCheck}
            />
          )}
        </main>
      </div>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {views.map((item) => (
          <button
            key={item}
            aria-label={viewNames[item]}
            aria-current={view === item ? "page" : undefined}
            className={view === item ? "active" : ""}
            onClick={() => navigate(item)}
          >
            {icon(item)}
            <span>{item}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

function OverviewPage({
  data,
  advisories,
  startCheck,
}: {
  data: Overview | null;
  advisories: Advisory[];
  startCheck: () => void;
}) {
  if (!data)
    return (
      <Empty
        title="Loading Overview"
        text="Updatarr is getting the latest recorded information."
      />
    );
  const checking = data.task?.state === "checking";
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Managed computer</p>
          <div className="heading-with-help">
            <h1>Software Overview</h1>
            <HelpButton kind="wide" title="How Overview Works">
              <p>
                Overview shows the most recent software check. It keeps ready
                updates, blocked updates and saved choices separate.
              </p>
              <p>
                <b>Check software</b> reads the configured update sources. It
                does not install anything.
              </p>
            </HelpButton>
          </div>
          <p>
            Records installed software and checks for newer versions only where
            the update source supports it. <b>Not checked</b> means installed
            software was recorded, but newer versions were not checked.
          </p>
        </div>
        <button
          className="primary"
          id="check-software"
          disabled={checking}
          onClick={startCheck}
        >
          {checking ? "Checking…" : "Check software"}
        </button>
      </div>
      <section className="process" aria-label="Update process">
        <ol>
          {[
            "Check",
            "Review",
            "Confirm here",
            "Allow access",
            "Verify results",
          ].map((step, index) => (
            <li className={index === 0 ? "current" : ""} key={step}>
              <span>{index + 1}</span>
              <b>{step}</b>
            </li>
          ))}
        </ol>
        {checking && (
          <div
            className="progress"
            role="progressbar"
            aria-label="Software check progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={data.task?.progress ?? 0}
          >
            <span style={{ width: `${data.task?.progress ?? 0}%` }} />
          </div>
        )}
      </section>
      <section className="metrics" aria-label="Recorded software summary">
        <Metric
          value={data.summary.software_recorded}
          label="software recorded"
        />
        <Metric value={data.summary.ready_to_review} label="ready to review" />
        <Metric
          value={
            data.saved_choices.postponed +
            data.saved_choices.paused +
            data.saved_choices.skipped
          }
          label="saved choices"
        />
        <Metric value={data.summary.blocked} label="blocked" />
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <div className="heading-with-help">
              <h2>Update Sources</h2>
              <HelpButton title="About Update Sources">
                <p>
                  Each source reports separately. If one source cannot be
                  checked, its missing results remain visible instead of being
                  treated as up to date.
                </p>
              </HelpButton>
            </div>
            <small className="checked-time">
              Last completed: {formatTime(data.snapshot?.completed_at)}
            </small>
          </div>
          <span className="mode">{data.mode}</span>
        </div>
        <div className="source-grid">
          {data.sources.map((source) => (
            <article key={`${source.source_id}-${source.scope}`}>
              <span className="source-icon">
                {source.name.slice(0, 2).toUpperCase()}
              </span>
              <div>
                <h3>{titleCase(source.name)}</h3>
                <span className={`status ${statusClass(source.state)}`}>
                  {source.state_label}
                </span>
                <p>{source.message}</p>
                {source.source_id === "flatpak" && source.evidence && (
                  <small>
                    {source.evidence.disabled_remotes?.length ?? 0} turned-off
                    Flatpak sources · {source.evidence.masks?.length ?? 0}{" "}
                    existing Flatpak update blocks
                  </small>
                )}
              </div>
              <strong>
                {source.software_count}
                <small>recorded</small>
              </strong>
            </article>
          ))}
        </div>
      </section>
      <section className="panel advisory-panel">
        <div className="section-heading">
          <div className="heading-with-help">
            <h2>Notices Before Updating</h2>
            <HelpButton title="About Update Notices">
              <p>
                Updatarr shows official source information as plain text and
                links back to the original source.
              </p>
            </HelpButton>
          </div>
        </div>
        {advisories.length === 0 ? (
          <p>No notices have been checked.</p>
        ) : (
          advisories.map((item) => (
            <article key={item.advisory_id}>
              <div>
                <h3>{titleCase(item.title)}</h3>
                <p>{item.summary}</p>
                <small>
                  {item.source_name}
                  {item.simulated ? " · Safe preview" : ""}
                  {item.published_at ? ` · ${item.published_at}` : ""}
                </small>
              </div>
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Read at source
              </a>
            </article>
          ))
        )}
      </section>
    </>
  );
}
function Metric({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function SoftwarePage({
  items,
  page,
  query,
  setQuery,
  search,
  changePage,
}: {
  items: Software[];
  page: { total: number; limit: number; offset: number };
  query: string;
  setQuery: (value: string) => void;
  search: (value: string) => void;
  changePage: (offset: number) => void;
}) {
  const [mode, setMode] = useState<"installed" | "catalog">("installed");
  const [catalogQuery, setCatalogQuery] = useState("kdenlive");
  const [catalogItems, setCatalogItems] = useState<CatalogItem[]>([]);
  const [catalogStates, setCatalogStates] = useState<CatalogState[]>([]);
  const [catalogComplete, setCatalogComplete] = useState<boolean | null>(null);
  const [aurPreview, setAurPreview] = useState<AurPreview | null>(null);
  const [source, setSource] = useState("all");
  const [catalogError, setCatalogError] = useState("");
  async function findCatalog(event: FormEvent) {
    event.preventDefault();
    setCatalogError("");
    const params = new URLSearchParams({ q: catalogQuery, limit: "60" });
    if (source !== "all") {
      const [sourceId = "", scope] = source.split(":");
      params.set("source_id", sourceId);
      if (scope) params.set("scope", scope);
    }
    const response = await fetch(`${apiBase}/catalog?${params}`);
    if (!response.ok) {
      setCatalogError(await readError(response));
      return;
    }
    const body = await response.json();
    setCatalogItems(body.items);
    setCatalogStates(body.sources);
    setCatalogComplete(body.complete);
    setAurPreview(null);
  }
  async function previewAur(packageName: string) {
    setCatalogError("");
    const response = await fetch(
      `${apiBase}/catalog/aur/${encodeURIComponent(packageName)}/build-preview`,
    );
    if (!response.ok) {
      setCatalogError(await readError(response));
      return;
    }
    setAurPreview(await response.json());
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Software sources</p>
          <div className="heading-with-help">
            <h1>Software</h1>
            <HelpButton kind="wide" title="How Software Works">
              <p>
                <b>Installed</b> shows software already recorded on this
                computer. Select a software name to open its source
                documentation.
              </p>
              <p>
                <b>Find new software</b> searches each source separately.
                Similar names remain separate so you can see where each result
                comes from and where it would be installed.
              </p>
            </HelpButton>
          </div>
          <p>View installed software or search the available sources.</p>
        </div>
      </div>
      <div className="segmented" role="group" aria-label="Software view">
        <button
          className={mode === "installed" ? "active" : ""}
          onClick={() => setMode("installed")}
        >
          Installed
        </button>
        <button
          className={mode === "catalog" ? "active" : ""}
          onClick={() => setMode("catalog")}
        >
          Find new software
        </button>
      </div>
      {mode === "installed" ? (
        <>
          <form
            className="filter-bar"
            onSubmit={(event) => {
              event.preventDefault();
              search(
                String(
                  new FormData(event.currentTarget).get("software-search") ??
                    "",
                ),
              );
            }}
          >
            <label htmlFor="software-search">Find software</label>
            <input
              id="software-search"
              name="software-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, package, or update source"
            />
            <button className="quiet">Search</button>
          </form>
          {items.length === 0 ? (
            <Empty
              title={query ? "No Matching Software" : "No Software Recorded"}
              text={
                query
                  ? "No recorded software matches this search."
                  : "Run a read-only software check from Overview."
              }
            />
          ) : (
            <>
              <nav className="table-pager" aria-label="Installed software pages">
                <span aria-live="polite">
                  {page.offset + 1}–{Math.min(page.offset + items.length, page.total)} of{" "}
                  {page.total.toLocaleString()} recorded
                </span>
                <div>
                  <button
                    className="quiet"
                    disabled={page.offset === 0}
                    onClick={() => changePage(Math.max(0, page.offset - page.limit))}
                  >
                    Previous
                  </button>
                  <button
                    className="quiet"
                    disabled={page.offset + page.limit >= page.total}
                    onClick={() => changePage(page.offset + page.limit)}
                  >
                    Next
                  </button>
                </div>
              </nav>
              <section className="panel table-panel">
                <div className="table-wrap software-table-wrap">
                  <table>
                  <thead>
                    <tr>
                      <th>Software</th>
                      <th>Installed Version</th>
                      <th>Update Source</th>
                      <th>Installed For</th>
                      <th>Managed By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.stable_id}>
                        <td>
                          <a
                            className="software-link"
                            href={item.source_documentation_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <b>{item.name}</b>
                            {item.name.trim().toLocaleLowerCase() !==
                              item.software_id.trim().toLocaleLowerCase() && (
                              <small>{item.software_id}</small>
                            )}
                          </a>
                        </td>
                        <td>{item.installed_version ?? "Unknown"}</td>
                        <td>{sourceLabel(item.source_id)}</td>
                        <td>{scopeLabel(item.scope)}</td>
                        <td>{ownershipLabel(item.ownership)}</td>
                      </tr>
                    ))}
                  </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </>
      ) : (
        <>
          <form className="catalog-search" onSubmit={findCatalog}>
            <div className="form-label-with-help">
              <label htmlFor="catalog-search">
                <b>Find new software</b>
              </label>
              <HelpButton title="About Search Results">
                <p>
                  Results stay separate by update source and installation place.
                  Updatarr will not silently switch one source for another.
                </p>
              </HelpButton>
            </div>
            <div>
              <input
                id="catalog-search"
                value={catalogQuery}
                onChange={(event) => setCatalogQuery(event.target.value)}
              />
              <select
                aria-label="Search source"
                value={source}
                onChange={(event) => setSource(event.target.value)}
              >
                <option value="all">All available sources</option>
                <option value="native:system">Arch repositories</option>
                <option value="aur:user">AUR (user-submitted)</option>
                <option value="flatpak:user">Flatpak for current user</option>
                <option value="flatpak:system">Flatpak for whole system</option>
              </select>
              <button className="primary">Search sources</button>
            </div>
          </form>
          {catalogError && (
            <p className="error" role="alert">
              {catalogError}
            </p>
          )}
          {catalogStates.length > 0 && (
            <div className="source-notices">
              {catalogStates
                .filter((item) => item.state !== "source_working")
                .map((item) => (
                  <p key={`${item.source_id}-${item.scope}`}>
                    <b>
                      {sourceLabel(item.source_id)} · {scopeLabel(item.scope)}
                    </b>
                    {item.message}
                  </p>
                ))}
            </div>
          )}
          {catalogComplete === false && (
            <p className="decision refused" role="status">
              <b>Some results are not shown</b>
              <span>
                The sources reported more results or could not complete a check.
                Narrow the search or choose one source.
              </span>
            </p>
          )}
          {aurPreview && (
            <section className="panel aur-preview">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">AUR build-file preview</p>
                  <div className="heading-with-help">
                    <h2>{aurPreview.package}</h2>
                    <HelpButton title="About This Preview">
                      <p>
                        This is the build file provided by the AUR source.
                        Review changes before allowing a build. Updatarr shows
                        it as plain text and does not run it from this screen.
                      </p>
                    </HelpButton>
                  </div>
                  <p>{aurPreview.message}</p>
                </div>
                <a
                  href={aurPreview.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View at source
                </a>
              </div>
              <pre>{aurPreview.content}</pre>
              <small>
                Shown as plain text · File check code{" "}
                {aurPreview.content_hash.slice(0, 12)}…
                {aurPreview.simulated ? " · Safe preview" : ""}
              </small>
            </section>
          )}
          {catalogItems.length === 0 ? (
            <Empty
              title="Search the Software Sources"
              text="Choose an exact source when similarly named results appear."
            />
          ) : (
            <section className="panel table-panel">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Software</th>
                      <th>Version</th>
                      <th>Source</th>
                      <th>Install For</th>
                      <th>What the Source Says</th>
                    </tr>
                  </thead>
                  <tbody>
                    {catalogItems.map((item) => {
                      const documentationUrl = catalogDocumentationUrl(item);
                      return (
                        <tr key={item.catalog_id}>
                          <td>
                            <a
                              className="software-link"
                              href={documentationUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <b>{item.name}</b>
                              <small>{item.software_id}</small>
                            </a>
                          </td>
                          <td>{item.version ?? "Not provided"}</td>
                          <td>
                            <b>{item.source_name}</b>
                            <small>{item.origin}</small>
                          </td>
                          <td>{scopeLabel(item.scope)}</td>
                          <td className="notes-cell">
                            <span>
                              {item.summary ?? "No description provided"}
                            </span>
                            <small>{item.trust}</small>
                            <a
                              href={documentationUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Read source documentation
                            </a>
                            {item.source_id === "aur" && (
                              <button
                                className="link-button"
                                type="button"
                                onClick={() =>
                                  void previewAur(item.software_id)
                                }
                              >
                                Preview build file
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </>
  );
}

function Updates({
  items,
  readyUpdateIds,
  planningIssues,
  safetyItems,
  policies,
  checkedAt,
  selected,
  setSelected,
  decision,
  checkSelection,
  preparePlan,
  updateReadySoftware,
  checkAgain,
  approvePlan,
  plan,
  run,
  addChoice,
  removeChoices,
  showOverviewCheck,
}: {
  items: Update[];
  readyUpdateIds: string[];
  planningIssues: PlanningIssue[];
  safetyItems: SafetyItem[];
  policies: Policy[];
  checkedAt?: string;
  selected: string[];
  setSelected: (value: string[]) => void;
  decision: SelectionDecision | null;
  checkSelection: () => void;
  preparePlan: () => void;
  updateReadySoftware: (readyIds: string[]) => void;
  checkAgain: () => void;
  approvePlan: () => void;
  plan: UpdatePlan | null;
  run: UpdateRun | null;
  addChoice: (item: Update, kind: string) => void;
  removeChoices: (ids: string[]) => void;
  showOverviewCheck: () => void;
}) {
  const [technicalDetailsOpen, setTechnicalDetailsOpen] = useState(false);
  function toggle(id: string, checked: boolean) {
    setSelected(
      checked
        ? [...new Set([...selected, id])]
        : selected.filter((value) => value !== id),
    );
  }
  function savedChoices(item: Update) {
    return policies.filter(
      (policy) =>
        policy.source_id === item.source_id &&
        policy.scope === item.scope &&
        (policy.software_id === systemUpdateGroup ||
          policy.target_stable_id === item.stable_id) &&
        (policy.kind !== "skip_version" ||
          policy.version === item.available_version),
    );
  }
  const order: Record<string, number> = {
    blocked: 0,
    not_checked: 1,
    not_supported: 2,
    ready: 3,
  };
  const orderedSafety = [...safetyItems].sort(
    (left, right) => (order[left.state] ?? 4) - (order[right.state] ?? 4),
  );
  const safetyCounts = safetyItems.reduce(
    (counts, item) => ({
      ...counts,
      [item.state]: (counts[item.state] ?? 0) + 1,
    }),
    {} as Record<string, number>,
  );
  const attentionCount = safetyCounts.blocked ?? 0;
  const readyUpdateSet = new Set(readyUpdateIds);
  const updateIds = items.map((item) => item.stable_id);
  const selectedUpdateCount = updateIds.filter((id) =>
    selected.includes(id),
  ).length;
  const allUpdatesSelected =
    updateIds.length > 0 && selectedUpdateCount === updateIds.length;
  const someUpdatesSelected = selectedUpdateCount > 0 && !allUpdatesSelected;
  return (
    <>
      <div className="page-heading ready-updates-heading">
        <div>
          <p className="eyebrow">Software ready now</p>
          <div className="heading-with-help">
            <h1>Ready Updates</h1>
            <HelpButton kind="wide" title="How Ready Updates Work">
              <p>
                Updatarr shows which updates are ready to plan from the checks
                completed so far. Choose <b>Update Ready Software</b> to review
                the exact changes before anything begins.
              </p>
              <dl className="help-choices">
                <div>
                  <dt>Postpone for 24 hours</dt>
                  <dd>
                    Wait one day, then return to the status reported by the
                    update source.
                  </dd>
                </div>
                <div>
                  <dt>Skip this version</dt>
                  <dd>
                    Set aside only the version shown. A newer version will
                    appear for review.
                  </dd>
                </div>
                <div>
                  <dt>Pause until resumed</dt>
                  <dd>
                    Keep this software and future versions waiting until you
                    remove the saved choice.
                  </dd>
                </div>
              </dl>
              <p>
                Choose <b>Remove saved choice</b> to return software to the
                status reported by its update source.
              </p>
            </HelpButton>
          </div>
          <p>
            {items.length} {items.length === 1 ? "update was" : "updates were"}{" "}
            found; {readyUpdateIds.length} {readyUpdateIds.length === 1 ? "is" : "are"}{" "}
            ready from the last check at {formatTime(checkedAt)}.
          </p>
        </div>
        <button className="quiet" onClick={checkAgain}>Check Again</button>
      </div>
      {items.length > 0 && (
        <section className="panel ready-update-worklist" aria-labelledby="ready-update-list-title">
          <div className="section-heading">
            <div>
              <h2 id="ready-update-list-title">Updates Found</h2>
              <p>Review the short list. Open details only when you need them.</p>
            </div>
            <span className="status ready">{readyUpdateIds.length} Ready</span>
          </div>
          <ul className="ready-update-list">
            {items.map((item) => {
              const choices = savedChoices(item);
              const needsAttention =
                choices.length === 0 && !readyUpdateSet.has(item.stable_id);
              return (
                <li className={needsAttention ? "needs-attention" : ""} key={`ready-${item.stable_id}-${item.available_version}`}>
                  <div>
                    <b>{item.name}</b>
                    <span>{sourceLabel(item.source_id)} · {item.installed_version ?? "Not installed"} → {item.available_version}</span>
                  </div>
                  {needsAttention ? (
                    <span className="status blocked">Needs Attention</span>
                  ) : choices.length > 0 ? (
                    <button className="quiet compact" onClick={() => void removeChoices(choices.map((choice) => choice.policy_id))}>
                      Remove Saved Choice
                    </button>
                  ) : (
                    <select
                      aria-label={`Choice for ${item.name}`}
                      defaultValue=""
                      onChange={(event) => {
                        const value = event.target.value;
                        event.target.value = "";
                        void addChoice(item, value);
                      }}
                    >
                      <option value="">Ready</option>
                      <option value="postpone">Wait 24 Hours</option>
                      <option value="skip_version">Skip This Version</option>
                      <option value="pause_software">Pause This Software</option>
                    </select>
                  )}
                </li>
              );
            })}
          </ul>
          {planningIssues.length > 0 && (
            <section className="ready-issues" aria-labelledby="ready-issues-title">
              <div>
                <h3 id="ready-issues-title">{planningIssues.length} {planningIssues.length === 1 ? "Item Needs" : "Items Need"} Attention</h3>
                <p>Open an item only when you need its instructions.</p>
              </div>
              {planningIssues.map((issue) => (
                <details key={`issue-${issue.source_id}-${issue.stable_ids.join("-")}`}>
                  <summary>{titleCase(issue.name)}</summary>
                  <p>{issue.message}</p>
                  {issue.source_id === "firmware" ? (
                    <button className="quiet compact" type="button" onClick={checkAgain}>Check Again</button>
                  ) : issue.source_id === "native" ? (
                    <button
                      className="quiet compact"
                      type="button"
                      onClick={() => {
                        setTechnicalDetailsOpen(true);
                        window.requestAnimationFrame(() => focusDetectedUpdateSource("native"));
                      }}
                    >
                      Review System Package Updates
                    </button>
                  ) : null}
                </details>
              ))}
            </section>
          )}
          <div className="ready-update-actions">
            <p>You will review the exact plan and confirm it on this computer before updates begin.</p>
            <button
              className="primary"
              disabled={readyUpdateIds.length === 0}
              onClick={() => updateReadySoftware(readyUpdateIds)}
            >
              Update Ready Software
            </button>
          </div>
        </section>
      )}
      {decision && (
        <section
          className={`decision ${decision.allowed ? "allowed" : "refused"}`}
          role="status"
        >
          <div>
            <b>
              {decision.allowed
                ? "Selection can be planned"
                : "Selection blocked"}
            </b>
            <span>{decision.message}</span>
            {decision.blocked_reason && (
              <small>{decision.blocked_reason}</small>
            )}
          </div>
          {decision.allowed && (
            <button className="primary" onClick={preparePlan}>
              Prepare update plan
            </button>
          )}
        </section>
      )}
      {plan && <PlanReview plan={plan} run={run} approve={approvePlan} />}
      <details
        className="workflow-details"
        open={technicalDetailsOpen}
        onToggle={(event) => setTechnicalDetailsOpen(event.currentTarget.open)}
      >
        <summary>Safety and technical details</summary>
        {items.length > 0 && (
          <div className="technical-actions">
            <p>Select individual rows below only when you do not want to update everything that is ready.</p>
            <button className="quiet" onClick={checkSelection}>Check Whether Selection Is Safe</button>
          </div>
        )}
      {safetyItems.length > 0 && (
        <section
          className="panel safety-readiness"
          aria-labelledby="safety-readiness-title"
        >
          <div className="checklist-header">
            <div>
              <p className="eyebrow">Before updates begin</p>
              <div className="heading-with-help">
                <h2 id="safety-readiness-title">Safety Checklist</h2>
                <HelpButton title="About the Safety Checklist">
                  <p>
                    Updatarr runs these checks for you. You do not need to tick
                    anything. Review the result, fix items that need attention,
                    and open a row only when you need more detail.
                  </p>
                  <p>
                    This checklist is a preview and cannot change the computer.
                  </p>
                </HelpButton>
              </div>
              <p
                className={`checklist-result ${attentionCount ? "has-attention" : "all-clear"}`}
              >
                {attentionCount
                  ? `${attentionCount} ${attentionCount === 1 ? "item needs" : "items need"} attention before every update type is ready.`
                  : "No known problem is blocking these update types."}
              </p>
            </div>
            <div
              className="checklist-counts"
              aria-label="Safety checklist summary"
            >
              <span className="count-ready">
                <b>{safetyCounts.ready ?? 0}</b> passed
              </span>
              <span className="count-blocked">
                <b>{attentionCount}</b> need attention
              </span>
              <span>
                <b>{safetyCounts.not_checked ?? 0}</b> not checked
              </span>
              <span>
                <b>{safetyCounts.not_supported ?? 0}</b> not supported
              </span>
            </div>
          </div>
          <ul className="safety-checklist">
            {orderedSafety.map((item) => {
              const statusAction =
                item.state === "blocked" &&
                item.capability_id.startsWith("firmware")
                  ? {
                      label: "check software again from Overview",
                      run: showOverviewCheck,
                    }
                  : item.state === "blocked" &&
                      item.capability_id === "npm:system" &&
                      items.some((update) => update.source_id === "native")
                    ? {
                        label: "review system package updates",
                        run: () => focusDetectedUpdateSource("native"),
                      }
                    : null;
              return (
                <li
                  className={`checklist-item checklist-${item.state}`}
                  key={item.capability_id}
                >
                <span className="checklist-mark" aria-hidden="true">
                  {checklistMark(item.state)}
                </span>
                <div className="checklist-content">
                  <div className="checklist-main">
                    <div>
                      <span>{titleCase(item.category)}</span>
                      <h3>{titleCase(item.name)}</h3>
                    </div>
                    {statusAction ? (
                      <button
                        className="checklist-status checklist-status-action"
                        type="button"
                        aria-label={`${checklistLabel(item.state)}: ${statusAction.label} for ${titleCase(item.name)}`}
                        onClick={statusAction.run}
                      >
                        {checklistLabel(item.state)}
                        <span aria-hidden="true">↗</span>
                      </button>
                    ) : (
                      <span className="checklist-status">
                        {checklistLabel(item.state)}
                      </span>
                    )}
                  </div>
                  {item.state !== "ready" && <p>{item.summary}</p>}
                  {item.restart_action !== "none" && (
                    <p className="restart-note">
                      <b>After the update:</b>{" "}
                      {restartLabel(item.restart_action)}
                    </p>
                  )}
                  {item.state !== "ready" && (
                    <p className="next-step">
                      <b>Next step:</b> {item.next_step}
                    </p>
                  )}
                  {(item.state === "ready" ||
                    item.checks.length > 0 ||
                    (item.details?.observed_sources?.length ?? 0) > 0 ||
                    item.details?.preview) && (
                    <details>
                      <summary>View details</summary>
                      {item.state === "ready" && (
                        <>
                          <p>{item.summary}</p>
                          <p className="next-step">
                            <b>Next step:</b> {item.next_step}
                          </p>
                        </>
                      )}
                      {item.details?.preview && (
                        <div className="preview-details">
                          <p>
                            <b>Keep:</b> {item.details.preview.retention}
                          </p>
                          <ul>
                            {item.details.preview.candidates.map(
                              (candidate) => (
                                <li key={candidate.candidate_id}>
                                  <b>
                                    {candidate.display_name} ·{" "}
                                    {formatBytes(candidate.size_bytes)}
                                  </b>
                                  <span>{candidate.reason}</span>
                                </li>
                              ),
                            )}
                          </ul>
                        </div>
                      )}
                      {(item.details?.observed_sources?.length ?? 0) > 0 && (
                        <ul className="observed-source-list">
                          {item.details?.observed_sources?.map((source) => (
                            <li key={`${source.source_id}-${source.scope}`}>
                              <b>{source.name}</b>
                              <span>
                                {source.state_label} · {source.message}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                      {item.checks.length > 0 && (
                        <ul className="subcheck-list">
                          {item.checks.map((check) => (
                            <li key={check.check_id}>
                              <span
                                className={`subcheck-mark subcheck-${check.state}`}
                                aria-hidden="true"
                              >
                                {checklistMark(check.state)}
                              </span>
                              <div>
                                <b>{titleCase(check.label)}</b>
                                <span>
                                  {checklistLabel(check.state)} ·{" "}
                                  {check.explanation}
                                </span>
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}
                    </details>
                  )}
                </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}
      {items.length === 0 ? (
        <Empty
          title="No Updates Recorded"
          text={`Last completed: ${formatTime(checkedAt)}. A source may have recorded software without checking for newer versions.`}
        />
      ) : (
        <section className="panel table-panel detected-updates">
          <div className="group-title">
            <span>{items.length}</span>
            <div>
              <div className="heading-with-help">
                <h2>Detected Updates</h2>
                <HelpButton kind="wide" title="About Detected Updates">
                  <p>
                    System packages must update together. Saved choices change
                    what Updatarr shows or plans, but they do not change system
                    package settings.
                  </p>
                </HelpButton>
              </div>
            </div>
            <span className="status ready">Review</span>
          </div>
          <div className="table-wrap">
            <table>
              <caption className="visually-hidden">
                Updates available for a safety check and saved review choices
              </caption>
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      aria-label="Select all detected updates"
                      checked={allUpdatesSelected}
                      ref={(node) => {
                        if (node) node.indeterminate = someUpdatesSelected;
                      }}
                      onChange={(event) =>
                        setSelected(event.target.checked ? updateIds : [])
                      }
                    />
                  </th>
                  <th>Software</th>
                  <th>Installed</th>
                  <th>Available</th>
                  <th>Update Source</th>
                  <th>Status</th>
                  <th>Saved Choice</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const choices = savedChoices(item);
                  return (
                    <tr key={`${item.stable_id}-${item.available_version}`}>
                      <td>
                        <input
                          type="checkbox"
                          data-update-source={item.source_id}
                          aria-label={`Include ${item.name} in safety check`}
                          checked={selected.includes(item.stable_id)}
                          onChange={(event) =>
                            toggle(item.stable_id, event.target.checked)
                          }
                        />
                      </td>
                      <td>
                        <b>{item.name}</b>
                        <small>
                          {item.summary ?? "No additional description"}
                        </small>
                      </td>
                      <td>{item.installed_version ?? "Unknown"}</td>
                      <td>{item.available_version}</td>
                      <td>{sourceLabel(item.source_id)}</td>
                      <td>
                        <span className={`status ${statusClass(item.state)}`}>
                          {item.state_label}
                        </span>
                      </td>
                      <td>
                        {choices.length > 0 ? (
                          <button
                            className="quiet compact"
                            onClick={() =>
                              void removeChoices(
                                choices.map((choice) => choice.policy_id),
                              )
                            }
                          >
                            Remove saved choice
                          </button>
                        ) : (
                          <select
                            aria-label={`Saved choice for ${item.name}`}
                            defaultValue=""
                            onChange={(event) => {
                              const value = event.target.value;
                              event.target.value = "";
                              void addChoice(item, value);
                            }}
                          >
                            <option value="">Choose…</option>
                            <option value="postpone">
                              Postpone for 24 hours
                            </option>
                            <option value="skip_version">
                              Skip this version
                            </option>
                            <option value="pause_software">
                              Pause until resumed
                            </option>
                          </select>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
      </details>
    </>
  );
}

function PlanReview({
  plan,
  run,
  approve,
}: {
  plan: UpdatePlan;
  run: UpdateRun | null;
  approve: () => void;
}) {
  const stateText =
    plan.state === "awaiting_review"
      ? "Ready for your review"
      : plan.state === "awaiting_local_confirmation"
        ? "Waiting for confirmation on this computer"
        : plan.state === "awaiting_authorization"
          ? "Waiting for administrator permission"
          : plan.state === "ready_for_execution"
            ? "Ready to start"
            : plan.state === "consumed"
              ? "Plan already used"
              : plan.state === "expired"
                ? "Plan expired"
                : plan.state === "invalidated"
                  ? "Plan needs to be prepared again"
                  : plan.state;
  return (
    <section className="panel plan-review" aria-labelledby="plan-review-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Update plan</p>
          <div className="heading-with-help">
            <h2 id="plan-review-title">{titleCase(stateText)}</h2>
            <HelpButton title="About This Update Plan">
              <p>
                Your review applies only to the software versions and steps
                shown here. If anything changes, Updatarr will ask you to
                prepare and review a new plan.
              </p>
              <p>
                The review code lets Updatarr confirm that the plan has not
                changed.
              </p>
            </HelpButton>
          </div>
          <small className="plan-id">
            Plan ID: <code>{plan.plan_id}</code>
          </small>
        </div>
        <span
          className={`status ${plan.blockers.length ? "blocked" : "ready"}`}
        >
          {plan.blockers.length ? "Blocked" : "Checked"}
        </span>
      </div>
      <dl className="plan-facts">
        <div>
          <dt>Review code</dt>
          <dd>
            <code>{plan.digest.slice(0, 16)}…</code>
          </dd>
        </div>
        <div>
          <dt>Expires</dt>
          <dd>{formatTime(plan.expires_at)}</dd>
        </div>
        <div>
          <dt>Permission</dt>
          <dd>
            {plan.requires_administrator
              ? "Administrator permission needed after confirmation here"
              : "Current user"}
          </dd>
        </div>
      </dl>
      <ol className="plan-steps">
        {plan.steps.map((step) => (
          <li key={step.step_id}>
            <span>{sourceLabel(step.source_id)}</span>
            <div>
              <b>{step.summary}</b>
              <small>
                {step.package_ids.join(", ")} ·{" "}
                {step.expected_changes
                  .map(
                    (change) =>
                      `${change[1] ?? "not installed"} → ${change[2]}`,
                  )
                  .join(", ")}
              </small>
              <small>
                When this step can stop safely:{" "}
                {step.safe_cancellation.toLowerCase()}.
              </small>
              {step.blocker && <p>{step.blocker}</p>}
            </div>
          </li>
        ))}
      </ol>
      {plan.unknowns.length > 0 && (
        <details className="plan-unknowns">
          <summary>Information not provided ({plan.unknowns.length})</summary>
          <ul>
            {plan.unknowns.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      )}
      {plan.blockers.map((blocker) => (
        <p className="decision refused" key={blocker}>
          <b>Cannot run this plan</b>
          <span>{blocker}</span>
        </p>
      ))}
      {plan.state === "awaiting_review" && plan.blockers.length === 0 && (
        <div className="plan-actions">
          <p>
            Approving here does not start the update. The managed computer must
            confirm it separately.
          </p>
          <button className="primary" onClick={approve}>
            Approve exact plan
          </button>
        </div>
      )}
      {plan.state === "awaiting_local_confirmation" && (
        <p className="local-wait">
          <b>Confirm on the managed computer</b>
          <span>
            Open the local approval companion on that computer. The browser
            cannot replace this separate confirmation step.
          </span>
        </p>
      )}
      {run && (
        <div
          className={`run-result ${run.state === "succeeded" ? "allowed" : run.state === "running" || run.state === "created" || run.state === "cancelled" ? "waiting" : "refused"}`}
          role="status"
        >
          <b>
            {run.state === "succeeded"
              ? "Simulation completed"
              : run.state === "running"
                ? "Simulation running"
                : run.state === "created"
                  ? "Simulation is starting"
                  : run.state === "cancelled"
                    ? "Simulation stopped safely"
                    : "Result needs attention"}
          </b>
          <span>{run.message}</span>
          {run.state === "running" && (
            <div
              className="run-progress"
              role="progressbar"
              aria-label="Update simulation progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={run.progress}
            >
              <i style={{ width: `${run.progress}%` }} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function History({
  data,
  importHistory,
}: {
  data: HistoryData | null;
  importHistory: () => void;
}) {
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Activity record</p>
          <div className="heading-with-help">
            <h1>History</h1>
            <HelpButton kind="wide" title="How History Works">
              <p>
                History keeps changes recorded by Updatarr separate from earlier
                activity found in other programs.
              </p>
              <p>
                Earlier activity may be incomplete because other programs do not
                always record every detail. Updatarr labels those limits instead
                of filling in missing information.
              </p>
            </HelpButton>
          </div>
          <p>See software changes recorded by Updatarr and other tools.</p>
        </div>
        <button className="quiet" onClick={importHistory}>
          Import earlier activity
        </button>
      </div>
      {data && (
        <section className="metrics history-metrics">
          <Metric
            value={data.summary.imported_events}
            label="imported changes"
          />
          <Metric
            value={data.summary.updatarr_events}
            label="Updatarr events"
          />
          <Metric
            value={data.summary.recorded_changes}
            label="recorded changes"
          />
          <div>
            <strong>—</strong>
            <span>{data.summary.download_data_label}</span>
          </div>
        </section>
      )}
      {data && data.import_batches.length > 0 && (
        <section className="panel history-import-notes">
          <div className="section-heading">
            <div className="heading-with-help">
              <h2>Earlier History Limits</h2>
              <HelpButton title="About Earlier History Limits">
                <p>
                  Each source explains why its earlier records may be incomplete
                  and how many entries were skipped.
                </p>
              </HelpButton>
            </div>
          </div>
          {data.import_batches.map((batch) => (
            <article key={batch.batch_id}>
              <div>
                <b>
                  {sourceLabel(batch.source_id)} · {scopeLabel(batch.scope)}
                </b>
                <span>
                  {batch.record_count} changes recorded · {batch.skipped_count}{" "}
                  other rows skipped
                </span>
              </div>
              <p>{batch.reason}</p>
            </article>
          ))}
        </section>
      )}
      {!data ||
      (data.items.length === 0 && data.imported_items.length === 0) ? (
        <Empty
          title="No History Yet"
          text="Import earlier activity or run a software check."
        />
      ) : (
        <div className="history-columns">
          <section className="timeline panel">
            <div className="section-heading">
              <div className="heading-with-help">
                <h2>Imported Activity</h2>
                <HelpButton title="About Imported Activity">
                  <p>
                    These are incomplete records from another program, not
                    updates reviewed or run by Updatarr.
                  </p>
                </HelpButton>
              </div>
            </div>
            {data.imported_items.length === 0 ? (
              <p>No earlier activity imported.</p>
            ) : (
              data.imported_items.map((item) => (
                <article key={item.event_id}>
                  <span className="timeline-mark imported" />
                  <div>
                    <h3>
                      {titleCase(historyAction(item.action))} {item.name}
                    </h3>
                    <p>{versionChange(item)}</p>
                    <small>{item.provenance} · Incomplete history</small>
                    <time>{item.occurred_at}</time>
                  </div>
                </article>
              ))
            )}
          </section>
          <section className="timeline panel">
            <div className="section-heading">
              <div className="heading-with-help">
                <h2>Updatarr Activity</h2>
                <HelpButton title="About Updatarr Activity">
                  <p>
                    These are sign-ins, checks, update plans and saved choices
                    recorded by this app.
                  </p>
                </HelpButton>
              </div>
            </div>
            {data.items.map((item) => (
              <article key={item.audit_id}>
                <span className="timeline-mark" />
                <div>
                  <h3>{titleCase(auditLabel(item.kind))}</h3>
                  <p>{auditDescription(item)}</p>
                  <time dateTime={item.occurred_at}>
                    {formatTime(item.occurred_at)}
                  </time>
                </div>
              </article>
            ))}
          </section>
        </div>
      )}
    </>
  );
}

function Settings({
  theme,
  setTheme,
  sources,
  toggleSource,
  policies,
  removeChoice,
}: {
  theme: string;
  setTheme: (value: string) => void;
  sources: SourceSetting[];
  toggleSource: (source: SourceSetting, enabled: boolean) => void;
  policies: Policy[];
  removeChoice: (id: string) => void;
}) {
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Preferences</p>
          <div className="heading-with-help">
            <h1>Settings</h1>
            <HelpButton title="About Settings">
              <p>
                Settings control how Updatarr looks, which update sources it
                checks and which review choices it remembers.
              </p>
            </HelpButton>
          </div>
        </div>
      </div>
      <section className="panel settings-section">
        <div className="section-heading">
          <div className="heading-with-help">
            <h2>Appearance</h2>
            <HelpButton title="About Appearance">
              <p>
                Choose how Updatarr looks. Changing the theme does not change
                update behavior or status meanings.
              </p>
            </HelpButton>
          </div>
        </div>
        <div className="settings-panel">
          <label htmlFor="theme">
            <b>Theme</b>
            <span>Your choice is saved for this Updatarr account.</span>
          </label>
          <select
            id="theme"
            value={theme}
            onChange={(event) => void setTheme(event.target.value)}
          >
            {themes.map(([id, name]) => (
              <option value={id} key={id}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </section>
      <section className="panel settings-section">
        <div className="section-heading">
          <div className="heading-with-help">
            <h2>Backup Settings</h2>
            <HelpButton title="About the Settings Backup">
              <p>
                Download appearance, update-source and saved-review choices.
                Passwords, signed-in sessions, software lists and update plans
                are not included.
              </p>
            </HelpButton>
          </div>
        </div>
        <div className="settings-panel">
          <div>
            <b>Settings file</b>
            <p>Keep a copy before changing the installation or service setup.</p>
          </div>
          <a className="button quiet" href={`${apiBase}/settings/export`} download>
            Download settings
          </a>
        </div>
      </section>
      <section className="panel settings-section">
        <div className="section-heading">
          <div className="heading-with-help">
            <h2>Update Sources</h2>
            <HelpButton title="About Update-Source Settings">
              <p>
                Turning off a source stops its checks in Updatarr. Its last
                information remains visible and is marked as needing refresh.
              </p>
            </HelpButton>
          </div>
        </div>
        <div className="source-settings">
          {sources.map((source) => (
            <label key={`${source.source_id}-${source.scope}`}>
              <span>
                <b>{source.name}</b>
                <small>{scopeLabel(source.scope)}</small>
              </span>
              <input
                type="checkbox"
                checked={source.enabled}
                onChange={(event) =>
                  void toggleSource(source, event.target.checked)
                }
                aria-label={`${source.name} for ${scopeLabel(source.scope)}`}
              />
            </label>
          ))}
        </div>
      </section>
      <section className="panel settings-section">
        <div className="section-heading">
          <div className="heading-with-help">
            <h2>Saved Choices</h2>
            <HelpButton title="About Saved Choices">
              <p>
                Remove a saved choice to return software to the status reported
                by its update source.
              </p>
            </HelpButton>
          </div>
        </div>
        {policies.filter((policy) => policy.kind !== "turn_off_source")
          .length === 0 ? (
          <p>No saved software choices.</p>
        ) : (
          <div className="choice-list">
            {policies
              .filter((policy) => policy.kind !== "turn_off_source")
              .map((policy) => (
                <article key={policy.policy_id}>
                  <div>
                    <b>{policyLabel(policy)}</b>
                    <span>
                      {policy.software_id === systemUpdateGroup
                        ? "All system packages"
                        : policy.software_id}
                    </span>
                    <small>
                      {sourceLabel(policy.source_id)} ·{" "}
                      {scopeLabel(policy.scope)}
                      {policy.version ? ` · ${policy.version}` : ""}
                    </small>
                  </div>
                  <button
                    className="quiet"
                    onClick={() => removeChoice(policy.policy_id)}
                  >
                    Remove saved choice
                  </button>
                </article>
              ))}
          </div>
        )}
      </section>
      <section className="panel settings-section about-settings">
        <div className="section-heading">
          <h2>About Updatarr</h2>
        </div>
        <dl className="about-list">
          <div>
            <dt>Version</dt>
            <dd>Version {releaseVersion} · Build {buildLabel}</dd>
          </div>
          <div>
            <dt>Copyright</dt>
            <dd>© 2026 ✦ ERIK WINBLAD ✦</dd>
          </div>
          <div>
            <dt>Contact</dt>
            <dd>
              <a href="mailto:soulctcher@soulctcher.net">
                soulctcher@soulctcher.net
              </a>
            </dd>
          </div>
          <div>
            <dt>License</dt>
            <dd>
              <a
                href="https://www.gnu.org/licenses/agpl-3.0.html"
                target="_blank"
                rel="noreferrer"
              >
                AGPL-3.0-or-later
              </a>
              <span>GNU Affero General Public License v3.0 or later</span>
            </dd>
          </div>
        </dl>
      </section>
    </>
  );
}

function Empty({ title, text }: { title: string; text: string }) {
  return (
    <section className="empty">
      <Mark />
      <h1>{title}</h1>
      <p>{text}</p>
    </section>
  );
}
function statusClass(state: string) {
  return state === "blocked" || state === "error"
    ? "blocked"
    : state === "ready" || state === "ready_to_review" || state === "up_to_date"
      ? "ready"
      : state === "postponed" || state === "paused" || state === "skipped"
        ? "waiting"
        : "neutral";
}
function checklistLabel(state: string) {
  return state === "ready"
    ? "Passed"
    : state === "blocked"
      ? "Needs attention"
      : state === "not_supported"
        ? "Not supported"
        : "Not checked";
}
function checklistMark(state: string) {
  return state === "ready"
    ? "✓"
    : state === "blocked"
      ? "!"
      : state === "not_supported"
        ? "—"
        : "?";
}
function restartLabel(action: string) {
  return action === "restart"
    ? "Restart the computer to use the new version."
    : action === "shut_down"
      ? "Shut down the computer completely."
      : action === "replug"
        ? "Disconnect and reconnect the device."
        : action === "activate"
          ? "Activate the firmware from the device controls."
          : action === "offline"
            ? "Restart into the protected firmware update environment."
            : action === "disappear"
              ? "The device may temporarily disappear, so the result needs a later check."
              : "The required step is not known yet.";
}
function formatBytes(value: number) {
  return value >= 1024 * 1024
    ? `${Math.round(value / (1024 * 1024))} MiB`
    : `${Math.round(value / 1024)} KiB`;
}
function sourceLabel(value: string) {
  return value === "native"
    ? "System packages"
    : value === "aur"
      ? "AUR"
      : value === "flatpak"
        ? "Flatpak"
        : value === "firmware"
          ? "Firmware"
          : value === "rustup"
            ? "Rust toolchains"
            : value === "cargo"
              ? "Cargo-installed tools"
              : value === "fnm"
                ? "Node.js from fnm"
                : value === "npm"
                  ? "Global npm packages"
                  : value === "uv"
                    ? "uv tools"
                    : value === "appimage"
                      ? "Portable apps"
                      : value;
}
function scopeLabel(value: string) {
  return value === "user"
    ? "Current user"
    : value === "system"
      ? "Whole system"
      : value;
}
function ownershipLabel(value: string) {
  return value === "native_repository"
    ? "System repository"
    : value === "system_prefix"
      ? "System folder; owner not checked"
      : value === "foreign_unresolved" || value === "unresolved"
        ? "Source not confirmed"
        : value === "uv_registered"
          ? "Registered with uv; how uv was installed is unknown"
          : value === "user_tool"
            ? "Current user's tool"
            : value === "confirmed"
              ? "Confirmed"
              : value;
}
function catalogDocumentationUrl(item: CatalogItem) {
  if (item.note) return item.note.source_url;
  if (item.source_id === "aur")
    return `https://aur.archlinux.org/packages/${encodeURIComponent(item.software_id)}`;
  if (item.source_id === "native")
    return `https://archlinux.org/packages/?q=${encodeURIComponent(item.software_id)}`;
  if (item.source_id === "flatpak" && item.origin === "flathub") {
    const appId = item.software_id.split("/", 1)[0] ?? item.software_id;
    return `https://flathub.org/apps/${encodeURIComponent(appId)}`;
  }
  return "https://docs.flatpak.org/en/latest/using-flatpak.html";
}
function policyLabel(policy: Policy) {
  if (policy.kind === "skip_version") return "Skipped this version";
  if (policy.kind === "postpone")
    return policy.expires_at
      ? `Postponed until ${formatTime(policy.expires_at)}`
      : "Postponed until removed";
  return policy.kind === "pause_software"
    ? "Paused until resumed"
    : "Turned off source";
}
function historyAction(action: string) {
  return action === "upgraded"
    ? "Updated"
    : action === "downgraded"
      ? "Moved back"
      : action === "installed"
        ? "Installed"
        : action === "reinstalled"
          ? "Reinstalled"
          : action === "removed"
            ? "Removed"
            : "Changed";
}
function versionChange(item: ImportedHistory) {
  if (
    item.version_before &&
    item.version_after &&
    item.version_before !== item.version_after
  )
    return `${item.version_before} to ${item.version_after}`;
  return item.version_after ?? item.version_before ?? "Version not recorded";
}
function auditLabel(kind: string) {
  return (
    (
      {
        signed_in: "Signed in",
        signed_out: "Signed out",
        sign_in_failed: "Sign-in attempt refused",
        password_changed: "Password changed",
        inventory_check_started: "Software check started",
        inventory_check_completed: "Software check completed",
        inventory_check_failed: "Software check failed",
        inventory_check_cancelled: "Software check cancelled",
        appearance_changed: "Appearance changed",
        saved_choice_added: "Saved choice added",
        saved_choice_removed: "Saved choice removed",
        update_source_setting_changed: "Update source setting changed",
        outside_history_imported: "Earlier activity imported",
        update_selection_checked: "Update selection checked",
        update_plan_prepared: "Update plan prepared",
        update_plan_reviewed: "Update plan approved",
        simulated_update_run_completed: "Update simulation completed",
      } as Record<string, string>
    )[kind] ?? "Updatarr activity"
  );
}
function auditDescription(item: Audit) {
  if (item.kind === "inventory_check_completed")
    return `${Number(item.details.software_recorded ?? 0)} software records saved from ${Number(item.details.source_count ?? 0)} update sources.`;
  if (item.kind === "appearance_changed") return "The saved theme was changed.";
  if (item.kind === "saved_choice_added")
    return "A postpone, skip or pause choice was saved.";
  if (item.kind === "saved_choice_removed")
    return "A saved choice was removed.";
  if (item.kind === "outside_history_imported")
    return `${Number(item.details.added ?? 0)} earlier changes were added.`;
  return "Recorded by Updatarr.";
}
