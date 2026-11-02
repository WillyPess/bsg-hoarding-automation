# BSG Hoarding App – plan (v1, 2026-11-02)

A web app around the existing engine. Gus or his boss enters a job and uploads the photo. An AI reviewer checks the inputs, the engine computes everything, and the AI reviewer checks the outputs. A person answers every flag, approves the run, and downloads the package and quote PDFs.

**Plan only; nothing is built yet.** v0 of this plan (2026-11-01) had no AI. This version adds the AI reviewer (§8) and records your answers to the v0 questions (§13) and to the v1 questions (§14, 2026-11-02).

## 1. Principles

1. **The engine computes every number.** Every number on screen and in every file comes from the engine (`run_job.py`, `run_summary.json`, the generated files). The app stores inputs, starts the engine and shows what the engine wrote. If the app needs a number or a check the engine doesn't give yet, that goes into the engine first, as its own PR with tests.
2. **The AI reviews, it never calculates or decides.** Claude reads the inputs, the photo and the outputs and raises **flags**. A person answers every flag. Claude never sets or changes a number, never changes a job, a rule or the engine, and never starts anything by itself (§8.1).
3. **Same engine, same outputs.** A job run from the app gives the same files as `python run_job.py <job folder>`. The baselines in `expected/` stay the test of the engine.
4. **Python only, local first.** No Node, no JavaScript build step. The app and its data live on Gus's Windows PC. **One cloud service is allowed: the Claude API**, for the AI reviewer only. The app works without it (§8.8).
5. **Nothing silent.** Provisional rules, estimates, unanswered flags and unanswered questions show as warnings. Every flag, suggestion and answer is saved with who answered and when.
6. **Small PRs, test first**, as in step D. The AI tests use recorded responses only; the test suite never calls the real API.

## 2. Stack

| Part | Choice | Why |
|---|---|---|
| Web framework | **FastAPI** + Uvicorn | Typed forms, a good test client, and it runs on Windows with no extra service. |
| Pages | **Server-rendered Jinja2 templates** | Every screen is a form, a list or a review page. The server has the data, so it renders the HTML. There is one place for the logic. |
| Interactivity | **HTMX** (one vendored JS file, no build) | For the run status, the AI review progress, flag answers, and adding or removing faces. It swaps server-rendered HTML, so it stays Python-only. |
| CSS | One small hand-written stylesheet | Readable, prints well, no CDN. |
| Storage | Files on disk + **SQLite** (stdlib `sqlite3`) | See §7. No database server. |
| Auth | Starlette session cookie + password hashes (stdlib `hashlib.scrypt`) | Two users in v1 (§3). No external identity service. |
| AI | **Anthropic Python SDK** (`anthropic`), Claude with vision | The official SDK, typed responses, retries built in. See §8.7. |
| Tests | pytest, FastAPI `TestClient`, **Playwright** (Python package) | pytest is what the engine uses; Playwright drives a real browser on Windows and Linux. |

**Frontend approach: server-rendered pages + HTMX.** Alternatives considered:
- **A React/Vue single-page app:** it needs Node, a build step and a JSON API, with the form checks written twice. That's too heavy for two users and about a dozen screens, and it breaks "Python only".
- **Streamlit / NiceGUI / Gradio:** quick to start, but harder to control the layout, the login and the URLs, and awkward to test end to end. Streamlit also reruns the whole script on every click, which fits long engine runs and AI calls badly.
- **Plain HTML with no HTMX:** possible, but the run status, the review progress and the faces editor would need full page reloads.

## 3. Users and roles

- **Two logins in v1: Gus and his boss.** Each has their own name and password, so the history shows who did what.
- **Roles:** `estimator` (Gus) and `manager` (the boss). In v1, both can create jobs, answer flags, run the engine and approve. The role is recorded with every action. Escalations (§8.4) can be addressed to either person.
- **Decided (2026-11-02):** in v1 both users can do everything; the history records who did what. Roles are revisited after the pilot (§14).

## 4. Screens

