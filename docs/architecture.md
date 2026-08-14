# Mazu 架構設計

## 1. 設計目標

1. **自然語言 → 指令流程 → 驗證 → 裝置執行 → 結果解碼 → 分析** 的完整 pipeline。
2. 支援 NVMe SSD、USB(BOT/UAS)、USB4(NVMe/SCSI 隧道與協議切換)。
3. 統一的指令抽象層:同一套流程可跑在不同 transport 上。
4. 之後可擴充廠商專屬指令。

本文件與 `CLAUDE.md` 的十大原則互為表裡:CLAUDE.md 規定「不可協商的紀律」,
本文件說明「架構如何讓那些紀律成為結構性事實,而不是靠自律」。

## 2. 架構不變量(Architectural Invariants)

以下七條是本架構的硬性約束。任何 PR 若違反其中一條,即是架構層級的錯誤。

### I1. 指令定義必須是結構化的

指令是型別化的資料物件(`LogicalCommand`:封閉的 `Op` 枚舉 + 具名參數),
不是字串、不是自由格式文字。任何一層之間都不傳遞「描述指令的文字」;
LLM 的自然語言輸出在進入系統的那一刻就被結構化為 IR,之後不再有文字解析。

### I2. 指令必須可序列化

`LogicalCommand`、Flow、執行結果(`FlowResult`)都必須能無損地序列化
(YAML/JSON)與反序列化。這是三件事的基礎:
流程可存檔、可 diff、可 review(IR 即序列化格式);
執行可重播(結果連同 raw payload 保留);
分析可離線進行(結果檔案就是完整證據,不依賴活著的裝置)。
不可序列化的狀態(open file descriptor、socket)只允許存在於
executor 介面之下,絕不進入資料模型。

### I3. 指令在執行前必須先經過驗證

驗證是強制閘門,不是建議步驟。`run_flow` 內建驗證,沒有繞過的 API;
validator 做三層檢查 — 結構(schema、已知 op)、語意(必要參數、
範圍上限、已知 log page)、政策(v1:破壞性指令一律拒絕,見 I7)。
LLM 產生的 IR 與人手寫的 IR 走完全相同的驗證路徑。

### I4. 執行必須抽象在 Executor 介面之後

裝置執行被封在一個窄介面之後(`executor/base.py` 的 `Executor` ABC:
`open / close / execute(LogicalCommand) → CommandResult`)。
core 只認這個介面,不 import 任何具體實作;流程引擎(`core/engine.py`)
是確定性的:同一份 IR + 同一個裝置狀態 ⇒ 同一串指令序列,
無隨機性、無隱式重試、無 LLM 呼叫。重試/逾時若有需要,宣告在 IR 裡。

### I5. 硬體執行必須可被 Mock Executor 取代

Mock 不是測試用的次等公民,而是第一個正式的 executor 實作。
Mock 產出的 payload 必須符合協議規範的欄位 offset
(Identify、SMART log 等以 spec 排版),因此 decode 層對 mock 與
真實硬體**零區分**。任何在 mock 上通過的流程,換上真實 executor
時流程檔一個字都不用改 — 這是「同一套流程跑不同 transport」的驗收標準。

### I6. 指令的編碼與解碼必須是可測試的

encoder(`LogicalCommand → wire bytes`)與 decoder(`bytes → 結構化資料`)
必須是純函式:輸入 bytes/物件,輸出物件/bytes,不碰裝置、不碰全域狀態。
每一個 codec 都必須有以已知位元組向量(依 spec 排版)做的 roundtrip 測試;
沒有測試的 codec 視同不存在。所有 wire 常數(offset、opcode、page ID)
必須註明 spec 出處,查不到出處的欄位一律不實作(回 UNSUPPORTED,不猜)。

### I7. 破壞性指令在 v1 中不在範圍內

v1 的已支援指令集是**唯讀的**:identify、read、get_log 等
不改變裝置狀態的操作。write、raw_nvme、raw_scsi 及未來的
format/sanitize/fw download 屬於 `DESTRUCTIVE_OPS`:
資料模型中保留其定義(讓抽象層形狀完整),但 v1 的 validator
對它們一律拒絕,不論任何旗標。
v2 引入破壞性指令時,採雙重閘門:flow 層級明確 `allow_destructive`
**加上** executor 層級的唯讀預設解除,缺一不可;
且 AI agent 不可代替使用者設定任何一道閘門。

## 3. 全系統資料流

