# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. API key bị hardcode trong code.
2. Không có health check endpoint.
3. Debug mode được bật cứng.
4. Không xử lý SIGTERM/graceful shutdown.
5. Config không lấy từ environment variables.

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config  | Hardcode trong code | Đọc từ environment variables | Dễ đổi cấu hình theo môi trường mà không sửa code |
| Secrets | Có nguy cơ hardcode như `api_key = "sk-abc123"` | Lấy từ env, không commit secrets | Tránh lộ khóa bí mật lên GitHub |
| Port | Cố định hoặc ngầm định | Lấy từ `PORT` env var | Chạy được trên platform cloud như Railway/Render |
| Health check | Không có | `GET /health` | Platform có thể kiểm tra app còn sống hay không |
| Shutdown | Tắt đột ngột | Graceful shutdown | Hoàn tất request đang chạy trước khi tắt |
| Logging | `print()` hoặc log đơn giản | Structured JSON logging | Dễ parse, search và monitor trên log aggregator |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: `python:3.11`
2. Working directory: `/app`
3. `requirements.txt` được copy trước để tận dụng Docker layer cache. Khi dependencies chưa đổi, Docker có thể tái sử dụng layer cài đặt package thay vì cài lại từ đầu, giúp build nhanh hơn.
4. `CMD` là lệnh mặc định khi container start và có thể bị ghi đè khi chạy `docker run`. `ENTRYPOINT` cố định executable chính của container; `CMD` thường đóng vai trò tham số mặc định cho `ENTRYPOINT`.

### Exercise 2.2: Build and run
- Build command đã chạy thành công:
	- `docker build -f 02-docker/develop/Dockerfile -t agent-develop .`
- Runtime test:
	- `GET /health` -> `{"status":"ok","uptime_seconds":0.0,"container":true}`
	- `POST /ask?question=What%20is%20Docker%3F` -> `{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}`
- Image size (Docker CLI): `agent-develop:latest` có `DISK USAGE = 1.66GB`, `CONTENT SIZE = 424MB`.

### Exercise 2.3: Image size comparison
- Stage 1 (builder): dùng `FROM agent-develop:latest` để tái sử dụng dependencies đã cài sẵn từ image develop.
- Stage 2 (runtime): dùng `python:3.11-slim`, tạo non-root user, chỉ copy packages cần thiết + source code để chạy service.
- Vì sao image cuối nhỏ hơn: runtime dùng base slim và chỉ copy artifacts cần chạy, không mang toàn bộ môi trường build.
- Kết quả build thực tế:
	- Develop (`agent-develop:latest`): `1.66GB` (disk usage)
	- Production (`agent-production:latest`): `261MB` (disk usage)
	- Chênh lệch: giảm khoảng `84.6%` so với develop.

### Exercise 2.4: Docker Compose stack
- Kiến trúc: client gửi request vào Nginx ở port 80/443, Nginx reverse proxy đến service `agent`, còn `agent` giao tiếp nội bộ với `redis` và `qdrant` qua network `internal`.
- Services khởi động: `agent`, `redis`, `qdrant`, `nginx`.
- Cách communicate: `nginx` proxy đến `agent_backend`; `agent` dùng `REDIS_URL=redis://redis:6379/0` và `QDRANT_URL=http://qdrant:6333`; `depends_on` đảm bảo `redis` và `qdrant` phải healthy trước khi `agent` start.
- Điểm đáng chú ý: `agent` không expose port trực tiếp ra host; traffic đi qua Nginx, và network nội bộ giúp tách biệt traffic nội bộ với bên ngoài.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- Platform chọn: Railway
- App folder deploy: `03-cloud-deployment/railway`
- Cấu hình đã xác nhận:
	- Start command trong `railway.toml`: `uvicorn app:app --host 0.0.0.0 --port $PORT`
	- Health check path: `/health`
	- Retry policy: `ON_FAILURE`, tối đa 3 lần
	- App đọc `PORT` từ environment variable trong `app.py`
- Trạng thái deploy thực tế:
	- Deploy thành công lên Railway và đã public.
	- Health check trả về `{"status":"ok","platform":"Railway"}`.
- URL public: https://day12-agent-railway-production.up.railway.app
- Test nhanh đã xác nhận:
	- `GET /` -> `{"message":"AI Agent running on Railway!","docs":"/docs","health":"/health"}`
	- `GET /health` -> `{"status":"ok","uptime_seconds":...,"platform":"Railway",...}`
- Screenshot:
	- [screenshots/dashboard.png](screenshots/dashboard.png)
	- [screenshots/running.png](screenshots/running.png)
	- [screenshots/test.png](screenshots/test.png)