| # | Screen | What it shows / does | Where the data comes from |
|---|---|---|---|
| 1 | **Login** | User name + password. Rate-limited. | `users` table |
| 2 | **Job list** | All jobs: title, site, type, status, last run, open flags, warnings count. Search by title or site. A separate **Examples** tab shows the reference jobs, read-only. | `jobs` table + each job's last `run_summary.json` |
| 3 | **New job / edit job** | The "Inputs from Gus" (§6). Saving runs the engine's `validate.check`, and its problems show next to the fields. Values from an accepted AI suggestion are filled in and marked **estimate** (§8.5). | form → `jobs.normalize` → `job.json` |
| 4 | **Photo** | Upload Gus's marked-up photo (used as-is, CLAUDE.md §1) or a clean photo. Preview, replace. A link to the Hoarding Planner. | stored as `<P>_hoarding_markup.jpg` / `<P>_photo.*` |
| 5 | **Input review** | The AI's flags on the inputs (§8.2): each with its level, what it saw, the rule it relates to, an optional suggested change, and the three answers. Safety flags left open show "Engine run blocked". | `flags` table |
| 6 | **Run** | "Run the engine", enabled only when validate passes and no safety flag is open. Status (queued / running / done / failed); on failure, the engine's own error text. | `run_job.run()` in a worker |
| 7 | **Review** | Grid sheet and melamine layout; the materials form (from the xlsx cells, plus the PDF); the quote (Pacific Fair); the summary counts; the engine's **warnings** (`jobs.warnings`); what changed since the previous run; and the **AI output review** (§8.3): flags plus "explain this number". | the run folder + `flags` table |
| 8 | **Approve** | Approve this run (name, date, optional note). Possible only when no safety flag is open on the run. An approved run is locked; editing the job afterwards starts a new draft. | `approvals` table |
| 9 | **Downloads** | Package PDF, quote PDF, materials xlsx/PDF, images. Draft files carry **"DRAFT - not approved"** on every page and in the file name (§7). | the run folder |
| 10 | **Job history** | Every run, flag, answer, AI call (model, cost) and approval, with who and when. Open any old run read-only. | `runs`, `flags`, `ai_calls`, `approvals`, `audit` tables |
| 11 | **Escalations** | Cases the AI or `validate` sent to Gus or his boss (§8.4): open / answered, with the job and the reason. | `escalations` table |
| 12 | **Rules** (read-only) | Every `rules.json` entry: value, source, **provisional** flag, and the switches (e.g. `tape.tape_rule`). Provisional ones are highlighted. | `rules.json` via `rules.py` |
| 13 | **AI usage** | Calls and cost this month against the caps (§8.8), by job. | `ai_calls` table |

## 5. Job flow

```
 draft ──save──▶ validate.check ──problems──▶ back to the form (fields marked)
                      │ ok
                      ▼
               AI input review ──flags──▶ user answers each flag
                      │                     · Yes, change it → form opens with the suggestion (estimate) → save → validate → review again
                      │                     · No, it's correct → flag closed
                      │                     · Not sure, I'll ask → escalation; a safety flag stays open
                      ▼  (no open safety flag)
                 engine run ──failed──▶ error shown; out-of-rules cases → escalation
                      │ done (starts by itself)
                      ▼
               AI output review ──flags──▶ answered the same way (a "Yes" goes back to the form)
                      │  (no open safety flag)
                      ▼
                   approve ──▶ run locked, final files downloadable
```

- The AI input review runs automatically after each successful save (and can be re-run by hand). The engine run is started by the user. **The AI output review starts by itself after every engine run** (decided 2026-11-02, §14).
- If the AI is unavailable or over its cost cap, the flow continues without it, and the job shows "AI review not done" (§8.8).

## 6. The new-job form

The same inputs as "Inputs from Gus" in CLAUDE.md, in metres. `jobs.normalize` turns them into job.json:

- **Always:** job title (exactly as Gus writes it), prefix (suggested by `jobs.suggest_prefix`, editable), site (Pacific Fair / Hyperdome / other, **always asked**, §12), date, prepared by (the logged-in user).
- **Job type:** standard / corner / U / fire door, plus a **kiosk** tick box (1.2 m only, rule 7). The type picks the next fields.
- **Standard:** front, returns (default 1.6), height, entry width (default 1.6), entry height (default 2.4; 1.2 on a kiosk), entry position **from the left or the right end**, entry note.
- **Corner / U / fire door:** a faces table (name, length, cut end; the entry face gets the entry position from either end) with HTMX add/remove rows; the track section fields on fire-door jobs, with the "suggestion only" note.
- **External:** a tick box. When ticked, the form asks Gus's question, **"This job is external. Add extra weight? If yes, how many percent?"**, with nothing filled in: the user must type 0 or a number (§7 of CLAUDE.md). Height 2.4 m.
- **Estimates:** any length can be ticked as an **estimate** (`"estimated"` in job.json). AI suggestions arrive ticked. Estimates show as warnings in the review and the package until someone unticks them with a site measurement.
- **Optional:** hand-set uprights (with the reason), photo note / photo text, quote fields for Pacific Fair.

