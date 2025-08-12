Perfect — we’ll call it **Medicines Alerts Automator**. I’ve baked in your choices (EMIS, Ardens installed, Excel-in-SharePoint as the single register, no patient automation, 4‑hour polling, auto‑close not‑relevant, backfill, and “send to you until 17 Sept, then Chandni”).

Below is a **build checklist** Claude Code can follow step‑by‑step. I’ve flagged one important technical caveat (Excel API permissions) and given you two safe implementation options—one that’s zero‑maintenance and one that enables mentions later if you want.

---

# Medicines Alerts Automator — Build Checklist (for Claude Code)

## 0) Names & constants

* Product name: **Medicines Alerts Automator**
* EHR: **EMIS Web** (Ardens installed)
* Register file: **`MHRA_Alerts_Register.xlsx`**
* SharePoint site: `https://nhs.sharepoint.com/sites/msteams_d73c2d-GPPMPharmacist` (as per your Teams path)
* Folder: `Shared Documents/GP PM Pharmacist/MHRA Alerts/`
* Teams channel for notifications (beta):
  `GP PM Pharmacist › MHRA Alerts` (deep link you provided)
  During beta **route alerts to Dr Anjan**; switch primary approver to **Chandni Shah from 17 Sept 2025**.
* Polling: every **4 hours**
* Retention: **8 years** (Excel is the source of truth)

---

## 1) Data sources to ingest (no scraping)

* **GOV.UK Search API** (JSON) — the same API that powers GOV.UK search & finders. Endpoint: `https://www.gov.uk/api/search.json`. Use filters for `medical_safety_alert` and (for history) `drug_safety_update`. ([API Catalogue][1])
* **GOV.UK Content API** — per‑page JSON for structured metadata (message type, medical specialism, issue date, sections, attachments). Endpoint root: `https://www.gov.uk/api/content`. ([API Catalogue][2], [Content API][3])
* The **“Alerts, recalls and safety information: medicines and medical devices”** finder (human check; showcases “Alert type / Medical specialism / Issued”). Your triage rules use these fields; they’re visible on the page. ([GOV.UK][4])
* Document type you’re filtering on: **`medical_safety_alert`** (includes recalls, NatPSAs, Safety Roundup, FSNs, etc.). ([GOV.UK Developer Documentation][5])

**Note:** GOV.UK’s “Reuse GOV.UK content” page documents the Search & Content APIs and notes the Search API is “unsupported”; code defensively. ([GOV.UK][6])

---

## 2) Critical design choice (Excel write method)

**Why this matters:** The **Graph Excel “add rows to table” API does not support application (app‑only) permissions**. It requires a signed‑in user (delegated). That’s awkward for a headless service. ([Microsoft Learn][7])

**We’ll take Option A now (recommended), Option B later if you want mentions/DMs:**

### Option A — File approach (no interactive sign‑in, reliable for services)

* **Download → edit workbook with `openpyxl` → upload new version** via Graph **DriveItem content** APIs (supports app‑only). This avoids Excel REST’s delegated‑only limitation. Use `PUT /drive/items/{item-id}/content` (<250 MB) or an **upload session** for larger files. ([Microsoft Learn][8])
* Handle concurrency with **ETag/`If-Match`** and retries; if the file is locked (or checked out by policy), back off and try again or log a warning. ([Microsoft Learn][9])

### Option B — Excel REST API (only if you want to @mention and go richer in Teams later)

* Run with **delegated** permissions under a dedicated “service” M365 user (device code sign‑in once; store refresh token securely). Then use **`/workbook/tables/{name}/rows/add`** — but this **won’t** work app‑only. Not recommended for v1; more operational friction. ([Microsoft Learn][7])

We’ll proceed with **Option A** below.

---

## 3) Azure/M365 setup (once)

1. **App registration** (Azure Entra)

   * Register app “Medicines Alerts Automator”.
   * Add **Application** permissions for Microsoft Graph:
     `Sites.ReadWrite.All` (or **Sites.Selected** with per‑site grant), `Files.ReadWrite.All`. Grant admin consent. ([Microsoft Learn][10])
   * Create a client secret, store in **Key Vault/App Settings**.

2. **Give the app access to the Team’s SharePoint site**

   * If using **Sites.Selected**, grant the app to the site `msteams_d73c2d-GPPMPharmacist` and approve **Read/Write**. (Least privilege.) ([Microsoft Learn][10])

3. **Teams Incoming Webhook** (simple and robust for v1)

   * In the **GP PM Pharmacist › MHRA Alerts** channel, add **Incoming Webhook** named “Medicines Alerts Automator”, copy the generated URL into `TEAMS_WEBHOOK_URL`. ([Microsoft Learn][11])

