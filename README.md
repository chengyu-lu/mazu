# Mazu 媽祖

**AI 輔助的儲存驗證與除錯框架**,為 SSD / 控制器韌體工程師打造。

> 目標流程:**自然語言 → 指令流程 (Flow IR) → 驗證 → 裝置執行 → 結果解碼 → 分析**

Mazu 提供一個統一的指令抽象層,讓同一套驗證流程可以透過不同傳輸方式
(NVMe、SCSI、USB BOT/UAS、USB4)操作同一個邏輯裝置,並在 USB4 情境下
支援 NVMe ↔ SCSI 的協議轉換。

## 核心概念

```
 自然語言 (之後實作)
     │  NL frontend 產生 Flow IR — LLM 只負責「翻譯成 IR」,不直接碰裝置
     ▼
 Flow DSL v2 (YAML)           ← 協議明確、目標明確、指令明確、參數型別化
     │                           (規格:docs/flow-dsl.md)
     │
     ▼
 Validator                    ← schema + 語意驗證(參數範圍、相依性、危險指令)
     │
     ▼
 Flow 引擎 ─ LogicalCommand ─→ Executor 介面(唯一通往裝置的門)
     │                            ├─ MockExecutor(模擬 NVMe 裝置,現已可用)
     │                            ├─ NvmeExecutor(Linux ioctl passthru,規劃中)
     │                            ├─ ScsiExecutor(SG_IO,規劃中)
     │                            └─ Usb4Executor(隧道 + 協議翻譯,規劃中)
     │                                  └─ translate/:NVMe ↔ SCSI 翻譯層 (SNTL)
     ▼
 Decoder                      ← raw bytes → 結構化資料(Identify、SMART、sense…)
     │
     ▼
 Analyzer / Report            ← assertion、比對、報告輸出
```

詳細設計請見 [docs/architecture.md](docs/architecture.md)。

## 快速開始

```bash
pip install -e ".[dev]"

# 用模擬裝置跑範例流程(NVMe 與 SCSI)
mazu run examples/flows/nvme_health.yaml
mazu run examples/flows/scsi_capacity_check.yaml --trace

# 試運行:驗證 + 依賴解析 + 指令計畫,不碰裝置
mazu run examples/flows/nvme_health.yaml --dry-run

# 只做驗證,不執行
mazu validate examples/flows/nvme_health.yaml

# 跑測試
pytest
```

## 目前狀態(Phase 1:mock-first)

| 元件 | 狀態 |
|---|---|
| Flow DSL v2(typed params、深度驗證)| ✅ 可用 |
| 指令註冊表(NVMe + SCSI,spec 出處)| ✅ 可用 |
| Mock NVMe + SCSI 裝置 / MockExecutor | ✅ 可用 |
| 確定性引擎(depends_on、dry-run、trace)| ✅ 可用 |
| Decoder(Identify/SMART/INQUIRY/CAPACITY)| ✅ 基本可用 |
| Linux 真實 NVMe/SCSI executor | 🔜 Phase 2 |
| USB4 隧道與 NVMe↔SCSI 翻譯 | 🔜 Phase 3(介面已預留) |
| 自然語言 → Flow IR | 🔜 IR 穩定後實作 |
| 廠商專屬指令 | ⏸ 之後透過 plugin 機制支援 |

## 授權

MIT