The defaults come from `rules.json` through `jobs.normalize`. The checks are `validate.check`'s, not the app's.

## 7. How jobs are stored

A data folder **outside the repo: `C:\BSG\data`** (set by `BSG_DATA`):

```
C:\BSG\data\
  bsg.sqlite                      jobs, runs, flags, escalations, approvals, ai_calls, users, audit
  config.toml                     AI settings: model ID, caps, effort, on/off (§8.7); no secrets
  secret.key                      session signing key, made on first start
  jobs/<Job>/
    job.json                      current inputs (draft)
    <P>_photo.jpg / <P>_hoarding_markup.jpg
    reviews/                      every AI call: the request sent (images by hash, not copied) and the raw response
    runs/0001/                    one folder per engine run, never changed after it finishes
      job.json                    the exact inputs of this run
      <P>_hoarding_sheet.png, <P>_melamine_layout.png, <P>_materials.xlsx/.pdf,
      <P>_Hoarding_Package.pdf, <P>_Quotation.pdf, run_summary.json
      engine.json                 engine git commit, sha256 of rules.json, versions, time taken
```

- **One folder per job, the same layout as `hoarding/<Job>/`**, so a job folder can still be run by hand with `run_job.py`.
- **Runs are immutable.** The engine runs on a copy of the inputs in `runs/<n>/`. Approving marks a run; it doesn't copy files. An approved run stays downloadable after the rules change.
- **Drafts:** downloads of an unapproved run are stamped **"DRAFT - not approved"** on every PDF page (a stamp added when the file is downloaded; the run folder stays as the engine wrote it) and get `DRAFT_` in the file name.
- **SQLite holds the index and the history.** The files stay the truth for inputs and outputs; flags, answers, AI calls and approvals live in SQLite and are also written to `audit` (append-only). A "rebuild index" command can rebuild the job index from the folders.
- **Daily backup** to another drive: a Windows scheduled task copies `C:\BSG\data` (SQLite through its backup API, so the copy is consistent) to the backup drive and keeps 30 days. The app shows the time of the last backup and warns when it's older than 2 days.
- **Examples:** the reference jobs in `hoarding/` stay in the repo for the tests. The app lists them read-only under **Examples**; they can't be edited, run or approved.
- **The API key** is not in the data folder or the repo: it comes from the `ANTHROPIC_API_KEY` environment variable (set once on the PC).

## 8. The AI reviewer

### 8.1 What it may and may not do

**It may:** read the job's inputs, photos, `validate` result, engine warnings, outputs and past jobs (§8.6); raise flags; propose a changed input value inside a flag; explain a number by pointing to its rule and the summary; and send a case to Gus or his boss.

**It may never (hard limits, enforced by the app, not only by the prompt):**
- set or change a number, or produce any quantity the engine computes;
- change a job by itself: a suggestion is only data in a flag until a person accepts it and saves the form;
- edit `rules.json`, the engine, the templates or any file;
- run anything: the app starts every call, and nothing in a response is executed;
- invent a rule: anything the rules don't cover becomes an escalation (§8.4).

How the app enforces this:
- The reviewer has **no tools**. Each call is one request and one structured response. Claude can't call functions, read files or browse.
- **Responses are data.** They are validated against the JSON schema (§8.6) and stored. Nothing in them is executed, and nothing writes to job.json until a person saves the form.
- **Suggestions only cover input fields.** A suggestion can only name job.json input fields from a fixed list (lengths, positions, types, notes). Anything else is dropped, and the drop is logged.
- **Explanations don't add numbers.** Every number in an explanation must already be in the summary, the job or `rules.json`. The app checks this, and an explanation that brings a new number is not shown.

### 8.2 Input review (after the form is saved, before the engine runs)

Claude gets the job as saved (job.json), the photo or photos, `validate.check`'s result, `jobs.warnings` for the inputs, the business rules (CLAUDE.md §1–12 and the provisional `rules.json` entries), and a short list of similar past jobs (§8.6).

It flags what the rules don't catch, for example:
- **The photo shows something missing from the form:** a fire door, a column, a sprinkler, a low ceiling, a shop entrance in a different place.
- **The entry doesn't line up** with the shop entrance in the photo (CLAUDE.md §1).
- **A measure looks wrong** for the photo (a 20 m front on a narrow shop), or unusual against past jobs (units, a typo).
- **Information is missing** that the rules expect: site not asked, an external job with no wind exposure noted, returns that differ from the photo.