> (Later, if you want @mentions: replace webhook with a **Graph channel message** poster using delegated permissions, but keep webhook for now.) ([Microsoft Learn][12])

---

## 4) Create the Excel register (source of truth)

* Path: `Shared Documents/GP PM Pharmacist/MHRA Alerts/MHRA_Alerts_Register.xlsx`
* Sheet: `Alerts`
* **Create a Table** named `AlertsRegister` with columns:

```
content_id | url | title | doc_type | message_type | medical_specialties |
published_at | issued_date | relevance | auto_reason |
teams_notified | approver | fallback_approver |
action_status | action_summary | action_dates | evidence_links |
last_updated_by_service | notes
```

We’ll append one **immutable** row per alert; pharmacist will **only** edit the `action_*` and `evidence_links` fields.

*(Why a Table? The Excel API favors writing to tables; we’ll emulate that with openpyxl in Option A. If you ever switch to Excel REST, table rows are the native contract.)* ([Microsoft Learn][13])

---

## 5) Project structure & dependencies

```
medicines-alerts-automator/
  app/
    main.py                # entrypoint (scheduler)
    config.py
    govuk_client.py        # Search + Content API
    models.py              # Pydantic models for alerts
    triage.py              # relevance rules
    excel_rw.py            # download->edit->upload via Graph; openpyxl
    teams_notify.py        # webhook payload & post
    backfill.py            # one-off 8y import
    reporting.py           # monthly/annual summary from workbook
    graph_client.py        # MSAL app-only + Graph helpers (drive, site)
  infra/
    dockerfile
    azureapp.yaml
  tests/
    ...
```

**Python packages:** `httpx`, `pydantic`, `python-dateutil`, `openpyxl`, `msal`, (optional) `tenacity` for retries.

---

## 6) GOV.UK ingestion — exact queries

**A) Alerts (main feed):**

```
GET https://www.gov.uk/api/search.json
  ?filter_content_store_document_type=medical_safety_alert
  &filter_organisations=medicines-and-healthcare-products-regulatory-agency
  &order=-public_timestamp
  &count=100
  &fields=title,link,public_timestamp,description,content_id
```

(Primary feed that powers the MHRA finder.) ([API Catalogue][1], [GOV.UK Developer Documentation][5])

**B) Drug Safety Update (history/top-up):**

```
GET https://www.gov.uk/api/search.json
  ?filter_content_store_document_type=drug_safety_update
  &order=-public_timestamp
  &count=100
  &fields=title,link,public_timestamp,description,content_id
```

(DSU items are largely historical; MHRA now does monthly **Safety Roundup** under the alerts finder.) ([API Catalogue][1], [GOV.UK][4])

**C) Per‑item enrichment:**

* For each item, derive `base_path` from `link`, then:

```
GET https://www.gov.uk/api/content/<path>
```

Pull **message type**, **medical specialism**, **issued date**, **sections** (e.g., “Advice for healthcare professionals”) and **attachments**. ([Content API][3])

---

## 7) Relevance rules (Phase 1)

Mark as **Relevant** if:

* `medical_specialties` includes **“General practice”** or **“Dispensing GP practices”**, or
* Message type is **National Patient Safety Alert** and the specialties include GP/Dispensing GP, or
* Message type is **MHRA Safety Roundup** *and* specialties include GP/Dispensing GP.

Otherwise: **Auto‑close** as “Not relevant (rule‑based)”.

These fields are explicitly shown on the GOV.UK alerts finder (and present via Content API). ([GOV.UK][4])

> Add a simple **allow/deny list** by `content_id` or keyword in `config.json` for manual overrides if tags are missing.

---

## 8) Teams notification (beta: to Dr Anjan)

**Mechanism:** **Incoming Webhook** to the MHRA Alerts channel. Payload includes:

* Title (linked to GOV.UK), message type, specialties, publish/issued dates
* “**Assigned approver (beta): Dr Anjan Chakraborty**” until **2025‑09‑17**; switch to **Chandni Shah** after that date (config flag).
* Button links: “Open GOV.UK” and **direct link to the Excel register**.

Webhook docs & sample payloads (O365 connector cards / Adaptive Cards over webhook). ([Microsoft Learn][11])

---

## 9) Writing to Excel in SharePoint (Option A details)

**Flow per batch:**

1. **Resolve driveItem** for `MHRA_Alerts_Register.xlsx` (by site & path).
2. **GET item content** (download). ([Stack Overflow][14])
3. Use **openpyxl**: open workbook, **append** rows to table `AlertsRegister` (create table if missing), update `last_updated_by_service`.
4. **PUT content** back to the same item (`/drive/items/{item-id}/content`), with **`If-Match`** ETag when possible; otherwise retry/backoff or fall back to upload session for large files. ([Microsoft Learn][8])