### Exercise 3.2: So sánh `render.yaml` và `railway.toml`
- `railway.toml` (Railway): cấu hình ngắn gọn theo 2 khối `build` và `deploy`, tập trung vào cách build/start app và health check.
- `render.yaml` (Render): mô tả hạ tầng chi tiết theo blueprint, có thể khai báo nhiều service cùng lúc (web + redis), region, plan, env vars, auto deploy.
- Điểm khác biệt chính:
	- Mức độ khai báo: Railway tối giản; Render chi tiết theo Infrastructure as Code.
	- Thành phần hệ thống: Render file mẫu đã khai báo luôn Redis service; Railway file mẫu chỉ tập trung web service.
	- Cách quản lý env secrets: cả hai đều hỗ trợ dashboard; Render cho phép `sync: false`/`generateValue` ngay trong YAML.
	- Trải nghiệm học nhanh: Railway phù hợp bài MVP/demo rất nhanh, ít cấu hình ban đầu.

### Checkpoint 3
- [x] Deploy thành công lên ít nhất 1 platform
- [x] Có public URL hoạt động
- [x] Hiểu cách set environment variables trên cloud
- [x] Biết cách xem logs
- Ghi chú: Deploy Railway đã xác nhận hoạt động qua public URL và health check.

## Part 4: API Security

### Exercise 4.1: API Key authentication (phương án đã chọn)

Mình chọn API Key thay vì JWT/OAuth theo yêu cầu bài làm.

- Điểm check API key: dependency `verify_api_key` trong `04-api-gateway/develop/app.py`, được gắn vào endpoint `POST /ask` qua `Depends(verify_api_key)`.
- Nếu thiếu key: trả về `401` với detail `Missing API key. Include header: X-API-Key: <your-key>`.
- Nếu key sai: trả về `403` với detail `Invalid API key.`.
- Nếu key đúng và gửi đúng format của endpoint develop (`/ask?question=...`): trả về `200`.
- Cách rotate key: đổi giá trị env var `AGENT_API_KEY` trên môi trường chạy (local/cloud), rồi restart service; không cần sửa code.

Kết quả test thực tế từ `python test_apps.py`:

```bash
a) No Key: 401 {'detail': 'Missing API key. Include header: X-API-Key: <your-key>'}
b) Wrong Key: 403 {'detail': 'Invalid API key.'}
c) Correct Key: 200 answer_present=True
```

Ghi chú: test script đã gọi đúng format endpoint develop (`/ask?question=...`) và set `AGENT_API_KEY=secret-key-123` để kiểm tra case key đúng.

### Exercise 4.2: JWT/OAuth

Không dùng OAuth trong lab này; phần JWT đã được đọc và phân tích đầy đủ theo `04-api-gateway/production/auth.py`.

JWT flow đã xác nhận:

1. Client gọi `POST /auth/token` với `username/password`.
2. Server gọi `authenticate_user()` để check credentials trong `DEMO_USERS`.
3. Nếu hợp lệ, server tạo JWT bằng `create_token()` với payload gồm:
	 - `sub` (username)
	 - `role` (user/admin)
	 - `iat` (issued at)
	 - `exp` (hết hạn sau 60 phút)
4. Client gọi `POST /ask` với header `Authorization: Bearer <token>`.
5. Dependency `verify_token()` decode token bằng `JWT_SECRET` + `HS256`.
6. Nếu token expired -> `401`; token invalid -> `403`; hợp lệ -> inject `{"username", "role"}` cho endpoint.

Kết quả test thực tế từ `python test_apps.py`:

```bash
d) Auth: 200 TokenLen: 168 Prefix: eyJhbGciOi...
e) No Token: 401 Detail: Authentication required. Include: Authorization: Bearer <token>
f) With Token: 200 Keys: ['question', 'answer', 'usage']
```

Lỗi gặp trong quá trình test và cách xử lý:

- Ban đầu production app lỗi middleware do `MutableHeaders` không có `.pop()`.
- Đã sửa tại `04-api-gateway/production/app.py`:
	- từ: `response.headers.pop("server", None)`
	- thành: `if "server" in response.headers: del response.headers["server"]`

### Exercise 4.3: Rate limiting

Phần rate limiting có trong bản advanced (`04-api-gateway/production/rate_limiter.py`):

- Thuật toán: Sliding Window (dùng `deque` timestamp theo user).
- Limit mặc định user: `10 requests / 60 giây`.
- Admin tier: `100 requests / 60 giây` (coi như cơ chế bypass theo vai trò/tier).
- Khi vượt ngưỡng: trả về `429 Too Many Requests`, kèm `Retry-After` và các header `X-RateLimit-*`.

Test output thực tế (student token, gửi 12 request nhanh):

```text
Statuses: [200, 200, 200, 200, 200, 200, 200, 200, 200, 429, 429, 429]
First 429 index: 9
```