A flag may carry a **suggested input change**, e.g. `door_offset: 3.6 (estimate)`.

### 8.3 Output review (after the engine runs)

Claude gets the grid sheet and layout images, the package PDF, the materials cells, `run_summary.json`, `jobs.warnings`, the inputs and the photo. It:
- **flags anything odd:** the drawing doesn't match the photo, the entry is on the wrong side, a section looks missing, a note contradicts the inputs, a page is unreadable;
- **explains any number on request** ("why 38 uprights?") by pointing to the rule (CLAUDE.md section or `rules.json` entry) and the summary values that give it. It never recalculates; the explanation quotes the engine's numbers.

### 8.4 Cases outside the rules

When a case isn't covered by the rules, Claude explains why and the app creates an **escalation** to Gus or his boss. Examples: a new shape, a height above 7.2 m, a kiosk at another height, anything `validate` refuses with "ask Gus", or a flag answered "Not sure".

The escalation holds the job, the reason, Claude's explanation and the question to answer. Claude never proposes a new rule or a value for one. A new rule is written by a person into CLAUDE.md / `rules.json` through a normal PR, as in step D.

### 8.5 Flags and answers

Every flag has:
- a **level**: safety or normal;
- a **category**;
- **what was seen** (with the photo region or page, when there is one);
- **the rule** it relates to;
- an optional **suggested input change**;
- three answers:

| Answer | What happens |
|---|---|
| **Yes, change it** | The form opens with the suggested values filled in and ticked as **estimates**. The user checks them and saves. `validate` runs, then the input review runs again, then the engine can run. |
| **No, it's correct** | The flag is closed with that answer. Optional comment. |
| **Not sure, I'll ask** | The flag stays open and an escalation is created. A **safety** flag keeps the job blocked. |

**Two levels:**
- **Safety flags block the engine run** (input review) or **the approval** (output review) until answered "Yes" (and the change saved) or "No". "Not sure" keeps the job blocked.
- **Normal flags** (an odd measure, entry alignment, a missing note) are shown and saved but don't block.

**The app decides the level, not Claude.** Claude picks a category from a fixed list. The level of each category is set in `config.toml`:

| Category | Level |
|---|---|
| `fire_door`, `uprights`, `counterweights`, `wind`, `structural` (columns, sprinklers, ceiling, anything that holds the hoarding up), `access_safety` | **safety** |
| `measure`, `entry_alignment`, `missing_info`, `drawing_mismatch`, `note` | normal |

A category Claude invents is treated as **safety**, so an unknown never slips through as harmless.

Every flag, suggestion and answer is saved with the user, role and time, in `flags` and in the append-only `audit` table. The job history shows them in order.

### 8.6 Structured outputs and context

- **Every call returns JSON matching a schema** (structured outputs, `output_config.format`). There is one schema per call type: `input_review`, `output_review`, `explain`.
- A flag in the schema has: `category` (enum), `title`, `what_i_saw`, `rule_ref`, optional `evidence` (photo region or page), optional `suggestion` (a list of `{field, value, reason}` limited to the input-field enum), and optional `escalate` (`{to: "gus"|"boss"|"either", question}`).
- `explain` returns `{answer, rule_refs, summary_keys}`; the app checks that every number in `answer` is in the summary, job or rules.
- A response that fails the schema is stored, shown as "AI review failed" and not used.
- **Context:**
  - The rules part of the prompt (CLAUDE.md business rules + `rules.json`) goes first and is the same for every call, so it is cached (prompt caching).
  - The job's own data comes after it.
  - Past jobs are a short table (type, site, run, height, sheets, uprights) of up to 10 approved jobs, picked by job type and site from the SQLite index. No photos or client details from other jobs are sent.

### 8.7 Model and API settings

All of these live in `config.toml`, are shown on the AI usage screen, and are recorded with every call:
- **Model ID pinned:** `claude-opus-5-5` (Claude Opus 5.5, with vision). Changing the model is a config change with its own PR and a re-run of the recorded tests (§10).
- **Effort set explicitly:** the model's default effort is `medium`, and the plan starts there for reviews. Raising it is a measured decision, not a default.
- **Refusals:**
  - A response with `stop_reason: "refusal"` is recorded as "AI review not done". It never blocks the job, and it is never treated as an empty review.
  - **No refusal fallback: strictly one model** (decided 2026-11-02, §14). The API's fallback is a beta feature, and one pinned model keeps the reviews predictable and matching the recorded tests. A refusal is recorded and shown as "AI review not done".
  - The model ID from each response is recorded with the call, and the app checks that it is the pinned one.
