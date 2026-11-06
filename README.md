# ProofPay AI — Industrial procurement with verified sandbox payments

**PayPal AI Hackathon 2026 entry candidate** | Next.js 15 + FastAPI + SQLite + PayPal Orders v2 + optional OpenAI-compatible AI inference + AG Grid Community.

> **Status:** GitHub-ready runnable code prototype, NOT a production commerce platform. Backend tests are automated. The frontend build and an end-to-end PayPal sandbox transaction require local setup and your own PayPal developer credentials. No hosted demo, public repository, or YouTube demo has been published by this package.

## The 60-second product explanation
A factory needs a replacement motor. ProofPay compares synthetic suppliers against the exact fit, approved-supplier policy, and hard budget. An optional AI model explains the ranked results; a deterministic rules engine alone decides eligibility. An AI natural-language intake tool can turn a detailed motor request into a reviewed, structured request. A purchasing lead explicitly approves a compatible quote, after which the buyer completes PayPal sandbox checkout. The server checks the exact captured USD amount, capture status, and transaction ID before showing **Payment verified** and writing an audit event.

**Important sandbox distinction:** The demo supplier catalog is simulated and does not contain real merchants, inventories, offers, or supplier PayPal accounts. In checkout, the payment goes to **your configured PayPal sandbox merchant**, not to the fictional supplier shown in the UI. It is a payment-protocol proof of concept, not a vendor disbursement or escrow platform.

## Features
- Polished responsive purchasing command center, status cards, task workflow, comparison of quotes, approval screen, payments and audit history.
- Four reproducible synthetic offer fixtures: $299 incompatible voltage, $425 eligible preferred, $489 eligible slower, $365 unapproved vendor.
- Hard rules for product type, horsepower, voltage, ±25 RPM, shaft, allowlisted seller, and maximum combined price + shipping.
- AI requirements extraction from natural language (requires all important technical details explicitly stated; missing fields are rejected rather than guessed).
- Optional **real model inference** through an OpenAI-compatible `/chat/completions` API (Ollama, Nebius, compatible hosted providers) for explanations. UI distinctly labels `AI MODEL ACTIVE` versus `RULES-ONLY FALLBACK`. Without an AI model, the app remains usable but does **not** satisfy the hackathon's meaningful-AI demonstration on its own.
- Explicit purchasing-lead approval prior to creating a PayPal order. Approval is a demo user action, **not identity/authentication enforcement**.
- PayPal sandbox OAuth2, Orders v2 `create-order`, buyer approval with PayPal JS SDK v5, `capture`, server-side amount/currency/status check, payment audit evidence and idempotency headers.
- Interactive analytics table with AG Grid Community. **AG Studio is not included**; do not apply for or claim the AG Studio sponsor prize until integrated and demonstrated.
- SQLite audit records, API documentation at `/docs`, Python unit/integration tests with mocked PayPal responses.

## Run locally (two terminals)

Prerequisites: Python **3.11–3.13**, Node.js **20+**, npm, a PayPal Developer sandbox business app and sandbox personal buyer. The current source uses Next.js 15 / React 19 and PayPal JS SDK v5 for the tested API contract documented in PayPal's reference materials. SDK v6 migration is a later enhancement.

### 1. API

```bash
cd backend
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env     # Windows: copy .env.example .env
```

Edit `backend/.env` (shown below). The API **automatically loads `backend/.env`** via `python-dotenv`. Start it with:

```bash
uvicorn app.main:app --reload --port 8000
```

For a quick no-credentials demo, simply use `uvicorn app.main:app --reload --port 8000`: quote analysis, approval, and audit still work, while checkout tells you to configure sandbox credentials. `DATABASE_PATH` defaults to `backend/proofpay.sqlite3` in this case.

Check: http://localhost:8000/api/health and http://localhost:8000/docs

### 2. Client

```bash
cd frontend
npm install
cp .env.example .env.local  # Windows: copy .env.example .env.local
npm run dev
```

Open **http://localhost:3000**. Click **Analyze supplier offers**, review the rejected $299 offer, click **Approve** on the $425 offer, then use the PayPal button to pay with a **sandbox personal buyer account**. The result screen should contain an actual PayPal sandbox order ID and verified capture ID.

### 3. PayPal sandbox configuration

At https://developer.paypal.com/dashboard/ create/select a sandbox **business** REST app and copy credentials. Never use your live PayPal production credentials in this prototype.

```
# backend/.env — do not commit
PAYPAL_CLIENT_ID=YOUR_SANDBOX_CLIENT_ID
PAYPAL_CLIENT_SECRET=YOUR_SANDBOX_CLIENT_SECRET
DATABASE_PATH=./proofpay.sqlite3
CORS_ORIGINS=http://localhost:3000
```

Use a **separate sandbox personal buyer account**, provided by the PayPal sandbox, to authorize payments. The business and buyer sandbox accounts must not be the same. The UI uses PayPal Checkout SDK v5 (the client ID is public by design); the secret stays on the API server. The API hardcodes `https://api-m.sandbox.paypal.com` and exposes **no production payment mode**.

### 4. Activate real AI inference for judging

Choose a model provider that supports an OpenAI-compatible Chat Completions endpoint. Example with **local Ollama**, assuming it is installed and a model has been downloaded separately:

```
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen2.5:7b
AI_API_KEY=
```

Example with another provider:

```
AI_BASE_URL=https://YOUR_COMPATIBLE_PROVIDER/v1
AI_MODEL=YOUR_MODEL_NAME
AI_API_KEY=YOUR_SERVER_SIDE_API_KEY
```