> Graph supports writing/replacing file content with **app‑only** permissions to SharePoint; this avoids Excel REST’s delegated requirement for table row APIs. ([Microsoft Learn][8])

---

## 10) Backfill (one‑off)

* **Date window:** last **8 years** (oldest→newest).
* Paginate Search API with `count=100` and `start=<offset>`. (Order by `public_timestamp` ascending for resilience.) ([API Catalogue][1])
* For each item: enrich via Content API → triage → write row → **do not** notify Teams (to avoid flooding).
* After backfill, set a **cursor** to latest `public_timestamp` processed.

---

## 11) Configuration (env)

```
GOVUK_SEARCH_ENDPOINT=https://www.gov.uk/api/search.json
ORG_FILTER=medicines-and-healthcare-products-regulatory-agency

SITE_HOSTNAME=nhs.sharepoint.com
SITE_PATH=/sites/msteams_d73c2d-GPPMPharmacist
WORKBOOK_PATH=/Shared Documents/GP PM Pharmacist/MHRA Alerts/MHRA_Alerts_Register.xlsx
TABLE_NAME=AlertsRegister

TEAMS_WEBHOOK_URL=*** (channel webhook)
PRIMARY_APPROVER_BEFORE=2025-09-17
APPROVER_BEFORE=Dr Anjan Chakraborty
APPROVER_AFTER=Chandni Shah

POLL_CRON=0 */4 * * *
ALLOWLIST=[]
DENYLIST=[]
```

---

## 12) Pseudocode (core parts)

**Poller (every 4h):**

```python
items = govuk.search(doc_types=["medical_safety_alert","drug_safety_update"])
new = dedupe_against_excel(items)  # uses content_id set from workbook
for it in new:
    meta = govuk.content(it.link)
    rec = build_record(it, meta)
    rec.relevance, rec.auto_reason = triage(meta)
batch_write_to_excel([rec for rec in new])  # download->openpyxl->upload
for rec in new:
    if rec.relevance == "Auto-Relevant":
        teams.post_card(rec, approver=resolve_approver(today))
```

**Backfill (one‑off):**

```python
for page in paginate_search(since=today-8y, order="asc"):
    ... same as above, but teams.notify=False
```

---

## 13) Teams webhook payload (example)

```json
{
  "@type": "MessageCard",
  "@context": "https://schema.org/extensions",
  "summary": "MHRA alert",
  "themeColor": "0078D7",
  "title": "Class 2 Medicines Recall: Depo‑Medrone 80 mg (EL(25)A/29)",
  "sections": [{
    "facts": [
      {"name": "Message type", "value": "Medicines recall/notification"},
      {"name": "Medical specialism", "value": "General practice; Dispensing GP"},
      {"name": "Published", "value": "2025‑06‑25"},
      {"name": "Assigned (beta)", "value": "Dr Anjan Chakraborty"}
    ],
    "text": "This item has been auto‑classified as Relevant for GP/Dispensing GP."
  }],
  "potentialAction": [{
    "@type": "OpenUri",
    "name": "Open on GOV.UK",
    "targets": [{"os": "default", "uri": "https://www.gov.uk/..."}]
  },{
    "@type": "OpenUri",
    "name": "Open Excel register",
    "targets": [{"os": "default", "uri": "https://nhs.sharepoint.com/sites/.../MHRA_Alerts_Register.xlsx"}]
  }]
}
```

(Webhook set‑up & card options: Microsoft Learn.) ([Microsoft Learn][11])

---

## 14) Testing checklist

1. **Search API happy path:** Returns items with `content_id`, `link`, `public_timestamp`. ([API Catalogue][1])
2. **Content API enrichment:** For a sample alert page, we retrieve **message type**, **medical specialism**, **issued**; confirm they match the live page. ([Content API][3], [GOV.UK][4])
3. **Triage:**

   * Positive: an alert listing **“General practice”** in medical specialism → **Auto‑Relevant**.
   * Negative: device FSN without GP/Dispensing GP → **Auto‑Not‑Relevant**.
4. **Excel write:** Append two new rows; verify workbook version increments, columns populated; pharmacist‑editable columns unchanged on re‑runs. (PUT `/content` used; retries on 409/423.) ([Microsoft Learn][8])
5. **Teams message:** On Relevant only; links resolve; beta “Assigned approver” shows **Dr Anjan**; simulated **switch** after **2025‑09‑17** shows **Chandni**. ([Microsoft Learn][11])
6. **Backfill:** Eight‑year window populates without sending Teams posts; dedupe by `content_id`.
7. **Failure modes:**

   * GOV.UK 5xx → exponential backoff, skip batch not whole run.
   * SharePoint file locked → warn & retry later; no data loss.
   * Webhook unreachable → queue & retry next cycle.

