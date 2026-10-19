# 驗收紀錄

日期：2026-10-20（Asia/Taipei）

## 已完成的本機驗收

- Git 已在 `main` 分支初始化，Remote 已設定為 `bestlatte/CloudDetectApi`。
- Alembic `0001_initial` 已在獨立 PostgreSQL 測試資料庫成功升級。
- Seed 重跑具冪等性，正式本機資料庫保存五個固定目標。
- 一次性 Monitor Job 實際寫入五筆結果：
  - Frankfurter USD/TWD：`UP`；
  - Mock Healthy：`UP`；
  - Mock Server Error：`DOWN / HTTP_STATUS_MISMATCH`；
  - Mock Slow：`DEGRADED / SLOW_RESPONSE`；
  - Mock Business Error：`DOWN / BUSINESS_RULE_MISMATCH`。
- 後端 Ruff 通過；42 個 Pytest 案例分別在 SQLite 與 PostgreSQL 通過。
- 前端 ESLint、TypeScript、2 個 Vitest 案例及 Vite production build 通過，`npm audit` 為 0 個已知漏洞。
- 正式多階段 Image smoke test 通過：`/health`、`/api/v1/overview`、`/`、靜態 JS、SPA `/history` 均為 200，production `/docs` 為 404。
- 以窄螢幕瀏覽器實際檢查 Dashboard、History 與未登入 Monitors 頁；主控台沒有 error 或 warning。
- Terraform `fmt -check`、`init -backend=false`、`validate` 通過；GitHub Actions workflow 通過 actionlint。

## GCP 前置檢查

