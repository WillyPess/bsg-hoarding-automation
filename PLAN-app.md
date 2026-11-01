# BSG Hoarding App – plan (v0, 2026-11-01)

A small web app around the existing engine: Gus enters a job, uploads the photo, runs the engine, checks the outputs, approves them and downloads the package and quote PDFs. **Plan only; nothing is built yet.** Rules 6 and 7 come after this plan is approved.

## 1. Principles

1. **The app never calculates.** Every number on screen comes from the engine (`run_job.py`, `run_summary.json`, the generated files). The app stores inputs, starts the engine and shows what the engine wrote. If the app ever needs a number or a check the engine doesn't give yet, that goes into the engine first, as its own PR with tests.
2. **Same engine, same outputs.** A job run from the app gives the same files as `python run_job.py <job folder>`. The reference jobs and baselines in `expected/` stay the test of the engine; the app adds its own tests on top.
3. **Python only.** No Node, no JavaScript build step, no cloud services.
4. **One user first.** One login, on Gus's Windows PC. Later the same app is reached through Cloudflare Tunnel.
5. **Nothing silent.** Provisional rules, estimates and unanswered questions show as warnings. An external job without the extra weight answer cannot run (§7 of CLAUDE.md).
6. **Small PRs, test first**, the same as step D.

## 2. Stack

| Part | Choice | Why |
|---|---|---|
| Web framework | **FastAPI** + Uvicorn | Asked for. Typed forms, a good test client, and it runs on Windows with no extra service. |
| Pages | **Server-rendered Jinja2 templates** | Every screen is a form, a list or a review page. The server already has all the data, so it renders the HTML. There is one place for the logic and no API to keep in sync. |
| Interactivity | **HTMX** (one vendored JS file, no build) | For the few dynamic parts: the engine run status, adding or removing faces on corner and U jobs, and inline validation messages. It works by swapping server-rendered HTML, so it stays Python-only. |
| CSS | One small hand-written stylesheet (or a vendored classless CSS file) | Simple, readable, and prints well. Nothing is loaded from a CDN, so it works offline. |
| Storage | Files on disk + **SQLite** (stdlib `sqlite3`) | See §5. No database server. |
| Auth | Starlette session cookie + a password hash (stdlib `hashlib.scrypt`) | One user. No external identity service yet. |
| Tests | pytest, FastAPI `TestClient`, **Playwright** (Python package) | pytest is what the engine already uses; Playwright drives a real browser from Python, on Windows and Linux. |

**Frontend approach: server-rendered pages + HTMX.** Alternatives considered:
- **A React/Vue single-page app:** it needs Node and a build step, a JSON API and the form checks written twice. That's too heavy for one user and about ten screens, and it breaks "Python only".
- **Streamlit / NiceGUI / Gradio:** quick to start, but harder to control the page layout, the login and the URLs, and awkward to test end to end. Streamlit also reruns the whole script on every click, which fits a long engine run badly.
- **Plain HTML with no HTMX:** possible, but the run-status page and the faces editor would need full page reloads. HTMX adds one small vendored file and no build step.

## 3. Screens

| # | Screen | What it shows / does | Where the data comes from |
|---|---|---|---|
| 1 | **Login** | Password (user name fixed in v1). Rate-limited. | `users` table |
| 2 | **Job list** | All jobs: title, site, type, status (draft / run / approved), last run, a warnings count. Search by title or site. | `jobs` table + each job's last `run_summary.json` |
| 3 | **New job / edit job** | The "Inputs from Gus" (CLAUDE.md), see §4. A save is checked by the engine's validator, and errors show next to the fields. | form → `job.json` |
| 4 | **Photo** | Upload Gus's marked-up photo (used as-is, §1 of CLAUDE.md) or a clean photo. Preview, replace. A link to the Hoarding Planner for marking a clean photo by hand. | stored as `<P>_hoarding_markup.jpg` / `<P>_photo.*` |
| 5 | **Run** | "Run the engine". Status (queued / running / done / failed); on failure, the engine's error text (e.g. "This job is external. Add extra weight?…"). | `run_job.run()` in a worker |
| 6 | **Review** | Grid sheet and melamine layout (images); the materials form (rendered from the xlsx cells, plus the PDF); the quote (Pacific Fair); the summary counts; **warnings**; and what changed since the previous run (fields that differ in `run_summary.json`). | the run folder |
| 7 | **Approve** | Approve this run (name + date, optional note). An approved run is locked. Editing the job afterwards starts a new draft run. | `approvals` table |
| 8 | **Downloads** | Package PDF, quote PDF, materials xlsx/PDF, images. Draft files get "DRAFT" in the file name; approved files keep the engine names. | the run folder |
| 9 | **Job history** | Every run of a job: date, status, who approved it, the engine version and rules version, the key counts. Open any old run read-only. | `runs` table |
| 10 | **Rules** (read-only) | Every `rules.json` entry: value, source, **provisional** flag, `used_from`, and the switches (e.g. `tape.tape_rule`). Grouped as in CLAUDE.md. Provisional ones are highlighted. | `rules.json` via `rules.py` |

