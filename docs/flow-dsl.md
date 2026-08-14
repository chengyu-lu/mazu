# Mazu Flow DSL v2 規格

適用範圍:NVMe 與 SCSI 指令序列。本文件是 DSL 的正式規格;
`core/flow.py`(解析)、`core/registry.py`(指令與參數型別)、
`core/validate.py`(驗證)必須與本文件一致。

## 設計要求(v2 的十項條件)

1. 協議必須明確 — 每個 target 宣告 `protocol: nvme | scsi`,不存在「猜協議」。
2. 目標裝置必須明確 — 指令只能下在具名 target 上,target 帶裝置位址。
3. 指令必須明確 — 指令名稱來自指令註冊表(registry),沒有註冊的指令
   直接驗證失敗;不允許縮寫或別名。
4. 參數必須型別化 — registry 為每個指令宣告參數型別
   (u8/u16/u32/u64/bool/enum)、範圍與必要性;未知參數是錯誤。
5. 每個步驟必須有唯一名稱 — 重名是驗證錯誤;名稱是依賴與追蹤的 key。
6. 支援步驟間依賴 — `depends_on`;依賴失敗的步驟被跳過(skipped),不執行。
7. 支援斷言 — 對解碼結果做宣告式檢查,並可引用依賴步驟的結果值。
8. 支援唯讀/破壞性分類 — 分類宣告在 registry(`effect`),不在 flow;
   v1 政策:破壞性指令一律拒絕(不變量 I7)。
9. 支援試運行(dry-run)— 驗證 + 依賴解析 + 產生執行計畫,不碰裝置。
10. 支援指令追蹤輸出(trace)— 每次執行產生逐指令的結構化 trace。

## 與 v1 的關鍵差異

v1 的步驟寫「邏輯操作」(transport 無關);v2 改為**協議明確**:
指令屬於某個協議的指令集(`nvme.identify_controller`、`scsi.inquiry`)。
「同一份流程跑不同傳輸」的語意隨之精確化 —
同協議指令可以走不同傳輸隧道(NVMe over PCIe / over USB4);
**跨協議**執行(在 SCSI-only 鏈路上跑 NVMe 指令)是 translate/ 的
明確且逐指令的翻譯,不再是隱式抽象。

## 文件結構

```yaml
version: 2                     # DSL 版本,必填;不支援的版本直接拒絕
name: nvme_health              # flow 名稱,必填
description: "..."             # 選填

targets:                       # 必填,至少一個
  - id: ssd0                   # 唯一 target 識別名
    protocol: nvme             # 必填:nvme | scsi
    executor: mock             # 必填:mock | nvme | scsi | usb4
    device: "mock://nvme/0"    # 必填:裝置位址(mock:// 或 /dev/...)

steps:                         # 必填,至少一個
  - name: id_ctrl              # 必填,全 flow 唯一,[A-Za-z0-9_-]+
    target: ssd0               # 必填,必須是已宣告的 target id
    command: identify_controller   # 必填,registry 中該協議的指令名
    params: {}                 # 依 registry 的型別宣告;未知參數 = 錯誤
    depends_on: []             # 選填,只能引用「較早宣告」的步驟名
    expect_status: success     # 選填,預設 success
    assert: []                 # 選填,見下
```

`command` 也接受帶協議前綴的寫法 `nvme.identify_controller`;
前綴必須與 target 的 protocol 一致,否則驗證錯誤。

## 指令註冊表(registry)

指令的唯一真相來源。每個指令宣告:協議、名稱、效果分類
(`read_only` | `destructive`)、參數規格(名稱、型別、必要性、
範圍/枚舉值)、spec 出處。v2 內建指令集:

