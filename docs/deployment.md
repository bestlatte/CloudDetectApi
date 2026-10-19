# GCP 部署手冊

本文件是操作清單。Remote State、主要資源 Bootstrap 與 Cloud SQL／Secret Cutover 已於 2026-10-20 完成；Migration、CloudPulse Image 部署、手動 Job 與 Scheduler 啟用尚未執行。每個標為「核准」的後續步驟仍需先提供變更內容與成本風險，再由使用者授權。

## 1. 前置檢查

1. 確認目前 gcloud 帳號、Project ID `clouddetctapi-demo`、Billing Account 與 `asia-east1` 配額。
2. 在 Cloud SQL Console 確認新專案能否選擇 PostgreSQL 30 天 Trial；不要用 Terraform 的一般付費 Instance 冒充試用。
3. 確認 Terraform 版本至少 1.7；正式 State 使用有版本控制及禁止公開存取的 GCS Bucket，不提交 Git。
4. GitHub Repository 已固定為 `bestlatte/CloudDetectApi`，WIF 同時限制此 Repository 與 `refs/heads/main`。

## 2. 建立遠端 State（第一次且需核准）

遠端 State Bucket 使用獨立的 `infrastructure/bootstrap` 設定，避免主要資源與 Backend 互相依賴。Bucket 啟用物件版本控制、Uniform bucket-level access、Public Access Prevention 及 `prevent_destroy`。

```powershell
Set-Location infrastructure/bootstrap
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan -out=state-bootstrap.tfplan
```

審查 Plan 後，經核准才執行：

```powershell
terraform apply state-bootstrap.tfplan
```

Bucket 建立後，將 bootstrap 自己的本機 State 遷移到該 Bucket：

```powershell
Copy-Item backend.tf.example backend.tf
Copy-Item backend.hcl.example backend.hcl
terraform init -migrate-state -backend-config=backend.hcl
```

如果預設 Bucket 名稱已被其他專案使用，須同時修改 `terraform.tfvars`、`backend.hcl` 與主要設定的 `backend.hcl`。不要刪除或提交產生的 State、Plan 與 Backend 實際設定檔。

## 3. 基礎設施 Bootstrap Plan

```powershell
Set-Location infrastructure
Copy-Item backend.hcl.example backend.hcl
Copy-Item bootstrap.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform fmt -check -recursive
terraform validate
terraform plan -out=bootstrap.tfplan
```

初次 plan 應保持：

- `scheduler_paused=true`
- `attach_runtime_secrets=false`
- `cloud_sql_connection_name=""`
- `github_repository="bestlatte/CloudDetectApi"`
- Bootstrap Image 使用公開 Hello Image 或已先推送的 CloudPulse Image

審查 plan 後才可申請 `terraform apply` 核准。

## 4. Cloud SQL 與 Secret（核准後）

1. 由 Console 建立 Trial PostgreSQL、Database 與 Application User，記錄 Connection Name。
2. Database 不開放全網路 5432；Cloud Run 使用 Cloud SQL volume/socket。
3. 產生正式管理員 Argon2id Hash。
4. 將完整 SQLAlchemy URL 與密碼 Hash 分別新增至：
   - `cloudpulse-database-url`
   - `cloudpulse-admin-password-hash`
5. Secret 值只能從受保護的終端或 Console 輸入，不出現在指令紀錄、Terraform State 或 Git。
6. 記錄兩個 Secret 的實際數字版本，正式環境不要使用 `latest`。

PostgreSQL socket URL 格式示例：

```text
postgresql+psycopg://USER:PASSWORD@/DATABASE?host=/cloudsql/PROJECT:REGION:INSTANCE
```

## 5. 第二次 IaC 更新（核准後）

以 `production.tfvars.example` 重新建立 `terraform.tfvars`，設定 `cloud_sql_connection_name`、第一次 apply 輸出的 `web_url`、兩個 Secret 的數字版本及 `attach_runtime_secrets=true`，仍保持 Scheduler 暫停。Container Image 由 CD 使用 Commit SHA 更新，不使用 `latest` Tag。再次 plan/apply 後：

1. 手動測試 `/health`；
2. 執行受保護的 `Initialize database` workflow，或經核准執行 `cloudpulse-initialize` Job；
3. 執行一次 `cloudpulse-monitor` 並確認八筆結果；
4. 查看 Web/API/Dashboard 與 Cloud Logging；
5. 最後才 plan/apply `scheduler_paused=false`。

## 6. GitHub Variables 與 Environments

Repository Variables：

- `GCP_PROJECT_ID=clouddetctapi-demo`
- `GCP_REGION=asia-east1`
- `GCP_WIF_PROVIDER=<terraform output>`
- `GCP_DEPLOY_SERVICE_ACCOUNT=<terraform output>`

建立需要審核者的 `production` 與 `production-database` Environment。CI 不使用 GCP 權限；Deploy 只接受 main 分支 OIDC。Migration 必須由手動 workflow 指定一個已通過 CI 的 Commit SHA。

## 7. 回滾

1. 找到前一個通過 CI 的 SHA Image。
2. 更新 Web、Monitor Job 和 Initialize Job 使用同一 SHA。
3. 驗證 `/health`、首頁與一輪手動 Job。
4. Schema Migration 若不向後相容，使用經審查的 Alembic downgrade；不可由 Web 容器自動執行。