The warnings come from the engine (new `warnings(job, summary)` function, §6). Examples: provisional rules used by this job (external table, tape switch, studs per 8.8 m), sizes marked as estimates, the rate card's printed validity has ended, the entry moved to use full sheets (`entry_note`), the track + timbers note on fire-door jobs, a height near the top of the matrix.

## 4. The new-job form

The same inputs as "Inputs from Gus" in CLAUDE.md, in metres, as job.json uses:

- **Always:** job title (exactly as Gus writes it), prefix (suggested from the title, editable), site (Pacific Fair / Hyperdome / other, **always asked**, §12), date, prepared by (default Gus).
- **Job type:** standard / corner / U (kiosk) / fire door. The type picks the next fields.
- **Standard:** front, returns (default 1.6 from `rules.json`), height, entry width (default 1.6), entry height (default 2.4), entry position **from the left or the right end** (the engine converts it to `door_offset`, §6), entry note.
- **Corner / U:** a faces table (name, length, cut end, door offset on the face with the door) with HTMX add/remove rows; `sheet_h` for 2.4 m jobs.
- **Fire door:** faces + the track section fields (as in `Medibank/job.json`); the form explains the "suggestion only" note.
- **External:** a tick box. When ticked, the form shows Gus's question, **"This job is external. Add extra weight? If yes, how many percent?"**, with no default filled in: the user must type 0 or a number (§7). The height is fixed at 2.4 m (§7).
- **Optional:** hand-set uprights (with the reason), photo note / photo text, quote fields for Pacific Fair (quote date, extra doors, passage sets, extra lines with POA).

The defaults shown in the form are read from `rules.json` (`defaults`). The checks are the engine's (§6), not the app's.

## 5. How jobs are stored

A data folder outside the repo, set by `BSG_DATA` (default `C:\BSG\data` on Windows):

```
data/
  bsg.sqlite                      jobs, runs, approvals, users, audit log
  jobs/<Job>/
    job.json                      current inputs (draft)
    <P>_photo.jpg / <P>_hoarding_markup.jpg
    runs/0001/                    one folder per engine run, never changed after it finishes
      job.json                    the exact inputs of this run
      <P>_hoarding_sheet.png, <P>_melamine_layout.png, <P>_materials.xlsx/.pdf,
      <P>_Hoarding_Package.pdf, <P>_Quotation.pdf, run_summary.json
      engine.json                 engine git commit, sha256 of rules.json, Python/Pillow/LibreOffice versions, time taken
    runs/0002/ ...
```

- **One folder per job, the same layout as `hoarding/<Job>/`**, so a job folder can still be run by hand with `run_job.py`, and an old job can be imported by copying its folder.
- **Runs are immutable.** The app runs the engine on a copy of the inputs in `runs/<n>/` (this is what `run_job.py --out` already does). Approving marks a run, it doesn't copy files. An approved run stays downloadable forever, even after the rules change.
- **SQLite holds only the index and the history** (job id, title, site, status, run numbers, approvals, who did what and when). The files stay the truth. A "rebuild index" command can rebuild the database from the folders.
- **One engine run at a time** (a lock). The runs take about 5 s each, so a queue isn't needed.
- **Backups:** copy the `data` folder (a scheduled copy to another drive comes later). The reference jobs in `hoarding/` stay in the repo for the tests; the app can show them as read-only examples.

## 6. What the engine gets first (engine PRs, before the app)

The app must not calculate or check rules itself, so the engine gains three small functions, each with tests:

1. **`hoarding/validate.py` – `check(job) -> list of errors`:** required fields per job type; ranges from `rules.json` (e.g. height within the weight matrix, external jobs at 2.4 m, `extra_weight_pct` present and ≥ 0 on external jobs); the entry inside the front; prefixes safe for file names. `run_job.py` calls it too, so the command line and the app refuse the same jobs.
2. **`normalize(inputs) -> job.json`:** turns the form's "entry from the right end" into `door_offset` from the left end (or from the corner), fills defaults from `rules.json`, and builds `dir`. This is the only place that turns form inputs into job.json.
3. **`warnings(job, summary) -> list`:** the warnings listed in §3, with the rule they come from.

## 7. Login and access

