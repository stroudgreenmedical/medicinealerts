Amazing—thanks for the specifics. I’ll lock those into the plan:

* **EHR:** EMIS Web (with Ardens installed)
* **Messaging:** iPlato and Accurx exist but **no patient comms automation**; pharmacist handles searches + comms **inside EMIS**
* **Storage:** one **Excel workbook in your Teams/SharePoint folder** (the one you linked) is the source‑of‑truth log
* **Workflow:** service ingests alerts, **auto‑triages**, **auto‑closes not relevant**, **notifies pharmacist in Teams**, and **appends a row to the Excel register** for every alert; from there, **pharmacist records actions in Excel**
* **Polling:** every 4 hours
* **Retention:** 8 years
* **Approver:** Chandni Shah; **Clinical fallback:** Dr Anjan Chakraborty

I’ve written the PRD below assuming a **headless Python service** (no new task app), plus a tiny status page (optional). If anything looks off, say the word and I’ll tweak.

---

# Safety Alerts Automator — PRD (for Claude Code)

## 1) Outcome & scope (what this must do)

A small Python service that:

1. **Ingests** MHRA alerts from GOV.UK (including the new **MHRA Safety Roundup**) and legacy **Drug Safety Update** items. ([GOV.UK Developer Documentation][1], [GOV.UK][2])
2. **Auto‑triages** each item for GP relevance (rules below) and **auto‑closes** not‑relevant items.
3. **Writes/updates one Excel register** (in the supplied Teams/SharePoint folder) with an **immutable row** per alert (populated with alert metadata + auto‑classification); pharmacist later edits the action columns. **No patient automation.**
4. **Notifies** the pharmacist via **Teams** (channel post), linking to the alert on GOV.UK and the Excel workbook. ([Microsoft Learn][3])
5. **Reports:** one‑click monthly/annual **summary report** generated **from the Excel register** (counts by type/status, open vs closed, SLA timings).
6. **Retention:** keep register entries for ≥8 years.

**Explicitly out of scope (Phase 1):** direct EMIS actions, Ardens API calls, auto‑generating patient lists or messaging. (Pharmacist does EMIS searches and comms; they record outcomes in the workbook.)

---

## 2) Data sources & truth

* **GOV.UK Search API** (public, JSON) for discovery: `https://www.gov.uk/api/search.json` (supports filters like `filter_content_store_document_type`, `order`, `count`, `start`, `fields`). It’s the same API that powers GOV.UK finders. ([API Catalogue][4], [GOV.UK Developer Documentation][5])

  * Document type: **`medical_safety_alert`** (this powers the “Alerts, recalls and safety information” finder). ([GOV.UK Developer Documentation][1])
  * Also pull legacy **`drug_safety_update`** to catch historical DSU items. ([GOV.UK][6])
* **GOV.UK Content API** for per‑page structured metadata (`/api/content/<path>`). Use it to fetch message type, medical specialties, and body sections for each alert page. ([Content API][7], [GOV.UK][8])
* **Finder page** (human reference): “Alerts, recalls and safety information” (has **Subscribe to feed**; page UI shows **Message type**, **Medical specialty**, **Issued**). ([GOV.UK][2])
* **Context note:** since **March/April 2025**, MHRA introduced the **MHRA Safety Roundup** as the monthly digest; treat it as part of `medical_safety_alert` (continue to collect DSU for archives). ([GOV.UK][9])

---

## 3) Core user story (as‑is workflow)

* **Every 4 hours**, the service fetches new GOV.UK items → auto‑triages →

  * If **Relevant**, it appends a row to the **Excel register** (status = “New, requires review”) **and** posts to the **Teams channel** to alert **Chandni** (with a link to GOV.UK + the workbook).
  * If **Not relevant**, it still appends a row (status = “Auto‑closed – not GP/dispensing”) but **does not** ping Teams.
* Chandni opens the workbook, performs **Ardens/EMIS** steps, and **records actions** in the workbook (no new app).
* Reports are generated straight from the workbook.

