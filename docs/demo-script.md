# 4–6 分鐘 Demo 腳本

## 1. 用途與真實目標

開啟 Dashboard，先選 REAL。說明 CloudPulse 監測 API 的 HTTP、延遲及 JSON 正確性，不提供交易或氣象決策建議。展示 Frankfurter、GitHub、Open-Meteo、PokéAPI 的最後檢查、回應時間與 60 分鐘週期；Frankfurter 另顯示資料日期。

## 2. 可重現異常

切換 MOCK，展示：

- Healthy：UP；
- Server Error：DOWN / `HTTP_STATUS_MISMATCH`；
- Slow：DEGRADED / `SLOW_RESPONSE`；
- Business Error：HTTP 200，但 DOWN / `BUSINESS_RULE_MISMATCH`。

指出畫面上的「預期模擬情境」，並說明它們沒有被計入真實 API 異常數。

## 3. 實際資料鏈

開啟 History，再展示 Cloud Run Job Execution 與 PostgreSQL `check_results`。說明資料路徑為 Scheduler → Job → HTTP Request → PostgreSQL → FastAPI → React，而不是前端寫死常數。

## 4. DevOps

展示 Terraform plan、最小權限 Service Account、GitHub PR CI，以及 main CD 對 Web/Job 部署同一 Commit SHA。正式 Demo 前準備一個只改版本字樣的 PR，避免臨場變更業務邏輯。

## 5. 收尾

說明固定 Allowlist、Secret Manager、OIDC、Cloud SQL 成本與 P1 項目。展示結束後依清理文件暫停 Scheduler。

