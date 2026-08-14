# Mazu 架構設計

## 1. 設計目標

1. **自然語言 → 指令流程 → 驗證 → 裝置執行 → 結果解碼 → 分析** 的完整 pipeline。
2. 支援 NVMe SSD、USB(BOT/UAS)、USB4(NVMe/SCSI 隧道與協議切換)。
3. 統一的指令抽象層:同一套流程可跑在不同 transport 上。
4. 之後可擴充廠商專屬指令。

## 2. 最重要的架構決策

### 2.1 Flow IR 是整個系統的「合約」

自然語言不直接驅動裝置。LLM 的唯一職責是把自然語言翻譯成
**Flow IR**(YAML/JSON 的宣告式流程描述),之後的驗證、執行、解碼、分析
全部只認 IR。這帶來三個好處:

- **安全**:所有要送進裝置的東西都經過同一個 validator,LLM 幻覺不會直接變成 ioctl。
- **可重現**:IR 可以存檔、diff、review、進 CI,除錯時可以完全重播。
- **可測試**:pipeline 的每一段都能獨立測試,不需要 LLM 也不需要實體裝置。

### 2.2 LogicalCommand:與 transport 無關的指令抽象

流程裡寫的不是「NVMe opcode 0x06」,而是邏輯操作,例如:

```yaml
- op: identify_controller
- op: read
  params: { lba: 0, blocks: 8 }
- op: get_log
  params: { log: smart }
```

每個 transport backend 負責把 LogicalCommand 映射成自己的線上格式:

| LogicalCommand | NVMe | SCSI |
|---|---|---|
| identify_controller | Identify (CNS=01h) | INQUIRY + VPD |
| read | Read (01h) | READ(10)/(16) |
| write | Write (02h) | WRITE(10)/(16) |
| flush | Flush (00h) | SYNCHRONIZE CACHE |
| get_log(smart) | Get Log Page (02h) | LOG SENSE / Informational Exceptions |

這正是 USB4「無縫協議切換」需求的解法:**翻譯發生在抽象層之下**,
流程本身完全不用改。對於抽象層蓋不到的指令,IR 另外提供
`raw_nvme` / `raw_scsi` escape hatch(明確標示、驗證更嚴格)。

### 2.3 協議翻譯層 (translate/)

USB4 裝置可能以 NVMe 或 SCSI 其中一種協議暴露。翻譯層參考
SNTL(SCSI-to-NVMe Translation)的概念,提供雙向映射:

- `LogicalCommand → NVMe wire` 與 `LogicalCommand → SCSI wire` 是主要路徑。
- `NVMe wire ↔ SCSI wire` 的直接翻譯(例如把使用者給的 raw NVMe 指令
  在 SCSI-only 隧道上執行)是次要路徑,只支援有明確對應的子集,
  翻譯不了就明確報錯,不猜。

## 3. 模組分層

```
src/mazu/
├── core/
│   ├── command.py    # LogicalCommand、CommandResult、狀態碼抽象
│   ├── flow.py       # Flow IR 資料模型 + YAML 載入
│   ├── validate.py   # schema 驗證 + 語意驗證(危險指令、參數範圍)
│   ├── executor.py   # 逐步執行、收集結果、跑 assertion
│   └── result.py     # 執行結果模型(可序列化,供分析/報告)
├── transport/
│   ├── base.py       # Transport ABC:open/close/execute(LogicalCommand)
│   ├── mock/         # 模擬 NVMe 裝置(記憶體 namespace、SMART 狀態機)
│   ├── nvme.py       # Phase 2:Linux NVMe passthru ioctl
│   ├── scsi.py       # Phase 2:Linux SG_IO
│   └── usb4.py       # Phase 3:隧道偵測 + 掛上 translate/
├── translate/
│   ├── base.py       # Translator 介面
│   └── sntl.py       # NVMe↔SCSI 映射表(骨架,逐指令補齊)
├── decode/           # bytes → dataclass(Identify、SMART、sense data…)
├── analyze/          # assertion 引擎、報告輸出
└── cli.py            # mazu run / mazu validate / mazu decode
```

依賴方向:`cli → core → transport → translate`,`decode`/`analyze`
只依賴 `core` 的資料模型。**transport 永遠不 import 上層。**

## 4. 實作順序

### Phase 1(現在):把 pipeline 打通 — mock first
- Flow IR + validator + executor + mock NVMe 裝置 + 基本 decoder + CLI。
- 產出:不需要任何硬體,`mazu run` 就能跑完整條 pipeline,測試全綠。

### Phase 2:接真實裝置(Linux)
- `NvmeTransport`(`NVME_IOCTL_ADMIN_CMD`/`IO_CMD`)、`ScsiTransport`(SG_IO)。
- 裝置列舉與識別(sysfs),安全機制:唯讀模式預設開啟、寫入指令需明確允許。
- USB BOT/UAS 裝置此時「免費」獲得支援 — 它們就是 SCSI transport。

### Phase 3:USB4 與協議翻譯
- 偵測 USB4 隧道下裝置實際暴露的協議,補齊 sntl.py 的映射子集。

### Phase 4:NL frontend 與廠商指令
- NL → Flow IR(此時 IR 已穩定,LLM prompt 以 IR schema + 範例為主)。
- 廠商專屬指令以 plugin 形式註冊(自帶 opcode、驗證規則、decoder)。

## 5. 現在刻意「不」做的事

- **不先接實體硬體**:pipeline 未成形前接硬體,除錯成本加倍。
- **不先做 NL/LLM 整合**:IR 還在變動時做 NL 端是白工。
- **不做完整 SNTL 覆蓋**:只做映射表骨架與介面,逐需求補齊。
- **不做廠商指令**:等抽象層與 plugin 介面穩定。
- **不做 GUI / Web dashboard / 分散式執行 / Windows 支援**。
- **不做效能測試(fio 類)**:Mazu 定位是功能驗證與除錯,不是 benchmark。