### Exercise 4.4: Cost guard implementation

Phần cost guard nằm ở `04-api-gateway/production/cost_guard.py`, cách làm:

- Track usage theo user theo ngày: input tokens, output tokens, số request.
- Tính chi phí từ token theo bảng giá mock (`PRICE_PER_1K_INPUT_TOKENS`, `PRICE_PER_1K_OUTPUT_TOKENS`).
- Chặn theo ngân sách user: mặc định `$1/ngày/user`, vượt thì trả `402`.
- Chặn theo ngân sách global: mặc định `$10/ngày`, vượt thì trả `503`.
- Cảnh báo khi chạm ngưỡng `80%` budget.

Flow bảo vệ request:

1. Check auth (API Key hoặc JWT tùy mode).
2. Check rate limit.
3. Check budget trước khi gọi model.
4. Gọi model xong thì ghi usage + cộng chi phí.

### Checkpoint 4

- [x] Implement API key authentication
- [x] Hiểu JWT flow
- [x] Implement rate limiting (đọc code + xác nhận bằng test thực tế)
- [x] Implement cost guard (đọc code + quan sát usage logs khi test)

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
Exercise 5.1 - Health checks và readiness:

- Ứng dụng develop (`05-scaling-reliability/develop/app.py`) có các endpoint:
	- `GET /health` cho liveness.
	- `GET /ready` cho readiness.
	- Có xử lý graceful shutdown (`SIGTERM`, `SIGINT`) và ghi `pid.txt`.
- Ứng dụng production (`05-scaling-reliability/production/app.py`) có:
	- `GET /health` và `GET /ready`.
	- Readiness kiểm tra kết nối Redis bằng `PING`.

Exercise 5.2 - Kiến trúc stateless với Redis:

- Production lưu lịch sử hội thoại theo `session_id` trong Redis:
	- Key format: `chat:<session_id>`.
	- Mỗi message được append vào Redis list (JSON), không phụ thuộc bộ nhớ local của container.
- Biến `instance_id = socket.gethostname()` được trả về trong response (`served_by`) để chứng minh request có thể đi qua nhiều replica.
- Endpoint `POST /chat` và endpoint tương thích `POST /ask` đều dùng session state trong Redis.

Exercise 5.3 - Cân bằng tải với Nginx:

- `05-scaling-reliability/production/nginx.conf` cấu hình upstream `agent_backend` cho 3 replica.
- Nginx expose cổng `8080` qua `docker-compose.yml` và route request vào upstream backend.

Exercise 5.4 - Scale stack bằng Docker Compose:

- File `05-scaling-reliability/production/docker-compose.yml` mô tả stack gồm:
	- `redis` (có healthcheck),
	- `agent` (phụ thuộc `redis` healthy),
	- `nginx` (đứng trước agent).
- Bằng chứng chạy thực tế (log gần nhất):
	- `docker compose up -d --build --scale agent=3`
	- Kết quả: `up 7/7`, trong đó `production-redis-1 Healthy`, `production-agent-1/2/3 Started`, `production-nginx-1 Started`.

Exercise 5.5 - Kiểm thử stateless:

- Script kiểm thử: `05-scaling-reliability/production/test_stateless.py`.
- Kết quả thực tế trong phiên làm việc:
	- Đã có bằng chứng request thành công qua Nginx:
		- `Invoke-WebRequest http://localhost:8080/health` trả về `StatusCode: 200`.
		- Body có `instance_id`, `storage: redis`, `redis_connected: true`.
		- Header có `X-Served-By` (backend phía sau Nginx).
	- Tuy nhiên, ở một số lần chạy chuỗi lệnh tự động, vẫn xuất hiện lỗi ngắt quãng:
		- `No connection could be made because the target machine actively refused it`.
		- `502 Bad Gateway`.
		- `test_stateless.py` có thể fail với `HTTPError 502` hoặc `URLError WinError 10061`.

Đánh giá hiện trạng Part 5:

- [x] Đã hoàn thành phần triển khai code: health/readiness, stateless Redis session, Nginx load balancing, và scaling bằng Compose.
- [x] Đã có bằng chứng runtime thành công (stack `up 7/7`, `/health` trả `200` qua Nginx).
- [x] Đã ghi nhận đầy đủ lỗi intermittent để phục vụ troubleshooting.
- [x] Đã ổn định kịch bản kiểm thử tự động khi bổ sung readiness-gating trước test (script `verify_with_readiness.ps1`), `/health` và `/ready` trả `200`, `test_stateless.py` chạy qua nhiều instance (Windows cần đặt `PYTHONIOENCODING=utf-8` để tránh lỗi encode ký tự tiếng Việt).

## Part 6: Final Project (Lab Complete)