---

## 4) Relevance rules (Phase 1)

Mark as **Relevant** if **any** of the following are true:

* Alert’s **Medical specialty** includes **“General practice”** or **“Dispensing GP practices”** (taken from the page metadata). ([GOV.UK][10])
* Message type is **National Patient Safety Alert** **and** specialties include GP (rare, but keep). ([GOV.UK][11])
* Message type is an **MHRA Safety Roundup** (monthly digest) **and** specialties include GP/Dispensing GP. ([GOV.UK][10])

Otherwise: **Auto‑close** as “Not relevant (rule‑based)”.

> Allow an **override list** (JSON in config) where we can force‑include or force‑exclude by content\_id or keyword if the tags are missing or misleading.

---

## 5) Excel register (single source of truth)

**Location**: the SharePoint/Teams folder you provided.
**Workbook name**: `MHRA_Alerts_Register.xlsx` (configurable).
**Table name**: `AlertsRegister` (Graph Excel API writes rows to a **Table**, not a naked range). ([Microsoft Learn][12])

**Columns (in order)**

1. `content_id` (GUID from GOV.UK)
2. `url` (GOV.UK page)
3. `title`
4. `doc_type` (`medical_safety_alert` or `drug_safety_update`)
5. `message_type` (e.g., Medicines recall/notification, National Patient Safety Alert, MHRA Safety Roundup)
6. `medical_specialties` (pipe‑separated list; keep exactly as GOV.UK shows)
7. `published_at` (UTC ISO 8601)
8. `issued_date` (if present)
9. `relevance` (Auto‑Relevant | Auto‑Not‑Relevant)
10. `auto_reason` (e.g., “specialty includes General practice”)
11. `teams_notified` (True/False)
12. `approver` (defaults to “Chandni Shah”)
13. `fallback_approver` (defaults to “Dr Anjan Chakraborty”)
14. `action_status` (New | In progress | Completed | Not relevant) — **pharmacist edits**
15. `action_summary` (free text) — **pharmacist edits**
16. `action_dates` (free text or “started; completed”) — **pharmacist edits**
17. `evidence_links` (optional links to EMIS docs / SOPs / uploaded files) — **pharmacist edits**
18. `last_updated_by_service` (timestamp; the bot’s last touch)
19. `notes` (free text; service or pharmacist)

**Why a Table:** the Graph **Excel REST API** appends rows to a **table** (`…/workbook/tables/{name}/rows/add`), which is faster and safer than range math; supports batching; works fine on **SharePoint‑stored** workbooks. ([Microsoft Learn][13])

---

## 6) Teams notification

* **Default**: **Incoming Webhook** into the “Pharmacist / MHRA Alerts” channel. Payload: a simple card with title, message type, specialties, publish/issued dates, and **two links** (“Open GOV.UK page” and “Open Excel register”). (Incoming webhooks are channel‑only; they cannot DM Chandni.) ([Microsoft Learn][3])
* **Optional (later):** Switch to **Graph `channelMessage`** to enable @mentions and richer formatting; requires Azure AD app + delegated permissions to the Team. ([Microsoft Learn][14])

---

## 7) Ingestion details

**Queries (Search API):**

* Alerts finder items (includes Safety Roundup, recalls, NatPSAs, FSNs…):

  ```
  GET /api/search.json
    ?filter_content_store_document_type=medical_safety_alert
    &filter_organisations=medicines-and-healthcare-products-regulatory-agency
    &order=-public_timestamp
    &count=100
    &fields=title,link,public_timestamp,description,content_id
  ```
* Historical **Drug Safety Update** items:

  ```
  GET /api/search.json
    ?filter_content_store_document_type=drug_safety_update
    &order=-public_timestamp
    &count=100
    &fields=title,link,public_timestamp,description,content_id
  ```

(See GOV.UK Search API docs; the v1 endpoint is public and powers finder pages.) ([API Catalogue][4], [GOV.UK Developer Documentation][5])