---

## 15) Reporting (from Excel)

* A simple Python script `reporting.py` that reads the workbook (download), builds **monthly** and **annual** pivot summaries (by message type; Relevant vs Auto‑closed; average **publish→first action** time). Output to the same folder as `MHRA_Alerts_Report_YYYY-MM.xlsx`.

---

## 16) Operational runbook

* **Deploy** container to Azure (Container Apps/App Service).
* **Schedule** with APScheduler (inside app) or Azure Job—keep it simple in‑process.
* **Secrets** in App Settings/Key Vault (Graph tenant, client id/secret, webhook URL).
* **Logs** to Azure Log Analytics; alert on repeated SharePoint write failures or GOV.UK ingest errors.
* **Cutover date:** on **2025‑09‑17**, flip `APPROVER_*` config (or coded date check) so Teams card shows **Chandni Shah**.

---

## 17) What I still need from you (tiny)

1. Please add the **Incoming Webhook** to that Teams channel and paste me the **Webhook URL** (safe to store in app config). ([Microsoft Learn][11])
2. Confirm the **exact workbook path** matches the folder you linked; I’ll create the file & **Table** if missing.
3. Any **allow/deny keywords** you want from day 1 (we can add later too).

---

## 18) Useful docs (for Claude’s bookmarks)

* GOV.UK **Search API** (overview & endpoint). ([API Catalogue][1])
* GOV.UK **Content API** docs. ([Content API][3])
* GOV.UK alerts finder (shows the fields we parse). ([GOV.UK][4])
* Teams **Incoming Webhook** guide. ([Microsoft Learn][11])
* Graph **write to Excel** overview (context; we’re not using table rows in v1). ([Microsoft Learn][13])
* Graph **TableRow add** (shows **Application: Not supported**). ([Microsoft Learn][7])
* Graph **DriveItem content PUT** and **upload session** (our Option A upload paths). ([Microsoft Learn][8])
* SharePoint + Graph core concepts (sites, drives, items). ([Microsoft Learn][10])

---

If you want, I can also hand Claude a starter **`.env`**, a **Dockerfile**, and the two trickiest modules (`excel_rw.py` with ETag‑safe uploads, and `govuk_client.py` with pagination) so you’re running same‑day. Would you like that?

[1]: https://www.api.gov.uk/gds/gov-uk-search/?utm_source=chatgpt.com "GOV.UK Search - API Catalogue"
[2]: https://www.api.gov.uk/gds/gov-uk-content/?utm_source=chatgpt.com "GOV.UK Content - API Catalogue"
[3]: https://content-api.publishing.service.gov.uk/reference.html?utm_source=chatgpt.com "API reference - Content API"
[4]: https://www.gov.uk/drug-device-alerts "Alerts, recalls and safety information: medicines and medical devices - GOV.UK"
[5]: https://docs.publishing.service.gov.uk/document-types/medical_safety_alert.html?utm_source=chatgpt.com "Document type: medical_safety_alert - GOV.UK Developer Documentation"
[6]: https://www.gov.uk/help/reuse-govuk-content?utm_source=chatgpt.com "Reuse GOV.UK content"
[7]: https://learn.microsoft.com/en-us/graph/api/table-post-rows?view=graph-rest-1.0 "Create TableRow - Microsoft Graph v1.0 | Microsoft Learn"
[8]: https://learn.microsoft.com/en-us/graph/api/driveitem-put-content?view=graph-rest-1.0&utm_source=chatgpt.com "Upload small files - Microsoft Graph v1.0 | Microsoft Learn"
[9]: https://learn.microsoft.com/en-us/graph/api/driveitem-update?view=graph-rest-1.0&utm_source=chatgpt.com "Update a file or folder - Microsoft Graph v1.0 | Microsoft Learn"
[10]: https://learn.microsoft.com/en-us/graph/api/resources/sharepoint?view=graph-rest-1.0&utm_source=chatgpt.com "Working with SharePoint sites in Microsoft Graph"
[11]: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook?utm_source=chatgpt.com "Create an Incoming Webhook - Teams | Microsoft Learn"
[12]: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/what-are-webhooks-and-connectors?utm_source=chatgpt.com "Webhooks and connectors - Teams | Microsoft Learn"
[13]: https://learn.microsoft.com/en-us/graph/excel-write-to-workbook?utm_source=chatgpt.com "Write data to an Excel workbook - Microsoft Graph"
[14]: https://stackoverflow.com/questions/60886616/update-contents-in-driveitem?utm_source=chatgpt.com "file - Update contents in DriveItem - Stack Overflow"
