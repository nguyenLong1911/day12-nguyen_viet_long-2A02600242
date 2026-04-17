import os
import sys
import importlib.util
from fastapi.testclient import TestClient
import time

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

print("--- Testing Develop App (API Key) ---")
os.environ["AGENT_API_KEY"] = "secret-key-123"
dev_app_mod = load_module("dev_app", r"./04-api-gateway/develop/app.py")
client_dev = TestClient(dev_app_mod.app)

# a) no X-API-Key
res_a = client_dev.post("/ask", params={"question": "Hello"})
print(f"a) No Key: {res_a.status_code} {res_a.json()}")

# b) wrong X-API-Key
res_b = client_dev.post("/ask", params={"question": "Hello"}, headers={"X-API-Key": "wrong"})
print(f"b) Wrong Key: {res_b.status_code} {res_b.json()}")

# c) correct X-API-Key
res_c = client_dev.post("/ask", params={"question": "Hello"}, headers={"X-API-Key": "secret-key-123"})
print(f"c) Correct Key: {res_c.status_code} answer_present={'answer' in res_c.json()}")

print("\n--- Testing Production App (JWT & Rate Limit) ---")
# clear modules to avoid naming conflicts if necessary, though using different names here
prod_app_mod = load_module("prod_app", r"./04-api-gateway/production/app.py")
client_prod = TestClient(prod_app_mod.app)

# d) POST /auth/token
res_d = client_prod.post("/auth/token", json={"username": "student", "password": "demo123"})
token = res_d.json().get("access_token", "")
print(f"d) Auth: {res_d.status_code} TokenLen: {len(token)} Prefix: {token[:10]}...")

# e) POST /ask without token
res_e = client_prod.post("/ask", json={"question": "Hello"})
print(f"e) No Token: {res_e.status_code} Detail: {res_e.json().get('detail')}")

# f) POST /ask with bearer token
res_f = client_prod.post("/ask", json={"question": "Hello"}, headers={"Authorization": f"Bearer {token}"})
print(f"f) With Token: {res_f.status_code} Keys: {list(res_f.json().keys())}")

# g) rate limiting
print("g) Rate Limiting (12 calls):")
statuses = []
for i in range(12):
    r = client_prod.post("/ask", json={"question": f"Q{i}"}, headers={"Authorization": f"Bearer {token}"})
    statuses.append(r.status_code)

first_429 = next((i for i, s in enumerate(statuses) if s == 429), "None")
print(f"Statuses: {statuses}")
print(f"First 429 index: {first_429}")
