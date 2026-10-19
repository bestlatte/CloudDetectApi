# 驗收紀錄

日期：2026-10-20（Asia/Taipei）

## 已完成的本機驗收

- Git 已在 `main` 分支初始化；尚未設定 GitHub remote，也未建立 commit。
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

## GCP 唯讀前置檢查

- Project `clouddetctapi-demo` 存在且狀態為 `ACTIVE`，Billing 已啟用。
- 已存在 `cloudpulse-pg`：`asia-east1`、PostgreSQL 18、`RUNNABLE`、Enterprise Plus、N2 8 vCPU tier、Zonal、無一般備份、未開啟刪除保護。
- 這組規格符合 [Cloud SQL 30 天 Trial](https://docs.cloud.google.com/sql/docs/postgres/free-trial-instance) 的預設硬體特徵，但 CLI 不顯示剩餘 Trial 天數；部署前仍必須在 Console 的 instance Overview 確認 Trial banner 與剩餘日期。
- 未執行 API 啟用、Terraform plan/apply、IAM 修改、Secret 建立或寫值、資料庫／使用者建立、正式 Migration、Artifact push、Cloud Run 部署或 Scheduler 啟用。

## 尚待人工核准／外部資訊

1. 在 Console 確認 `cloudpulse-pg` 的 Trial 剩餘時間，以及既有 Database/User 是否符合命名與權限需求。
2. 提供 GitHub `owner/repository`，再設定 WIF 精確限制與 repository variables/environments。
3. 逐項審查 Terraform plan、IAM、Secret、Migration、部署與 Scheduler 啟用後，分別核准執行。
4. 正式部署後補上 Cloud Run URL、Revision、Job Execution、Scheduler 與關機後新結果的雲端驗收證據。

## 2026-10-20 擴充紀錄

- 核准模板由五個增加為八個；新增 GitHub REST API、Open-Meteo Taipei 與 PokéAPI Pikachu 三個 REAL 目標。
- 三者均使用固定 HTTPS URL、專用 Schema／業務驗證與 60 分鐘週期；管理 API 仍不接受任意網址。