```
 自然語言(之後實作)
     │  LLM 只輸出 Flow IR — 不碰裝置、不選 opcode、不產生 wire bytes
     ▼
 Flow IR(YAML/JSON)          ← I1/I2:結構化、可序列化的系統合約
     │
     ▼
 Validator                    ← I3:強制閘門(結構/語意/政策)
     │
     ▼
 Flow 引擎(確定性)           ← I4:core/engine.py
     │  LogicalCommand
     ▼
 Executor 介面(Executor ABC)  ← I4/I5:唯一通往裝置的門(executor/base.py)
     ├─ MockExecutor(✅ 現行,spec-shaped payload)
     ├─ NvmeExecutor(Phase 2:Linux ioctl passthru)
     ├─ ScsiExecutor(Phase 2:SG_IO;USB BOT/UAS 隨之支援)
     └─ Usb4Executor(Phase 3:隧道偵測 + translate/)
     │                              └─ SNTL 子集:只翻有明確對應的指令,
     │                                 翻不了回 UNSUPPORTED,不猜
     ▼
 Decoder                      ← I6:純函式,bytes → 結構化資料,mock/實機零區分
     │
     ▼
 Analyzer / Report            ← 結論必附證據(指令、狀態、raw bytes、期望/實際值)
```

依賴方向:`cli → core → executor → translate`;
`decode`/`analyze` 只依賴 `core` 的資料模型。executor 實作永不 import 上層。

## 4. 為什麼 Flow IR 是合約

- **安全**:所有要送進裝置的東西都經過同一個 validator,
  LLM 幻覺最多產生一份會被拒絕的 YAML,不會變成 ioctl。
- **可重現**:IR 可存檔、diff、review、進 CI;除錯時完全重播。
- **可測試**:pipeline 每一段都能獨立測試,不需要 LLM 也不需要硬體。
- **傳輸無關**:流程寫邏輯操作,協議差異(含 USB4 的 NVMe↔SCSI 切換)
  由 executor 與翻譯層處理,流程檔不因 transport 而異。

邏輯指令與各協議的對應(語意真相在 `translate/sntl.py` 的 `LOGICAL_MAPPING`):

| LogicalCommand | NVMe | SCSI |
|---|---|---|
| identify_controller | Identify (CNS=01h) | INQUIRY + VPD |
| identify_namespace | Identify (CNS=00h) | READ CAPACITY(16) |
| read | Read (01h) | READ(10)/(16) |
| get_log(smart) | Get Log Page (02h) | LOG SENSE / Informational Exceptions |
| flush | Flush (00h) | SYNCHRONIZE CACHE(10) |
| write(v2) | Write (02h) | WRITE(10)/(16) |

## 5. 實作順序

### Phase 1(現在)= v1:唯讀 pipeline 全通,mock first
- Flow IR + validator + 確定性 flow 引擎 + MockExecutor + decoder + CLI。
- v1 指令集唯讀(I7);破壞性指令保留定義但 validator 一律拒絕。
- 產出:不需要任何硬體,`mazu run` 跑完整條 pipeline,測試全綠。

### Phase 2:接真實裝置(Linux),仍為唯讀
- `NvmeExecutor`(`NVME_IOCTL_ADMIN_CMD`/`IO_CMD`)、`ScsiExecutor`(SG_IO)。
- 裝置列舉(sysfs)、`tests/hw/`(`@pytest.mark.hw`,預設排除)。
- USB BOT/UAS 裝置此時「免費」獲得支援 — 它們就是 SCSI executor。

### Phase 3:USB4 與協議翻譯
- 偵測 USB4 隧道下裝置實際暴露的協議,補齊 sntl.py 的 wire-level 映射子集。

### v2:破壞性指令(獨立里程碑,不綁 Phase)
- 解除 I7:引入 write 等破壞性操作,雙重閘門
  (flow 層 `allow_destructive` + executor 層唯讀預設解除)。

### Phase 4:NL frontend 與廠商指令
- NL → Flow IR(此時 IR 已穩定,LLM prompt 以 IR schema + 範例為主)。
- 廠商專屬指令以 plugin 形式註冊(自帶 opcode、驗證規則、decoder、測試)。

## 6. 現在刻意「不」做的事

- **不做破壞性指令**(I7,v1 唯讀;v2 才引入,帶雙重閘門)。
- **不先接實體硬體**:pipeline 未成形前接硬體,除錯成本加倍。
- **不先做 NL/LLM 整合**:IR 還在變動時做 NL 端是白工。
- **不做完整 SNTL 覆蓋**:只做映射表骨架與介面,逐需求補齊。
- **不做廠商指令**:等抽象層與 plugin 介面穩定。
- **不做 GUI / Web dashboard / 分散式執行 / Windows 支援**。
- **不做效能測試(fio 類)**:Mazu 定位是功能驗證與除錯,不是 benchmark。