| 指令 | 協議 | 效果 | 參數(型別) | Spec 出處 |
|---|---|---|---|---|
| identify_controller | nvme | read_only | — | NVMe Base 2.x, Identify CNS=01h |
| identify_namespace | nvme | read_only | nsid: u32 (≥1) | NVMe Base 2.x, Identify CNS=00h |
| get_log_page | nvme | read_only | lid: enum{error, smart, firmware_slot} | NVMe Base 2.x, Get Log Page (02h) |
| read | nvme | read_only | nsid: u32, slba: u64, nlb: u16 (1..65536) | NVM Cmd Set, Read (opcode 02h) |
| flush | nvme | read_only | nsid: u32 | NVM Cmd Set, Flush (opcode 00h) |
| write | nvme | **destructive** | nsid, slba, nlb, pattern: u8 | NVM Cmd Set, Write (opcode 01h) |
| inquiry | scsi | read_only | evpd: bool=false, page_code: u8=0 | SPC-4, INQUIRY (12h) |
| read_capacity_16 | scsi | read_only | — | SBC-3, READ CAPACITY(16) (9Eh/10h) |
| read_16 | scsi | read_only | lba: u64, transfer_length: u32 (1..65536) | SBC-3, READ(16) (88h) |
| write_16 | scsi | **destructive** | lba, transfer_length, pattern: u8 | SBC-3, WRITE(16) (8Ah) |

型別系統:`u8`/`u16`/`u32`/`u64`(整數 + 範圍檢查)、`bool`、
`enum`(具名值集合,YAML 中寫名稱不寫數字)。
參數規則:未知參數 = 錯誤;缺必要參數 = 錯誤;超出範圍 = 錯誤;
有預設值的參數可省略(預設值宣告於 registry,寫在文件裡)。

## 依賴(depends_on)

- 只能引用**較早宣告**的步驟(強制 DAG、禁止前向引用與自引用)。
- 執行順序 = 宣告順序(確定性;depends_on 不重排執行順序,只做閘門)。
- 依賴的步驟任何一個未 PASS(含被跳過),本步驟標記 `skipped`,
  不會發出任何指令;skipped 造成整個 flow FAIL。

## 斷言(assert)

```yaml
assert:
  - { path: smart.media_errors, op: eq, value: 0 }
  - path: length                      # 引用依賴步驟的結果值
    op: eq
    value_from: { step: read_cap, path: capacity.block_size }
```

- `path`:dot-path,查自己這一步的解碼結果。
- `op`:eq | ne | lt | le | gt | ge | exists。
- `value` 與 `value_from` 二擇一;`value_from.step` **必須**出現在
  本步驟的 `depends_on` 裡(資料依賴必須是宣告過的依賴)。

## 試運行(dry-run)

`mazu run flow.yaml --dry-run`:
執行完整驗證與依賴解析,產生執行計畫(planned trace):
每一步會下的協議、指令、型別化參數、效果分類。
**不建立 executor、不碰任何裝置**;步驟狀態為 `planned`。
dry-run 成功 ⇔ 此 flow 通過驗證且依賴圖可執行。

## 指令追蹤(trace)

每次執行(含 dry-run)產生逐指令 trace,包含於 JSON 報告
(`--json`)並可用 `--trace` 在文字報告中列印:

```json
{ "seq": 0, "step": "id_ctrl", "target": "ssd0", "protocol": "nvme",
  "command": "identify_controller", "params": {}, "effect": "read_only",
  "status": "success", "duration_us": 123 }
```

dry-run 的 trace 以 `"status": "planned"` 標示且無 duration。
trace 是證據鏈的一部分:與 raw payload(data_hex)一起,
構成「這台裝置上到底發生過什麼」的完整記錄。

## 完整範例

```yaml
version: 2
name: scsi_capacity_check
description: INQUIRY, capacity, then read LBA 0 and cross-check block size.

targets:
  - id: disk0
    protocol: scsi
    executor: mock
    device: "mock://scsi/0"

steps:
  - name: inq
    target: disk0
    command: inquiry
    assert:
      - { path: inquiry.vendor, op: exists }

  - name: read_cap
    target: disk0
    command: read_capacity_16
    depends_on: [inq]
    assert:
      - { path: capacity.block_size, op: eq, value: 512 }

  - name: read_lba0
    target: disk0
    command: read_16
    params: { lba: 0, transfer_length: 1 }
    depends_on: [read_cap]
    assert:
      - path: length
        op: eq
        value_from: { step: read_cap, path: capacity.block_size }
```