The model receives only **synthetic requirements and quotes**. It writes a concise explanation; it cannot modify the server-side eligibility decision, supplier price, approved offer or PayPal amount. If inference fails, the UI will show `RULES-ONLY FALLBACK` and its evidence in the audit history; for judging, **verify `AI MODEL ACTIVE` is visible**.

## Tests

```bash
cd backend
pytest -q
# Includes working API, quote rejection, budget constraints, approval gates,
# fake PayPal checkout/capture, duplicate/idempotent calls and tamper rejection.
```

Run a browser smoke test locally:

```bash
cd frontend
npm run lint    # TypeScript compile check
npm run build   # Next.js production build
```

**Do not claim a real payment was tested** until you successfully complete a PayPal sandbox transaction with your own credentials. Tests mock PayPal responses and do not make external transactions.

## API contract

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/config` | Public sandbox/AI configuration status (no secrets) |
| GET | `/api/requests` | List requests |
| POST | `/api/requests` | Create a motor request |
| POST | `/api/agent/parse-request` | Use real AI to extract, validate and preview a detailed motor specification |
| GET | `/api/requests/{id}` | Request, eligible offers, order, audit |
| POST | `/api/requests/{id}/analyze` | Rule-scored offers + model explanation |
| POST | `/api/requests/{id}/approve` | Human chooses eligible supplier (`{"offer_id":"ofs-02"}`) |
| POST | `/api/requests/{id}/paypal/create-order` | Authoritative server-side priced sandbox order |
| POST | `/api/requests/{id}/paypal/capture` | Verify PayPal capture (`{"paypal_order_id":"..."}`) |
| GET | `/api/overview` | Spend and order summary |

## Trust and security model

**Prototype guardrails implemented:** server-authoritative catalog amounts; deterministic exclusion checks; no LLM payment permissions; no checkout until an explicit approve action; unique order per request; provider idempotency headers; server-side capture amount/currency/status checks; audit trail; sandbox-only endpoint. PayPal buyer consent occurs inside PayPal checkout.

**Not production-ready:** no authenticated employees/roles, multi-tenant isolation, CSRF protection, payment-order reconciliation background job, webhook signature verification, rate limiting, distributed order locks, taxes, supplier KYB, procurement integrations, SOC2 controls, or real supplier onboarding. Anyone able to access an exposed API could create or approve demo requests. **Do not expose this service publicly with credentials and unrestricted write endpoints.** A judged public deployment requires at least access control and secure secret management. Also ensure PayPal sandbox order status/reconciliation is inspected when a network timeout occurs after a provider action.

## Deployment path

- **Frontend:** Vercel or Render Static/Node service; set `NEXT_PUBLIC_API_URL` to your reachable, HTTPS backend origin.
- **Backend:** Render web service using `render.yaml`, setting `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY` and `CORS_ORIGINS` in its secret environment variables.
- **Storage:** SQLite is fine for a single-process local prototype. For a persistent hosted demo replace SQLite with managed Postgres. Ephemeral Render disks can reset demo transaction history.
- Set API host authentication and safety limits before making a credentialed API publicly reachable. Always verify a fresh deployment on a clean browser and with a new sandbox purchase request.

## Submission checklist

- [ ] Devpost profile joined to PayPal AI Hackathon
- [ ] At least one real model inference shown in UI
- [ ] A complete PayPal sandbox buyer approval and verified capture shown in video
- [ ] End-to-end client tested and deployed or reproducible setup verified
- [ ] A public GitHub repository with top-level `LICENSE`
- [ ] YouTube video under 3 minutes, publicly visible
- [ ] Devpost text, screenshots, all tools used, repo, video, functional instructions
- [ ] Cite synthetic fixtures as demo data; disclose real PayPal sandbox payee is test merchant
- [ ] Submit before **Nov 12, 2026 at 12:00pm PST**, preferably Nov 11

## Submission assets

- [`docs/DEVPOST_SUBMISSION.md`](docs/DEVPOST_SUBMISSION.md) — title, pitch, long description and tool disclosure
- [`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md) — timestamped 2:45 screencast
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — technical data flow and risk controls
- [`docs/FINAL_QA.md`](docs/FINAL_QA.md) — pre-submission acceptance checks

## License
MIT. See [LICENSE](LICENSE). Open-source submission includes original app code; PayPal and AG Grid remain trademarks/property of their respective owners.

## Public hosted demo (November 2026)

- Frontend: https://proofpayai.vercel.app
- Backend: https://proofpay-sandbox-api.onrender.com
- Read-only browsing is public. For interactive mutation, click **Unlock operator** in the top navigation and enter the **DEMO_ACCESS_TOKEN** supplied privately by the maintainer. The browser stores it in sessionStorage, not the repository.
- The API validates this token on every POST/PUT/PATCH/DELETE under /api/. Do not put real customer data or production PayPal credentials in this demonstration.
- For Devpost judging, supply a **demo-specific, temporary operator token privately** in the submission's testing instructions where access is restricted to judges, or use a dedicated sandbox-only hosted instance. Never post a reusable privileged token in a public README, screenshot, or YouTube description.
- On Render configure `DEMO_ACCESS_TOKEN` in Environment, `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` from a **PayPal sandbox** REST app, and `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY` for an OpenAI-compatible model. Never use production credentials or commit .env.
- On Vercel set `NEXT_PUBLIC_API_URL=https://proofpay-sandbox-api.onrender.com` for production and preview, then redeploy if updated.
- The free Render instance uses temporary SQLite storage; operations and audit history are not durable across restarts. Do not claim production-grade persistence. Sandbox payments still require a real sandbox buyer approval and PayPal capture.
