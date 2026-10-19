# 成本與清理

## 成本邊界

- Cloud SQL Trial 需在 Console 確認，不能假定新專案必定符合資格。
- Trial 到期、跨區傳輸、公網傳輸或最終備份可能產生費用；Trial 不提供一般備份與 SLA。
- Cloud Run min instances 為 0、max instances 為 1；Job 每五分鐘啟動，但四個 REAL 公開 API 每 60 分鐘才到期。
- Scheduler、Artifact Registry 儲存與 Cloud Logging 仍可能依實際使用量計費。
- Budget Alert 只發通知，不是硬上限。

## Demo 後優先停用

```powershell
gcloud scheduler jobs pause cloudpulse-every-five-minutes --location asia-east1 --project clouddetctapi-demo
```

確認停止新 Job Execution，再決定是否保留 Web 與資料庫。不要直接刪除尚未備份或仍需展示的資料。

## 完整清理核對

1. 匯出需要保留的資料或截圖；Trial 本身沒有一般備份。
2. 暫停 Scheduler，確認沒有執行中的 Job。
3. 記錄目前 Terraform State 位置與資源清單。
4. 經核准後執行 `terraform plan -destroy`，先審查再 `terraform destroy`。
5. 手動建立、未由 Terraform 管理的 Cloud SQL Trial 需另在 Console 刪除。
6. 刪除 Final Backup 前確認其保留費用；若不需要，建立刪除流程時不要勾選 Final Backup。
7. 檢查 Artifact Registry、Secret Versions、Cloud Logging 與 Billing 報表是否仍有殘留資源。

任何 destroy 或資料庫刪除都必須再次取得使用者核准。
