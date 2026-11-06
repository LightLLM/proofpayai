# Final QA / demo acceptance test

**Deadline: Thursday Nov 12, 2026, 12:00pm PST.** Submit by Nov 11.

## API acceptance
- [ ] `cd backend && pytest -q` passes.
- [ ] `GET /api/health` returns `sandbox-only`.
- [ ] No PayPal keys or AI keys appear in repo, screenshots, network requests (other than public client ID), or logs.
- [ ] Seed request is present after first launch.
- [ ] Before approval `/paypal/create-order` returns 400.
- [ ] Cheapest offer (460V) is rejected for 230V equipment.
- [ ] Unapproved vendor cannot be purchased.
- [ ] Compatible $425 offer passes.
- [ ] AI response says `AI MODEL ACTIVE` after real provider inference.
- [ ] Lowering budget below $425 makes $425 offer ineligible (verify via API test fixture).

## Checkout acceptance
- [ ] Configured credentials are from a PayPal **sandbox business app**.
- [ ] Sandbox personal buyer is different from seller account.
- [ ] Browser checkout opens and sandbox buyer authorizes.
- [ ] Server receives actual PayPal order ID.
- [ ] Server receives actual capture ID and checks exact USD amount.
- [ ] Screen shows **Payment verified** ONLY after a completed real sandbox capture.
- [ ] Repeat create/capture calls do not produce extra orders/captures.
- [ ] Cancelled checkout never shows `PAID`.
- [ ] PayPal sandbox account confirms transaction in developer dashboard.

## Build / deploy acceptance
- [ ] `cd frontend && npm install && npm run lint && npm run build` passes.
- [ ] Frontend reaches backend over HTTPS and `CORS_ORIGINS` is correct.
- [ ] Public demo is protected from unrestricted anonymous writes and does not expose sandbox secrets.
- [ ] Clean browser can view demo/test with clear instructions until judging completes.
- [ ] Synthetic suppliers/payee distinction is clear.
- [ ] Repository is public and has visible LICENSE, documentation, build and test instructions.
- [ ] Public YouTube video under 3 minutes is accessible anonymously.
- [ ] All submission fields and links are correct on Devpost.
- [ ] No claim of AG Studio award implementation unless actually added.