**Per‑item enrichment (Content API):**

* `GET /api/content/<path>` to fetch structured fields (message type, medical specialities, issue date, sections). ([Content API][7])
* Example of the page structure (shows message type & specialties on the live page): **MHRA Safety Roundup: July 2025**. ([GOV.UK][10])

**Backfill job:**

* One‑off scan back through **8 years** using Search API pagination (`start` + `count`), ordered by **oldest first** (`order=public_timestamp`) to avoid missing items if the job is interrupted. ([Data in Government][15])

**Deduplication key:** `content_id` (GOV.UK UUID). If an item already exists in the Excel table, **update in place** (by content\_id match) for any metadata changes; do **not** overwrite pharmacist‑edited columns.

---

## 8) Architecture (minimal + robust)

* **Runtime:** Python 3.12 container (Azure Container Apps) with a single **worker** (APScheduler) on a 4‑hour schedule.
* **No separate DB** (Phase 1): use the **Excel table as the ledger**; keep a small local SQLite cache for `content_id` seen (optional).
* **Outbound integrations:**

  * **GOV.UK** Search + Content APIs over HTTPS. ([API Catalogue][4], [Content API][7])
  * **Teams**: Incoming Webhook (URL stored in Key Vault/app settings). ([Microsoft Learn][3])
  * **Graph Excel API**: append/update rows in the SharePoint workbook (App Registration, client credentials flow). ([Microsoft Learn][12])
* **Monitoring:** console logs shipped to Azure Log Analytics; alert on failures or when GOV.UK calls exceed retry budget.

**Key libraries:** `httpx` (with timeouts), `tenacity` (retries), `pydantic` (models), `msal` (Graph auth), `python-dateutil`.

---

## 9) Graph integration details (Excel in SharePoint)

1. Resolve the **site** and **drive** for your Team (Graph).

   * Example: `GET /v1.0/sites/{hostname}:/sites/{teamSiteName}` → site ID
   * Then: `GET /v1.0/sites/{site-id}/drives` to find “Documents” drive (a.k.a. “Shared Documents”). ([Microsoft Learn][16])
2. Resolve the **workbook** by path:

   * `GET /v1.0/sites/{site-id}/drive/root:/GP PM Pharmacist/MHRA Alerts/MHRA_Alerts_Register.xlsx` → driveItem ID. ([Microsoft Learn][17])
3. Ensure a **Table** named `AlertsRegister` exists (create once if missing).
4. **Append rows**:

   * `POST /workbook/tables/AlertsRegister/rows/add` with batched `values` (array of arrays). (Graph supports batching; avoid one‑row‑at‑a‑time.) ([Microsoft Learn][13])
5. **Update existing** (idempotence): find the row by `content_id` (use a hidden `Index` column or search the table range) and update the row range.

---

## 10) Teams integration details

* **Incoming Webhook** to a dedicated channel (e.g., “Pharmacist ⟶ MHRA Alerts”). Card body:

  * Title, message type, specialties, publish/issue dates
  * “Open on GOV.UK” link
  * “Open Excel register” link (SharePoint URL)
* Note: webhooks **cannot @mention** users; if you need true mentions, use **Graph** to `POST /teams/{id}/channels/{id}/messages` with mentions (requires delegated permissions). ([Microsoft Learn][3])

---

## 11) Status & reporting

* Optional **status page** (FastAPI) with `/health` and a read‑only list of the last 50 processed items (title + status).
* **Report generator** (Python): reads the Excel table via Graph, produces `MHRA_Alerts_Report_{YYYY-MM}.xlsx` back into the same folder with pivots:

  * by **message type** (recall, NatPSA, Roundup, FSN, etc.)
  * **Relevant vs Auto‑closed**
  * **Elapsed days** from publish to first pharmacist edit (SLA proxy)

---

## 12) Security, privacy, compliance

