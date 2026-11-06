# System architecture

```mermaid
flowchart TD
    U[Purchasing user / reviewer] --> UI[Next.js React command center]
    UI --> API[FastAPI workflow API]
    API --> DATA[(SQLite: requests / orders / audit)]
    API --> POLICY[Deterministic engineering / vendor / budget checks]
    POLICY --> RECOMMEND[Ranked eligible offers]
    RECOMMEND --> LLM[Optional OpenAI-compatible model]
    LLM --> EXPLAIN[Explanations only; never payment authority]
    EXPLAIN --> UI
    U --> APPROVE[Explicit approval action]
    APPROVE --> API
    API --> CHECKOUT[PayPal sandbox OAuth2 & Orders v2]
    UI --> JS[PayPal JavaScript SDK buyer checkout]
    JS --> CHECKOUT
    CHECKOUT --> VERIFY[Capture ID / COMPLETED / USD amount check]
    VERIFY --> DATA
    DATA --> UI
```

## State machine

`NEW -> ANALYZED -> APPROVED -> ORDER_CREATED -> PAID`

The LLM only explains deterministic eligible results; if it fails, the app labels `rules-only` and never claims real AI inference. Purchasing approval is a local demo button, not identity-enforced authorization. The PayPal buyer separately approves checkout with a sandbox buyer account. A recorded successful capture requires a matching server-side request, PayPal order ID, exact amount, currency and COMPLETED capture status.

## API controls

- PayPal secret never enters frontend; only public client ID does.
- Orders can only be created after selecting an eligible offer via approval action.
- Server recalculates amounts from its fixture catalog; client cannot submit payment amount.
- `orders.request_id` has a unique constraint; existing completed captures are returned idempotently.
- PayPal-Request-Id is stable for create and capture retries.
- Capture failures never mark a request `PAID`.
- The sandbox host is hard-coded server-side.

## Unimplemented production protections

Authn/authz, signing PayPal webhooks, reconciliation state machine, database concurrency locks, production-quality spend approvals, catalog integrations, tax and delivery handling. Do not use or expose as a real purchasing service.