- **v1 (Windows PC):** the app listens on `127.0.0.1:8000` only. There is one user, created with `python -m app.users set-password`; the password hash (scrypt) is stored in SQLite. Signed session cookie, CSRF token on every form, a login rate limit, and a logout. The secret key lives in `data/secret.key`, made on first start.
- **Start:** `start-bsg.bat` (activates the venv, runs `python -m app`, opens the browser). Optionally a Windows Task Scheduler entry at login.
- **Later, Cloudflare Tunnel:** `cloudflared` on the same PC points a hostname at `127.0.0.1:8000`, so no ports are opened on the router. **Cloudflare Access** goes in front (email one-time code for Gus and his boss) as a second lock before the app's own login. Cookies become `Secure`, and the app trusts the tunnel's forwarded headers. This is a separate PR, after v1 works locally.

## 8. Testing

| Level | What | Tools |
|---|---|---|
| Engine (existing) | Reference jobs, baselines, rules tests. Unchanged; new engine functions (§6) get the same kind of tests. | pytest |
| App unit | Storage (job folders, run numbers, immutability), the auth helpers, the template helpers. | pytest |
| App routes | Every page and form through FastAPI `TestClient`: login required, CSRF, validation errors shown, an approved run can't be changed, downloads return the right file names. | pytest + httpx |
| **"The app never calculates"** | A route test runs the review page with a fake `run_summary.json` full of marker values (e.g. sheets = 9991). The page must show exactly those markers. A test that greps the `app/` package for imports of `layout_gen`, `titan`, `tape` and `quote_gen` (only the engine bridge may call `run_job`). | pytest |
| Engine through the app | For each reference job: create it through the app, run it, and compare the run folder with `expected/` using the same checks as `tests/test_reference_jobs.py` (counts, materials cells, PDF text, tolerant drawings). | pytest |
| **End to end** | Real browser against a running app on a temp data folder: log in → new standard job (Bikini inputs) → upload the photo → run → review shows 11 sheets, 11 uprights, 77 weights (read from `expected_counts.json`, not typed into the test) → approve → download the package and check its text against the baseline. Plus: an external job without the extra-weight answer can't run; a wrong height shows the engine's error; a corner job with three faces; logout. Screenshots on failure. | **Playwright (pytest-playwright)** |
| Windows | The same suite on Gus's PC before each release (the drawings comparison is tolerant across machines). | pytest |

## 9. Build order (small PRs, each from main, test first)

1. **Engine: `validate.check`** + `run_job.py` uses it.
2. **Engine: `normalize`** (entry from either end, defaults) + **`warnings`**.
3. **App skeleton:** `app/` package, FastAPI, the base template, static files, settings (`BSG_DATA`), `python -m app`, a health page, the first route tests.
4. **Login:** set-password command, sessions, CSRF, rate limit, logout.
5. **Storage:** the data folder, SQLite index, job folders, run folders, the rebuild-index command.
6. **Job list + new job form (standard jobs)**, using `normalize` and `validate`.
7. **Photo upload:** type and size checks, preview, replace.
8. **Run:** worker, lock, status page (HTMX polling), errors shown.
9. **Review screen:** images, materials table, quote, summary, warnings, changes since the last run.
10. **Approve, downloads, job history.**
11. **Corner, U and fire-door forms** (faces editor) and **external jobs** (extra weight question).
12. **Rules page** (read-only, provisional highlighted).
13. **Playwright end-to-end suite** + `start-bsg.bat` + README section.
14. **Later:** Cloudflare Tunnel + Access (its own PR and checklist).

Then rules 6 and 7 continue in the engine. The app picks them up with no app change, and only their baselines change.

## 10. Later phase: where AI could help (not in v1)

v1 has no AI. Later, each idea would be a separate, optional feature. AI only **drafts inputs**; the engine still computes every number, and Gus still approves.

- **Reading the photo:** suggest the hoarding outline and the entry on a clean photo, for Gus to correct. Sizes read from a photo are always marked as **estimates** (§1).
- **Drafting job.json from Gus's message** (e.g. "Medibank, 7.5 front, 4.2 high, door 4.7 from the left"): the AI fills the form; Gus checks it and the engine validates it.
- **Spotting odd inputs:** "this front is 3x longer than any earlier job, check the units".
- **Explaining a number:** "why 38 uprights?", answered by pointing to the rules and the summary, not by recalculating.
- **Summaries:** a short message for the install team or centre management from the approved run.

These need a privacy check (photos of shopfronts, client names) and a cost check before any of them is built.

## 11. Questions for you before building

1. The data folder location on the Windows PC (`C:\BSG\data`?), and whether it should be inside a synced folder (OneDrive) for backup.
2. Should the reference jobs show in the app as read-only examples?
3. Can draft files be downloaded (marked DRAFT), or only approved runs?
4. Does Gus's boss need his own login in v1, or later with the tunnel?