* **No patient data** touched by the service.
* **Secrets** in Azure App Settings/Key Vault.
* Graph scopes: `Sites.ReadWrite.All`, `Files.ReadWrite.All` (or narrower site‑scoped permissions).
* You’ve said **no DCB0160** required; we’ll keep the footprint minimal and patient‑free accordingly.

---

## 13) Acceptance criteria

1. New GOV.UK items appear in Excel within **≤30 minutes** of publish (given the 4‑hour polling, we accept a worst‑case of \~4h + 30m).
2. For each item, the Excel row contains: title, GOV.UK URL, `content_id`, doc\_type, message\_type, specialties, published/issued dates, relevance decision, auto\_reason. (Message type + specialties demonstrably appear on the live page.) ([GOV.UK][10])
3. Items **without GP/Dispensing GP specialties** are **auto‑closed** and logged; **no Teams message** sent.
4. Items **with GP/Dispensing GP** are logged as **Relevant** **and** trigger a Teams post with links. ([Microsoft Learn][3])
5. Backfill job populates the workbook with **8 years** of alerts (deduped by `content_id`).
6. Reports can be generated on demand (monthly/yearly) from the register.

---

## 14) Delivery plan

* **Sprint 1 (Ingest + Log):** GOV.UK Search/Content client; Excel writer (create table, append rows); minimal config; run manual backfill. ([API Catalogue][4], [Content API][7])
* **Sprint 2 (Triage + Teams):** implement rules; auto‑close; Teams webhook message. ([Microsoft Learn][3])
* **Sprint 3 (Reports + Hardening):** report builder; status page; retries/alerts; clean docs.

---

## 15) Config (env vars)

* `GOVUK_SEARCH_ENDPOINT=https://www.gov.uk/api/search.json`
* `ORG_FILTER=medicines-and-healthcare-products-regulatory-agency`
* `EXCEL_SITE_HOSTNAME=nhs.sharepoint.com`
* `EXCEL_SITE_PATH=/sites/msteams_d73c2d-GPPMPharmacist`
* `EXCEL_WORKBOOK_PATH=/Shared Documents/GP PM Pharmacist/MHRA Alerts/MHRA_Alerts_Register.xlsx`
* `EXCEL_TABLE_NAME=AlertsRegister`
* `TEAMS_WEBHOOK_URL=...`
* `APPROVER_PRIMARY="Chandni Shah"`
* `APPROVER_FALLBACK="Dr Anjan Chakraborty"`
* `POLL_CRON="0 */4 * * *"`
* `ALLOWLIST=[], DENYLIST=[]` (content\_ids)

---

## 16) Test cases (condensed)

* **Relevance positive:** An MHRA Safety Roundup page **with** “General practice” specialty → row with Relevant; Teams post created. (Example page shows specialties incl. General practice.) ([GOV.UK][10])
* **Relevance negative:** A device alert **without** GP/Dispensing GP specialties → row with Auto‑Not‑Relevant; **no** Teams post.
* **Retry logic:** transient 5xx from Search API → retried (exponential backoff) → success.
* **Idempotence:** re‑poll same content\_id → row is not duplicated.
* **Backfill:** runs from 8 years ago to today (paged with `start/count`), populates workbook; total row count matches Search API count for filters (± withdrawn items). ([Data in Government][15])
* **Excel concurrency:** workbook open by user → Graph still appends rows to the table (expected behavior). ([Microsoft Learn][12])

---

## 17) Open choices (defaults below—confirm or edit)

* **Teams channel** to receive notifications: default “GP PM Pharmacist” team, channel “MHRA Alerts”.
* **Webhook vs Graph for messages:** default **Incoming Webhook** (simpler); upgrade to Graph later if you want @mentions. ([Microsoft Learn][3])
* **Status page:** optional (I’d still add it—very light lift).
* **Workbook naming & sheet layout:** as specified; happy to adopt your naming convention if preferred.

---

## Notes on the data landscape (important context)

