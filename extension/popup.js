/* Popup logic: send the active tab's URL to the Proposal Engine's existing
 * import endpoint (POST /imports/urls, Workflow 2) via the frontend's
 * authenticated /api/proxy route. The session lives in the app's httpOnly
 * cookie, so the extension never sees or stores the JWT — it just needs the
 * user to be logged in to the app in this browser profile, plus host
 * permission for the app's origin so Chrome attaches the cookie. */

const DEFAULT_APP_URL = "http://localhost:3000";

const importBtn = document.getElementById("import-btn");
const saveBtn = document.getElementById("save-btn");
const appUrlInput = document.getElementById("app-url");
const tabUrlEl = document.getElementById("tab-url");
const statusEl = document.getElementById("status");

let activeTabUrl = null;

function setStatus(kind, nodes) {
  statusEl.hidden = false;
  statusEl.className = `status ${kind}`;
  statusEl.replaceChildren(...nodes);
}

function text(s) {
  return document.createTextNode(s);
}

function link(href, label) {
  const a = document.createElement("a");
  a.href = href;
  a.target = "_blank";
  a.rel = "noreferrer";
  a.textContent = label;
  return a;
}

async function getAppUrl() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  return appUrl;
}

async function init() {
  appUrlInput.value = await getAppUrl();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.url && /^https?:/.test(tab.url)) {
    activeTabUrl = tab.url;
    tabUrlEl.textContent = activeTabUrl;
    tabUrlEl.title = activeTabUrl;
    importBtn.disabled = false;
  } else {
    tabUrlEl.textContent = "This page can't be imported — open a listing page first.";
  }
}

importBtn.addEventListener("click", async () => {
  const appUrl = await getAppUrl();
  importBtn.disabled = true;
  setStatus("ok", [text("Importing… the page is fetched and parsed server-side, this can take ~10–30 seconds.")]);

  let res;
  try {
    res = await fetch(`${appUrl}/api/proxy/imports/urls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ urls: [activeTabUrl] }),
      // The scrape can legitimately take up to ~15-30s (headless render +
      // parse), but it must not hang the popup forever if the target site
      // never responds — bound it so the UI always resolves to an error.
      signal: AbortSignal.timeout(60_000),
    });
  } catch (err) {
    const reason =
      err?.name === "TimeoutError" || err?.name === "AbortError"
        ? "The import timed out — the target page may be blocking automated access."
        : `Couldn't reach the app at ${appUrl}. Check that it's running, and that the URL under Settings is correct.`;
    setStatus("error", [text(reason)]);
    importBtn.disabled = false;
    return;
  }

  if (res.status === 401) {
    setStatus("error", [
      text("You're not logged in to the Proposal Engine. "),
      link(`${appUrl}/login`, "Log in"),
      text(" in this browser, then try again."),
    ]);
    importBtn.disabled = false;
    return;
  }

  if (!res.ok) {
    setStatus("error", [text(`Import failed (HTTP ${res.status}). Check the app's logs.`)]);
    importBtn.disabled = false;
    return;
  }

  const [result] = await res.json();
  if (result?.status === "created") {
    const nodes = [
      text(`Imported "${result.title ?? activeTabUrl}". `),
      link(`${appUrl}/buildings/${result.building_id}`, "Open it in the Proposal Engine"),
      text(" to review and fill in anything the scraper couldn't determine."),
    ];
    if (result.message) nodes.push(document.createElement("br"), text(`Note: ${result.message}`));
    setStatus("ok", nodes);
  } else {
    setStatus("error", [text(`Import failed: ${result?.message ?? "unknown error"}`)]);
  }
  importBtn.disabled = false;
});

saveBtn.addEventListener("click", async () => {
  let origin;
  try {
    origin = new URL(appUrlInput.value.trim()).origin;
  } catch {
    setStatus("error", [text("That doesn't look like a valid URL — include the scheme, e.g. https://your-app.example")]);
    return;
  }

  // Chrome only attaches the app's session cookie to our requests if the
  // extension holds host permission for that origin; localhost is granted in
  // the manifest, anything else must be requested here (from a user gesture).
  const originPattern = `${origin}/*`;
  const alreadyGranted = await chrome.permissions.contains({ origins: [originPattern] });
  if (!alreadyGranted) {
    const granted = await chrome.permissions.request({ origins: [originPattern] });
    if (!granted) {
      setStatus("error", [
        text("Permission for that site was declined — the extension can't send authenticated requests to it without approval."),
      ]);
      return;
    }
  }

  await chrome.storage.sync.set({ appUrl: origin });
  appUrlInput.value = origin;
  setStatus("ok", [text(`Saved. Imports will go to ${origin}.`)]);
});

init();