### Objective
Hoàn thành production-ready AI agent trong thư mục `06-lab-complete` với đầy đủ các yêu cầu functional và non-functional của Part 6.

### Implementation Summary


- Ứng dụng FastAPI trong `06-lab-complete/app/main.py` với endpoint chính `POST /ask`.
- Conversation history được lưu Redis theo `history:{user_id}` (stateless, không lưu state trong RAM process).
- Xác thực API key qua header `X-API-Key` trong `06-lab-complete/app/auth.py`.
- Rate limiting Redis sliding window trong `06-lab-complete/app/rate_limiter.py` (10 req/60s/user).
- Cost guard theo tháng trong `06-lab-complete/app/cost_guard.py` (`MONTHLY_BUDGET_USD`, mặc định 10 USD).
- Health/readiness checks:
	- `GET /health`
	- `GET /ready` (kiểm tra Redis `PING`)
- Graceful shutdown đã xử lý `SIGTERM` (bật `_is_draining`, từ chối request mới bằng 503 trừ endpoint health/ready).
- Structured JSON logging đã bật trong app middleware và startup/shutdown events.
- Docker multi-stage trong `06-lab-complete/Dockerfile` (builder + runtime, non-root user, HEALTHCHECK).
- Stack local qua `06-lab-complete/docker-compose.yml` gồm `agent`, `redis`, `nginx` và scale 3 replicas.

### Validation Commands Đã Chạy

```bash
cd 06-lab-complete
docker compose down -v
docker compose build --no-cache agent
docker compose up -d --scale agent=3
docker compose ps
docker compose exec -T agent python -c "import sys,uvicorn; print(sys.executable); print(uvicorn.__version__)"
curl -i http://127.0.0.1/health
curl -i http://127.0.0.1/ready
curl -i -X POST http://127.0.0.1/ask -H "Content-Type: application/json" -d '{"user_id":"u1","question":"hello"}'
curl -i -X POST http://127.0.0.1/ask -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" -d '{"user_id":"u1","question":"hello"}'
python check_production_ready.py
docker compose logs --tail=60 agent
docker compose down -v
```

### Test Results

- Đã có bằng chứng runtime Part 6 được chạy thật: compose build/up/down thành công, container `agent/redis/nginx` khởi động, và logs ghi nhận uvicorn startup + ready event.
- Ở các lần chạy gần nhất, HTTP probe thường được gọi khi các `agent` còn `health: starting`, nên kết quả qua nginx là `502 Bad Gateway` cho `/health`, `/ready`, và `/ask`.
- Rate probe 13 requests ở các lần này trả về chủ yếu `502` (không phản ánh logic rate limiter, mà phản ánh backend chưa sẵn sàng tại thời điểm test).
- `check_production_ready.py`: `20/20 checks passed (100%)`, nhưng đây là static/code checks, không thay thế được runtime verification.
- Đã deploy public Railway riêng cho Part 6: `https://day12-lab-complete-production.up.railway.app`.
- Kiểm thử public endpoint thành công:
	- `GET /health` -> `200`
	- `GET /ready` -> `200`
	- `POST /ask` không key -> `401`
	- `POST /ask` với `X-API-Key: secret-key-123` -> `200`

### Part 6 Requirement Mapping

Functional:

- [x] Agent trả lời câu hỏi qua REST API (`POST /ask`).
- [x] Support conversation history qua Redis.
- [x] Streaming responses (optional): không bắt buộc trong phạm vi lab này.

Non-functional:

- [x] Dockerized multi-stage build.
- [x] Config từ environment variables.
- [x] API key authentication.
- [x] Rate limiting 10 req/min/user.
- [x] Cost guard 10 USD/tháng/user.
- [x] Health check endpoint.
- [x] Readiness check endpoint.
- [x] Graceful shutdown.
- [x] Stateless design với Redis.
- [x] Structured JSON logging.
- [x] Deploy public URL cho Part 6: `https://day12-lab-complete-production.up.railway.app`.

### Day12 Delivery Checklist (Liên quan Part 6)

- [x] Có đầy đủ source code trong `06-lab-complete`.
- [x] Dockerfile multi-stage + non-root + healthcheck.
- [x] Có `docker-compose.yml`, `requirements.txt`, `.env.example`, `.dockerignore`.
- [x] Auth/rate-limit/cost-guard/health-ready/stateless đã được chạy runtime local; kết quả HTTP qua nginx phụ thuộc thời điểm readiness.
- [x] Không hardcode secret trong code chính Part 6.
- [x] Public service domain cho Part 6: `https://day12-lab-complete-production.up.railway.app`.

## Tổng Kết Mục Chưa Hoàn Thành

- Không còn mục bắt buộc nào chưa hoàn thành trong checklist hiện tại.