- Project `clouddetctapi-demo` 存在且狀態為 `ACTIVE`，Billing 已啟用。
- 已存在 `cloudpulse-pg`：`asia-east1`、PostgreSQL 18、`RUNNABLE`、Enterprise Plus、N2 8 vCPU tier、Zonal、無一般備份、未開啟刪除保護。
- 這組規格符合 [Cloud SQL 30 天 Trial](https://docs.cloud.google.com/sql/docs/postgres/free-trial-instance) 的預設硬體特徵，但 CLI 不顯示剩餘 Trial 天數；部署前仍必須在 Console 的 instance Overview 確認 Trial banner 與剩餘日期。
- 前置檢查完成後，已依使用者明確核准執行 Remote State Bootstrap、主要資源 Bootstrap 與後續 Cloud SQL Cutover；結果記錄於下方。正式 Migration、CloudPulse Artifact push 與 Scheduler 啟用均未執行。

## 尚待人工核准／外部資訊

1. 在 Console 確認 `cloudpulse-pg` 的 Trial 剩餘時間，以及既有 Database/User 是否符合命名與權限需求。
2. 在 GitHub Repository 設定 Terraform 輸出的 WIF／Project／Region／Deploy Service Account Variables，以及受保護的 Environments。
3. 逐項審查 Migration、CloudPulse Image 部署、手動 Job 與 Scheduler 啟用後，分別核准執行。
4. 正式部署後補上 CloudPulse Revision、Job Execution、Scheduler 與關機後新結果的雲端驗收證據。

## 2026-10-20 擴充紀錄

- 核准模板由五個增加為八個；新增 GitHub REST API、Open-Meteo Taipei 與 PokéAPI Pikachu 三個 REAL 目標。
- 三者均使用固定 HTTPS URL、專用 Schema／業務驗證與 60 分鐘週期；管理 API 仍不接受任意網址。
- Terraform 已加入獨立 Remote State Bootstrap：GCS Bucket 啟用版本控制、Uniform bucket-level access、Public Access Prevention 與 `prevent_destroy`。
- 主要 Terraform Backend 改為部分設定的 GCS Backend；Repository 條件固定為 `bestlatte/CloudDetectApi`，另提供 Bootstrap／Production 分階段變數範本。
- Cloud Run Secret 引用支援釘選數字版本，並加入 Runtime Secret 與 Scheduler 啟用前置條件，避免資料庫尚未連接時誤啟動正式排程。
- Terraform 1.13.4 `fmt -check`、主要設定 `validate`、State Bootstrap `validate` 均通過。
- 經使用者明確核准，已 Apply State Bootstrap Plan `E8850C66D7794A8A4F9EE1F6B16BCBFC9C69955EF28B0578DFAF72F068F99D66`：`2 added, 0 changed, 0 destroyed`。內容僅為啟用 `storage.googleapis.com` 及建立 `clouddetctapi-demo-cloudpulse-tfstate`。
- Bootstrap State 已遷移至 `gs://clouddetctapi-demo-cloudpulse-tfstate/cloudpulse/state-bootstrap/default.tfstate`；Bucket 為 `ASIA-EAST1`、版本控制啟用、Uniform bucket-level access 啟用、Public Access Prevention enforced，並有 7 天 Soft Delete。
- Remote State 重新整理後包含 `google_project_service.storage` 與 `google_storage_bucket.terraform_state`，後續 Plan 顯示 `No changes`。
- 主要應用 Bootstrap Plan 已產生，SHA-256 為 `1D7454119037E3CEBDAEFCA25B433F9F7AD0F33107D5BF8A821222CA5A7B5A61`：`30 to add, 0 to change, 0 to destroy`。內容包括 9 個 API、3 個 Service Account、WIF、IAM、Artifact Registry、2 個空 Secret 容器、Cloud Run Web、2 個 Job，以及保持暫停的 Scheduler；Cloud SQL 與 Secret 值尚未掛載。
- 經使用者明確核准，已 Apply 上述主要應用 Bootstrap Plan：`30 added, 0 changed, 0 destroyed`。
- Artifact Registry：`asia-east1-docker.pkg.dev/clouddetctapi-demo/cloudpulse`；Deploy Service Account：`cloudpulse-deploy@clouddetctapi-demo.iam.gserviceaccount.com`。
- WIF Provider：`projects/847641313599/locations/global/workloadIdentityPools/cloudpulse-github/providers/cloudpulse-repository`，條件限制 `bestlatte/CloudDetectApi` 與 `refs/heads/main`。
- Cloud Run Web Ready Revision：`cloudpulse-web-00001-vsm`；`https://cloudpulse-web-nor3voukaq-de.a.run.app` 回傳 HTTP 200，但目前仍為公開 Hello Image，不視為 CloudPulse 正式部署。
- `cloudpulse-monitor`、`cloudpulse-initialize` Jobs 已建立；`cloudpulse-every-five-minutes` Scheduler 保持 `PAUSED`。
- 主要資源 Bootstrap 階段只建立 `cloudpulse-database-url` 與 `cloudpulse-admin-password-hash` 空 Secret 容器，當時尚未新增 Secret Version 或掛載既有 Cloud SQL。
- Cloud Run API 會回填未設定的 Service-level scaling 預設值；Terraform 僅忽略該層 API 預設值，Revision-level `max_instance_count=1` 仍由 Terraform 管理。修正後 `fmt -check`、`validate` 與遠端 Plan 均通過，結果為 `No changes`。
- 兩個 Secret 的 Version 2 已確認為 `ENABLED`；資料庫 URL 符合 Psycopg Unix Socket 格式，管理員密碼為 Argon2id Hash。檢查過程沒有顯示 Secret 內容。
- 經使用者明確核准，已 Apply Cloud SQL Cutover Plan `1B763CD17194EC14A76A22A07C11BD74551484EECC56446F15C8F722725DFFA4`：`0 added, 3 changed, 0 destroyed`。
- Cloud Run Web、Monitor Job 與 Initialize Job 均固定引用 Secret Version 2，並掛載 `/cloudsql` 與 `clouddetctapi-demo:asia-east1:cloudpulse-pg`。
- 新 Web Revision `cloudpulse-web-00002-f8t` 已 Ready，公開 URL 回傳 HTTP 200；Scheduler 仍為 `PAUSED`，沒有執行 Initialize／Monitor Job。
- Cutover 後 Terraform Plan 顯示 `No changes`。Web 仍使用 Hello Image，因此此階段只驗證 Cloud Run 平台設定，尚未驗證 FastAPI 實際資料庫登入、Migration 或查詢。
