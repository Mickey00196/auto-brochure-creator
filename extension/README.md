# Proposal Engine Importer (Chrome extension)

One-click import of the commercial listing you're currently viewing (e.g. a
funda in business object page) into the Real Estate Proposal Engine. It sends
the active tab's URL to the app's existing import endpoint
(`POST /imports/urls`, Workflow 2) through the frontend's authenticated
`/api/proxy` route — the same path the `/import` page uses, so it writes to
the exact same Building/Unit/AddOn schema.

The extension never sees your password or session token: authentication rides
on the app's own httpOnly session cookie, so it works as long as you're
logged in to the Proposal Engine in the same Chrome profile.

## Installing (Load unpacked)

This extension is not on the Chrome Web Store — you load it straight from
this folder:

1. Keep a copy of this repository somewhere **permanent** on your computer
   (e.g. `Documents/auto-brochure-creator`). Chrome loads the extension from
   the folder *in place* — if the folder is later moved, renamed, or deleted
   (a Downloads cleanup, a temp folder), the extension breaks with a grey
   icon and a popup that won't open.
2. Open `chrome://extensions` in Chrome.
3. Turn on **Developer mode** (toggle, top-right).
4. Click **Load unpacked** and select this `extension/` folder.
5. Pin it: puzzle-piece icon in the toolbar → pin "Proposal Engine Importer".

## Using it

1. Make sure the Proposal Engine is running and you're logged in to it in
   Chrome (locally: backend on `:8000`, frontend on `:3000` — see the root
   README's "Running it").
2. If your app isn't at `http://localhost:3000`, open the extension popup →
   **Settings**, enter the app's URL, and click **Save** (Chrome will ask you
   to approve access to that site — this is required for the login cookie to
   be attached).
3. Browse to a listing page, click the extension icon, click
   **Import this listing**.
4. The result links straight to the created Building in the app, where you
   can fill in anything the scraper couldn't determine (stored as `TBD`,
   never guessed).

## Troubleshooting

**The popup doesn't open / the icon is greyed out.** The folder Chrome loaded
the extension from no longer exists at that path (moved/renamed/deleted), or
the files changed underneath it. Go to `chrome://extensions`, remove the
broken entry, and **Load unpacked** again from this folder's current
location. If the entry shows a red **Errors** button, click it — the message
there says exactly what failed.

**"You're not logged in".** Log in to the Proposal Engine app itself (the
`/login` page) in the same Chrome profile, then retry.

**"Couldn't reach the app".** The app isn't running at the URL in Settings.
Locally that means `npm run dev` (frontend) and `uvicorn app.main:app`
(backend) both need to be up; on Render's free plan the first request after
15 idle minutes takes ~30s to wake the service — wait and retry.

**Import succeeds but most fields are TBD.** Expected — the scraper only
stores what it can confidently extract from the page and leaves the rest for
you to fill in via the building's detail page (see "Same schema, two ways in"
in the root README).

**"The import timed out".** The popup's import request gives up after 60s
(`popup.js`, `AbortSignal.timeout`) so it can never hang forever — this fires
either because the backend's headless-browser render is taking too long, or
because the target site is blocking/challenging automated access. Retry once;
if it keeps happening for one site, that site likely needs a
Playwright-side workaround (custom headers/stealth) rather than a longer
timeout.

## Maintainer note: the backend's headless browser

`backend/app/services/scraping/generic_scraper.py::fetch_rendered_html`
launches Chromium via Playwright's normal browser resolution (no hardcoded
`executable_path`) — it relies on whatever `playwright install chromium` put
in Playwright's default cache dir, or on `PLAYWRIGHT_BROWSERS_PATH` if that
env var is set. **Do not hardcode an `executable_path`** — a fixed path only
matches wherever the browser happened to be installed on one particular
machine (e.g. a dev sandbox) and silently breaks every import, including
funda.nl, on any other machine or deployment. `tests/test_scraping.py`
(`test_fetch_rendered_html_does_not_hardcode_a_sandbox_browser_path`) guards
against this regressing.