- **Timeouts and retries:** the SDK's retries (429 and 5xx); a call that still fails is "AI review not done".
- **The API key** comes from `ANTHROPIC_API_KEY` (§7) and is never written to logs, reviews or the history.

### 8.8 Cost caps and when the AI is unavailable

- **A cap per job and a cap per month**, in `config.toml`: **$1 per job and $60 per month** to start (USD, the API's billing currency; decided 2026-11-02, §14). The per-job cap covers all the job's AI calls over its life. With the output review after every run, it fits about two or three review rounds; after that, calls show "AI review not done (job cap reached)". During the pilot, the AI usage screen shows how many jobs hit the cap, and the cap is raised if many do.
- **For scale:** at Opus 5.5 prices ($4 / $20 per million input / output tokens), an input review with one photo and the cached rules should cost about $0.10–0.20 (most of it the written answer and thinking, at $20 per million output tokens), and an output review with the drawings and the package around $0.20–0.40.
- **Before each call**, the app estimates the input tokens (token counting) and checks both caps. **After each call** it records the real token use and cost in `ai_calls`.
- **Over a cap, the AI is unavailable, or a refusal:** the call is skipped or recorded as "AI review not done". **The app still works:** validate, the engine, the warnings and approval are unchanged. The review page says clearly that the AI review was not done, and why.
- **A setting turns the AI off completely.** Then the app is the v0 app.

### 8.9 Privacy

The photos, job titles and site names go to the Claude API, under Anthropic's commercial terms. Nothing else is sent: no other jobs' photos, no client contacts and no prices beyond the job's own quote. This is shown once on the settings screen.

## 9. Login and access

- **v1 (Windows PC):** the app listens on `127.0.0.1:8000` only.
- **Users:** two, Gus (estimator) and his boss (manager), each created with `python -m app.users add <name> --role ...`. Password hashes (scrypt) are in SQLite.
- **Sessions and forms:** a signed session cookie, a CSRF token on every form, a login rate limit and a logout.
- **Start:** `start-bsg.bat` (activates the venv, runs `python -m app`, opens the browser), optionally run at login by a scheduled task.
- **Later, Cloudflare Tunnel:**
  - `cloudflared` points a hostname at `127.0.0.1:8000`, so no router ports are opened.
  - **Cloudflare Access** (email one-time code for Gus and his boss) sits in front, as a second lock before the app's login.
  - Cookies become `Secure`.
  - This is its own PR, after v1 works locally.

## 10. Testing

| Level | What | Tools |
|---|---|---|
| Engine (existing) | Reference jobs, test jobs, baselines, rules tests. Unchanged. | pytest |
| App unit | Storage (job folders, run numbers, immutability, draft stamping), auth, roles, backup check. | pytest |
| App routes | Every page and form through `TestClient`: login, CSRF, validate problems shown, approved runs locked, Examples read-only, DRAFT on draft downloads. | pytest + httpx |
| **"The app never calculates"** | The review page with a fake `run_summary.json` full of marker values (e.g. sheets = 9991) must show exactly those markers. A grep test: no `app/` module imports `layout_gen`, `titan`, `tape` or `quote_gen` (only the engine bridge calls `run_job`). | pytest |
| **AI reviewer, recorded** | A fake Claude client returns **recorded responses** (JSON files in `tests/ai_recordings/`). See the cases below. | pytest |
| **No real API calls** | The test suite sets no API key, blocks network sockets, and fails if a real client is created. | pytest |
| Engine through the app | Each reference job created through the app, run and compared with `expected/` using the same checks as `tests/test_reference_jobs.py`. | pytest |
| **End to end** | A real browser against a running app on a temp data folder, with the fake AI client. See the scenarios below. | **Playwright** |
| AI quality (manual, not in the suite) | A script that runs the real reviewer on the reference jobs with **seeded problems** (e.g. Medibank with the fire door removed from the form, DJ Lift with the entry moved) and reports which problems were flagged. It runs only on request, with a cost shown first. Its results decide prompt or model changes. | script |
| Windows | The same suite on Gus's PC before each release. | pytest |

**AI reviewer cases (recorded responses):**
- the schema is enforced;
- an invented category becomes safety;
- a suggestion for a field outside the list is dropped;
- an explanation with a new number is hidden;
- a safety flag blocks the run and the approval;
- "Not sure" keeps the job blocked and creates an escalation;
- "Yes" opens the form with the estimates ticked and nothing saved;
- a refusal or schema failure shows "AI review not done" and doesn't block;
- the caps skip calls;
- every answer lands in `audit`.

**End-to-end scenarios:**
- log in, create Bikini, upload the photo, answer the recorded flags, run, review (11 sheets, 11 uprights, 77 weights, read from `expected_counts.json`), approve, download the package and check its text;
- a safety flag that blocks the run until answered;
- "Yes, change it" lands on the form with estimates;
- a draft download carries "DRAFT - not approved";
- the boss's login sees Gus's job and the escalation.

## 11. Build order (small PRs, each from main, test first)

**Done:** engine `validate.check` (#20), `jobs.normalize` + `jobs.warnings` (#21), rules 6 and 7 (#22, #23).

**App core (standard jobs, no AI):**
1. **App skeleton:** `app/` package, FastAPI, base template, static files, settings (`BSG_DATA`, `config.toml`), `python -m app`, a health page.
2. **Users and login:** two users with roles, sessions, CSRF, rate limit, logout.
3. **Storage:** data folder, SQLite schema (incl. `flags`, `escalations`, `ai_calls`, `audit` tables, empty for now), job and run folders, rebuild-index, daily backup task + last-backup check.
4. **Job list + Examples + new job form (standard jobs)**, through `normalize` and `validate`, with the estimate ticks.
5. **Photo upload:** type and size checks, preview, replace.
6. **Run:** worker, lock, status page, engine errors shown.
7. **Review screen:** images, materials table, quote, summary, engine warnings, changes since the last run.
8. **Approve, downloads (DRAFT stamping), job history.**

**AI reviewer (each its own PR):**
9. **AI client layer:**
   - the config (pinned model, effort; no fallback);
   - the fake client and recordings;
   - the network block in tests;
   - token estimate + caps + the `ai_calls` ledger;
   - the AI usage screen.
10. **Flags and answers:** the flag store, the three answers, the level-from-category map, blocking of run and approval, the audit trail, the escalations screen. Tested with hand-written flags; no AI call yet.
11. **Input review:** schema, prompt, context (rules cached, past jobs table), suggestions → form with estimates.
12. **Output review + "explain this number":** schema, the number check on explanations.
13. **AI quality script** with seeded problems (manual, §10).

**Remaining:**
14. **Corner, U, fire-door and external forms** (faces editor, track section, extra weight question).
15. **Rules page** (read-only, provisional highlighted).
16. **Playwright end-to-end suite** + `start-bsg.bat` + README section.
17. **Later:** Cloudflare Tunnel + Access (its own PR and checklist).

## 12. What could go wrong (and what the plan does about it)

| Risk | Answer in the plan |
|---|---|
| The AI is confidently wrong | It only flags; a person answers. Safety categories always block until answered. The AI quality script measures misses before any prompt or model change. |
| The AI is too noisy | Normal flags don't block. Flag counts per job are in the history, so noisy categories can be tuned with data. |
| A suggestion sneaks a value in | Suggestions are limited to input fields, arrive as estimates, and only a person's save writes job.json. |
| The API costs more than planned | Caps per job and per month, checked before every call; usage shown on screen. |
| The API is down or refuses | The app works without it and says "AI review not done". |
| A new model behaves differently | The model is pinned; changing it is a PR that re-runs the recorded tests and the quality script. |

## 13. Answers to the v0 questions (2026-11-02)

1. **Data folder:** `C:\BSG\data`, outside the repo, with a **daily backup to another drive** (§7).
2. **Reference jobs:** shown **read-only as "Examples"**.
3. **Drafts:** downloadable, with **"DRAFT - not approved" on every page**.
4. **The boss:** gets **his own login in v1**.

## 14. Answers to the v1 questions (2026-11-02)

1. **Cost caps:** **$1 per job and $60 per month** to start. Watch the AI usage screen during the pilot and raise the per-job cap if many jobs hit it (§8.8).
2. **Roles:** in v1 **both users can do everything**; the history records who did what. Roles are revisited after the pilot (§3).
3. **Output review:** **starts by itself after every engine run** (§5).
4. **Refusal fallback:** **off, strictly one model.** It's a beta feature, and one pinned model keeps the reviews predictable and matching the recorded tests. A refusal shows "AI review not done" (§8.7).

The plan was approved on 2026-11-02. The app core (§11, steps 1-8) starts after this PR is merged.
