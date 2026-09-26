---
name: pse-staged-ui-origin-must-match-cors
description: A separate PSE staged frontend can show Failed to fetch at login when its localhost and 127.0.0.1 origins differ from the staged API CORS allowance.
metadata: { type: gotcha }
---

During the Batch 25 staged browser check, the frontend ran at `http://127.0.0.1:4040` while the staged API was configured with `CLIENT_URL=http://localhost:4040`. A valid temporary login returned `Failed to fetch` in the browser even though direct API registration and the 258-detail HTTP verifier worked. A local CORS preflight to `/api/auth/login` with `Origin: http://127.0.0.1:4040` returned `400 Disallowed CORS origin`. Restarting the staged API with `CLIENT_URL=http://127.0.0.1:4040` and Vite with `VITE_API_URL=http://127.0.0.1:4038` made the signed-in UI pass.

**Why:** Browser origin comparison treats `localhost` and `127.0.0.1` as different hosts, even when they reach the same local service. Direct HTTP checks do not exercise CORS.

**How to detect / apply:** For separate staged API/UI ports, choose one hostname and use it consistently in the browser URL, `CLIENT_URL` and `VITE_API_URL`. If browser login alone says `Failed to fetch`, test one CORS preflight with the actual frontend `Origin` before blaming authentication, catalog integrity or model code. See [[pse-bulk-api-verification-respects-shared-rate-limit]].
