# Devpost submission — ready to edit before publishing

**Title:** ProofPay AI — From Machine Downtime to Verified Payment

**Tagline:** An AI purchasing agent for industrial teams that refuses unsafe orders, explains decisions, requires human approval and verifies PayPal sandbox checkout.

## Inspiration

A single unavailable industrial replacement part can stall a production line, yet small factories often coordinate their purchasing in chat, email and spreadsheets. Buying the wrong motor is just as costly as waiting for a compatible one. We asked: what if an AI agent could do the research and still make no unauthorized purchase?

## What it does

ProofPay accepts a purchasing request with a technical specification and a spending ceiling. It compares supplier offers, performs hard engineering compatibility checks, and optionally asks an AI model to explain the ranking. A purchasing lead reviews and explicitly approves an eligible offer. The buyer completes PayPal sandbox checkout. ProofPay confirms the captured USD amount, currency, capture status and PayPal capture ID before recording a verified transaction in its immutable-in-intent, append-only-at-application-level audit view.

One visual moment makes the concept clear: a $299 motor appears cheaper, but it is a 460V unit for a 230V machine. ProofPay refuses to recommend or approve it. A compatible $425 offer is selected instead. The economic value is avoiding mismatches while reducing routine manual coordination — not a demonstrated real-world saving claim.

## How we built it

- Next.js / React / TypeScript responsive interface
- FastAPI, Python and SQLite purchasing workflow
- Explicit deterministic policy engine for technical compatibility, budget and supplier allowlist
- OpenAI-compatible chat-completions inference for narrative explanations (requires configured model)
- PayPal Developer sandbox OAuth2 / Orders v2 / JS Checkout SDK to create and capture buyer-authorized orders
- AG Grid Community for interactive spend records
- Pytest and mocked sandbox gateway for workflow/amount/idempotency tests

## Challenges

AI must not change payment amounts, approve its own recommendations, or invent completed payment records. We separated explanation from permission, recompute all totals server-side, store PayPal request IDs and verify completed captures. We also label real model inference vs fallback visibly.

## What we learned

AI commerce needs human intention, payment rails and a verifiable audit story. A more compelling workflow is not simply an AI shopping chat, but one in which an ineligible low-cost offer gets blocked and a verified payment is matched to an approved business purchase.

## What's next

Real supplier integrations, vendor identity verification, access roles, PayPal webhook verification, reconciliation jobs, invoice/purchase order matching, multi-tenant workspaces, Postgres and a dedicated analytics agent. None of these are claimed as already implemented.

## Demo link

**TO ADD:** Hosted demo URL (or README setup link)

## Public repository

**TO ADD:** GitHub public repository URL (must include top-level MIT LICENSE)

## Demo video

**TO ADD:** Public YouTube URL, under three minutes

## AI tools used

**TO EDIT WITH THE REAL CONFIGURATION USED:** The backend supports model inference using `AI_BASE_URL` and `AI_MODEL` with an OpenAI-compatible chat-completions interface. In the video, name the model and provider that actually performed the request and show `AI MODEL ACTIVE`. Explain that deterministic checks control merchant eligibility and amounts. If no model call occurred, do not state that a model was used.

## PayPal technologies used

PayPal sandbox OAuth2; Orders v2 Create Order and Capture Order endpoints; PayPal JavaScript Checkout SDK v5; PayPal-Request-Id idempotency headers; captured amount and currency verification. Real sandbox payment success should be shown only after it happens.

## Sponsor technologies

AG Grid **Community** is integrated. AG **Studio** is not integrated in the current codebase. Do not claim Studio Agent Framework or Studio custom widgets. For that sponsor prize, build a separately verified Studio integration and edit this text accurately.

## Ethical demo disclosure

Supplier offers and vendor reliability are synthetic test fixtures; the PayPal payment recipient is the entrant's sandbox business merchant account, not any real supplier. All commerce transactions occur exclusively in a sandbox. No real equipment or funds are moved.
