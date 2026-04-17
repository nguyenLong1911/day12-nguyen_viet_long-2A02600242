# Deployment Information

## Public URL
https://day12-agent-railway-production.up.railway.app

## Platform
Railway

## Status
- Service is reachable on public internet.
- Verified endpoints:
  - GET / -> 200
  - GET /health -> 200

## Test Commands

### Health Check
```bash
curl https://day12-agent-railway-production.up.railway.app/health
# Expected: {"status":"ok", ...}
```

### Root Endpoint
```bash
curl https://day12-agent-railway-production.up.railway.app/
# Expected: {"message":"AI Agent running on Railway!","docs":"/docs","health":"/health"}
```

### Ask Endpoint
```bash
curl -X POST https://day12-agent-railway-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello from Railway"}'
# Expected: 200 with question + answer + platform
```

## Environment Variables Set (Railway)
- PORT=8000
- AGENT_API_KEY=my-secret-key

Note:
- This Part 3 Railway app currently does not enforce API key auth in endpoint logic.
- REDIS_URL and LOG_LEVEL are not required for this specific Part 3 service.

## Screenshots
- Captured from real endpoint outputs at `2026-04-17 16:57:37 +07:00`.
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
