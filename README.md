# CloudPulse

CloudPulse 是一個以 React、FastAPI、PostgreSQL 與 GCP 組成的 API 健康監測平台。它同時監測 Frankfurter、GitHub、Open-Meteo、PokéAPI 四個真實公開來源與四個受控 Mock 端點，並刻意將 REAL／MOCK 統計分開，避免把示範故障誤認為正式服務異常。

目前儲存庫包含完整 P0 原始碼、測試、容器、Terraform 與 GitHub Actions。GCP Remote State、主要應用 Bootstrap 與 Cloud SQL Cutover 已完成；Cloud Run 目前仍使用公開測試 Image，尚未執行正式 Migration、部署 CloudPulse Image 或啟用排程。

## 功能

- HTTP 狀態、8 秒 Timeout、最大 256 KiB 回應與延遲門檻檢查
- JSON Content-Type、結構與業務欄位驗證
- Frankfurter `date/base/quote/rate` 驗證與獨立資料新鮮度警告
- 每個目標獨立週期：Mock 5 分鐘、Frankfurter 60 分鐘
- PostgreSQL 租約與 `(execution_id, monitor_id)` 唯一鍵處理重疊工作
- 公開唯讀 Dashboard、History 與 REAL／MOCK 篩選
- 單一管理員 Session、Argon2id、HttpOnly Cookie、CSRF 與 Origin 驗證
- 精確的八個 URL 模板；管理 API 不能建立任意探測網址

REAL 端點文件：[Frankfurter](https://frankfurter.dev/)、[GitHub rate limit](https://docs.github.com/en/rest/rate-limit/rate-limit)、[Open-Meteo forecast](https://open-meteo.com/en/docs)、[PokéAPI](https://pokeapi.co/docs/v2)。

## 本機啟動

需求：Docker Desktop 與 Docker Compose。

1. 建立本機環境檔：

   ```powershell
   Copy-Item .env.example .env
   ```

2. 建置後產生 Argon2id Hash，將輸出貼到 `.env` 的 `ADMIN_PASSWORD_HASH`：

   ```powershell
   docker compose build backend
   docker compose run --rm --no-deps backend python -m app.core.password_hash
   ```

3. 啟動 PostgreSQL、FastAPI 與 Vite：

   ```powershell
   docker compose up --build -d postgres backend frontend
   docker compose exec backend alembic upgrade head
   docker compose exec backend python -m app.db.seed
   ```

4. 開啟 `http://localhost:5174`。FastAPI Swagger 在開發環境為 `http://localhost:8001/docs`。預設改用 5174／8001／5433，避免占用其他常見本機專案；可在 `.env` 覆寫。

5. 執行一次到期監測：

   ```powershell
   docker compose --profile tools run --rm monitor
   ```

再次執行 Job 時，未到期目標會被略過。若要重做本機 Demo，可在資料庫中將 `next_check_at` 更新為目前時間；不要在正式環境任意改動排程欄位。

## 驗證命令

```powershell
docker compose run --rm --no-deps backend ruff check app tests
docker compose run --rm --no-deps backend python -m pytest
Set-Location frontend
npm run lint
npm run test
npm run build
```

正式 Image：

```powershell
docker build --target production -t cloudpulse:local .
docker run --rm -p 8080:8080 --env-file .env cloudpulse:local
```

## 後端分層

後端採用類似 Java 的 `Controller → Service → DAO/Repository → Database`：

- `backend/app/api/`：Controller，只處理 HTTP 輸入、輸出與 Cookie。
- `backend/app/services/`：Service，集中商業規則與使用案例。
- `backend/app/repositories/`：DAO/Repository，集中 SQLAlchemy 查詢與持久化。
- `backend/app/db/`：ORM Model、Session 與 PostgreSQL 連線。

FastAPI 透過 `backend/app/dependencies.py` 組裝 request-scoped Service；分層規則由 AST 測試守門。完整責任與 Monitor Job 的 `Claim → Probe → Save` 交易邊界請見 [架構文件](docs/architecture.md)。

## Terraform

Terraform 主設定位於 `infrastructure/`，已固定 GCP Project `clouddetctapi-demo`、Region `asia-east1` 與 GitHub Repository `bestlatte/CloudDetectApi`。另有 `infrastructure/bootstrap/` 專門建立受保護且具版本控制的 GCS Remote State Bucket。

部署分成三個核准關卡：Remote State Bootstrap、主要資源 Bootstrap、Cloud SQL／Secret Cutover。請依 `docs/deployment.md` 操作；不要直接提交 `.tfvars`、Backend 實際設定或 State，也不要跳過 Plan 審查執行 Apply。

## 主要 API

| Method | Route | 存取 |
|---|---|---|
| GET | `/health` | 公開 |
| GET | `/api/v1/overview` | 公開唯讀 |
| GET | `/api/v1/monitors` | 公開唯讀 |
| GET | `/api/v1/checks` | 公開唯讀 |
| GET | `/api/v1/monitors/{id}/checks` | 公開唯讀 |
| POST | `/api/v1/auth/login` | 允許 Origin、速率限制 |
| GET | `/api/v1/auth/session` | 公開；只回登入狀態 |
| POST | `/api/v1/auth/logout` | 管理 Session + CSRF |
| POST/PATCH/DELETE | `/api/v1/monitors...` | 管理 Session + CSRF |
| GET | `/demo/{healthy,server-error,slow,business-error}` | 受控 Demo |

查詢篩選：`/api/v1/checks?source_kind=REAL&monitor_id=<uuid>&limit=50`、`/api/v1/monitors?health_status=DOWN`。

## 雲端交付狀態

- GCP Project ID：`clouddetctapi-demo`
- Region：`asia-east1`
- Terraform State：`gs://clouddetctapi-demo-cloudpulse-tfstate/cloudpulse/production/default.tfstate`
- Cloud Run Bootstrap URL：`https://cloudpulse-web-nor3voukaq-de.a.run.app`（目前是 Hello Image，尚非 CloudPulse 網站）
- 已建立 Artifact Registry、Runtime／Deploy／Scheduler Service Account、限定 `bestlatte/CloudDetectApi` main 分支的 WIF、兩個 Secret、Web、Monitor Job、Initialize Job 與保持暫停的 Scheduler。
- Cloud Run Web、Monitor Job 與 Initialize Job 已掛載既有 Cloud SQL，並固定引用兩個 Secret Version 2；Terraform Cutover 後 Plan 為 `No changes`。
- Terraform 的 Scheduler 維持 `paused=true`。目前仍是 Hello Image，因此尚未完成 FastAPI 實際資料庫連線與 Migration 驗證。
- `infrastructure/example.tfvars` 只含安全的 Bootstrap 設定，不含 Secret 值。
- Migration、CloudPulse Image 部署、手動 Job 與 Scheduler 啟用仍須分別審查並核准。

詳見 [架構](docs/architecture.md)、[部署](docs/deployment.md)、[Demo 腳本](docs/demo-script.md)、[成本清理](docs/cost-and-cleanup.md) 與 [驗收紀錄](docs/acceptance-record.md)。

## 非本次範圍

Incident、管理員 Check Now、可用率趨勢圖及通知屬 P1/P2，目前未實作，也不會在介面或文件中宣稱可用。