* **Search API** is officially described as **“unsupported”** (stable in practice, but may change)—we’ll code defensively. If it ever shifts toward **Search API v2**, we can adapt since the Content API still gives us the per‑page structure. ([GOV.UK][18], [GOV.UK Developer Documentation][19])

---



If you’re happy with the above, I’ll hand Claude Code a build checklist (Endpoints, models, example payloads, Graph scopes, and pseudocode for the poller and Excel writer) next.

[1]: https://docs.publishing.service.gov.uk/document-types/medical_safety_alert.html?utm_source=chatgpt.com "Document type: medical_safety_alert - GOV.UK Developer Documentation"
[2]: https://www.gov.uk/drug-device-alerts?utm_source=chatgpt.com "Alerts, recalls and safety information: medicines and medical devices"
[3]: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook?utm_source=chatgpt.com "Create an Incoming Webhook - Teams | Microsoft Learn"
[4]: https://www.api.gov.uk/gds/gov-uk-search/?utm_source=chatgpt.com "GOV.UK Search - API Catalogue"
[5]: https://docs.publishing.service.gov.uk/repos/search-api.html?utm_source=chatgpt.com "Application: search-api - GOV.UK Developer Documentation"
[6]: https://www.gov.uk/drug-safety-update?utm_source=chatgpt.com "Drug Safety Update - GOV.UK"
[7]: https://content-api.publishing.service.gov.uk/reference.html?utm_source=chatgpt.com "API reference - Content API"
[8]: https://www.gov.uk/api/content/drug-device-alerts?utm_source=chatgpt.com "Welcome to GOV.UK"
[9]: https://www.gov.uk/government/news/mhra-launches-new-monthly-safety-bulletin-and-redesigned-safety-alerts?utm_source=chatgpt.com "MHRA launches new monthly safety bulletin and redesigned safety alerts"
[10]: https://www.gov.uk/drug-device-alerts/mhra-safety-roundup-july-2025 "MHRA Safety Roundup: July 2025 - GOV.UK"
[11]: https://www.gov.uk/drug-device-alerts/national-patient-safety-alert-medical-beds-trolleys-bed-rails-bed-grab-handles-and-lateral-turning-devices-risk-of-death-from-entrapment-or-falls-natpsa-slash-2023-slash-010-slash-mhra?utm_source=chatgpt.com "National Patient Safety Alert: Medical beds, trolleys, bed rails, bed ..."
[12]: https://learn.microsoft.com/en-us/graph/api/resources/excel?view=graph-rest-1.0&utm_source=chatgpt.com "Working with Excel in Microsoft Graph - Microsoft Graph v1.0"
[13]: https://learn.microsoft.com/en-us/graph/api/tablerowcollection-add?view=graph-rest-1.0&utm_source=chatgpt.com "TableRowCollection: add - Microsoft Graph v1.0 | Microsoft Learn"
[14]: https://learn.microsoft.com/en-us/graph/api/channel-post-messages?tabs=http&view=graph-rest-1.0&utm_source=chatgpt.com "Send chatMessage in a channel - Microsoft Graph v1.0"
[15]: https://dataingovernment.blog.gov.uk/2016/05/26/use-the-search-api-to-get-useful-information-about-gov-uk-content/?utm_source=chatgpt.com "Use the search API to get useful information about GOV.UK content"
[16]: https://learn.microsoft.com/en-us/graph/api/resources/sharepoint?view=graph-rest-1.0&utm_source=chatgpt.com "Working with SharePoint sites in Microsoft Graph"
[17]: https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0&utm_source=chatgpt.com "Get driveItem - Microsoft Graph v1.0 | Microsoft Learn"
[18]: https://www.gov.uk/help/reuse-govuk-content?utm_source=chatgpt.com "Reuse GOV.UK content"
[19]: https://docs.publishing.service.gov.uk/manual/govuk-search.html?utm_source=chatgpt.com "GOV.UK Search: how it works - GOV.UK Developer Documentation"
