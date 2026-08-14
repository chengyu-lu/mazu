# CLAUDE.md

Mazu — AI 輔助的儲存驗證與除錯框架,給 SSD / 控制器韌體工程師用。
目標 pipeline:自然語言 → Flow IR → 驗證 → 裝置執行 → 結果解碼 → 分析。
完整設計請先讀 `docs/architecture.md`。

## 常用指令

```bash
pip install -e ".[dev]"                          # 安裝(開發模式)
pytest                                           # 跑全部測試(必須全綠才能 commit)
mazu validate examples/flows/identify_and_smart.yaml   # 只驗證流程
mazu run examples/flows/identify_and_smart.yaml        # 在 mock 裝置上執行
mazu run <flow.yaml> --json                      # JSON 報告輸出
```

## 架構鐵則(違反等於破壞設計)

1. **Flow IR 是系統合約。** 自然語言/LLM 永遠不直接產生裝置指令;LLM 只輸出
   Flow IR(YAML),之後所有東西只認 IR。任何要送進裝置的指令都必須通過
   `core/validate.py`。
2. **依賴方向:`cli → core → transport → translate`。**
   `decode/` 與 `analyze/` 只依賴 `core` 的資料模型。
   **transport 永遠不 import 上層**;core 永遠不 import 任何具體 transport
   (`core/executor.py` 只認 `transport/base.py` 的 `Transport` ABC)。
3. **流程只寫 LogicalCommand**(`identify_controller`、`read`、`get_log`…),
   不寫 NVMe opcode 或 SCSI CDB。協議差異(含 USB4 的 NVMe↔SCSI 切換)
   由 transport backend 與 `translate/` 處理,流程檔不因 transport 而異。
4. **翻譯不猜。** `translate/`(SNTL 子集)只翻有明確對應的指令,
   翻不了就丟 `TranslationUnsupported`;transport 對不支援的指令回
   `Status.UNSUPPORTED`,絕不默默替換。
5. **安全預設。** 破壞性指令(write、raw_*)必須 flow 層級明確
   `allow_destructive: true` 才能通過驗證。新增指令時若會改變裝置狀態,
   要加進 `core/command.py` 的 `DESTRUCTIVE_OPS`。
6. **Mock 與真實裝置行為一致。** `transport/mock/device.py` 產出的 payload
   必須符合 NVMe spec 的欄位 offset,decoder 對 mock 與真實裝置不做任何區分。

## 目錄導覽

```
src/mazu/
├── core/       # command.py(LogicalCommand/Op/Status)、flow.py(IR 解析)、
│               # validate.py(語意驗證)、executor.py、result.py
├── transport/  # base.py(Transport ABC)、mock/(可用)、
│               # nvme.py / scsi.py / usb4.py(Phase 2/3 stub,勿刪介面說明)
├── translate/  # base.py(Translator ABC)、sntl.py(NVMe↔SCSI 映射表骨架)
├── decode/     # bytes → dict;以邏輯 op 為 key,不以 transport 為 key
├── analyze/    # report.py(text/JSON 報告)
└── cli.py      # mazu validate / run
```

## 開發階段(照順序,不跳段)

- **Phase 1(完成)**:mock-first pipeline 全通。
- **Phase 2(下一步)**:`NvmeTransport`(Linux `NVME_IOCTL_ADMIN_CMD`/`IO_CMD`)、
  `ScsiTransport`(SG_IO)。做完 SCSI,USB BOT/UAS 自動支援。
  需加:裝置列舉(sysfs)、預設唯讀模式。
- **Phase 3**:USB4 隧道偵測、補齊 `sntl.py` 的 wire-level 映射。
- **Phase 4**:NL → Flow IR(LLM frontend)、廠商指令 plugin 機制。

**現在不要做**:NL/LLM 整合、完整 SNTL 覆蓋、廠商指令、GUI/Web、
分散式執行、Windows 支援、效能測試(Mazu 是功能驗證工具,不是 benchmark)。

## 寫程式的慣例

- Python ≥ 3.10,標準 dataclass,不引入重量級框架;目前唯一 runtime 依賴是 PyYAML。
- 新的邏輯指令:改 `core/command.py`(Op + 需要時 DESTRUCTIVE_OPS)→
  `core/validate.py`(參數驗證)→ 各 transport 的 dispatch → 需要時加 decoder
  → 補測試與範例 flow。缺一不可。
- 新的 decoder 回傳巢狀 dict,欄位名稱用 snake_case,讓 assertion 能以
  dot-path(如 `smart.media_errors`)存取。
- 測試放 `tests/`,不需要硬體就能跑;範例 flow 放 `examples/flows/`,
  必須在 mock transport 上 PASS。
- Commit 前:`pytest` 全綠 + 兩個 example flow `mazu run` 都 PASS。
