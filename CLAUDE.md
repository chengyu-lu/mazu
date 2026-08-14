# CLAUDE.md

Mazu — 專為 SSD / USB / USB4 控制器韌體工程師設計的儲存驗證與除錯框架。
目標 pipeline:自然語言 → Flow IR → 驗證 → 裝置執行 → 結果解碼 → 分析。
完整設計請先讀 `docs/architecture.md`。

**這不是一般軟體專案。** 這個框架產生的指令會直接打進儲存裝置的韌體;
一個編錯的欄位可能毀掉資料、bricked 裝置,或讓工程師對著假象 debug 好幾天。
因此:**協議正確性永遠優先於實作速度。** 不確定就停下來查 spec,
查不到就回報 UNSUPPORTED——寧可少做,不可做錯。

## 十大原則(不可協商)

1. **協議正確性 > 實作速度。**
   寫 encoder/decoder 前先查規範,不是先寫再修。適用規範:
   NVMe Base Spec / NVM Command Set Spec、SPC/SBC(SCSI)、
   USB MSC BOT、UAS、USB4/CM。動到 wire format 的 PR,
   慢而正確的版本永遠贏過快而近似的版本。

2. **NVMe、SCSI、USB 的協議語意必須明確定義。**
   每個 LogicalCommand 在每個協議上的映射、參數語意、錯誤語意,
   都必須寫進 `translate/sntl.py` 的 `LOGICAL_MAPPING`(它是語意的
   single source of truth)。新增邏輯指令時,若某協議上的語意
   無法明確定義,就明確標記為該協議 UNSUPPORTED,不留模糊地帶。

3. **絕對不可在沒有明確確認的情況下執行破壞性指令。**
   write / raw_nvme / raw_scsi 及未來任何會改變裝置狀態的指令
   (format、sanitize、fw download…)都必須列入 `core/command.py` 的
   `DESTRUCTIVE_OPS`,並且只有 flow 層級明確寫了
   `allow_destructive: true` 才能通過驗證。
   **AI agent(包括你)不可以為了讓流程跑過而代替使用者加上這個旗標。**
   Phase 2 接真實裝置後,transport 另外預設唯讀模式,破壞性指令
   需要 transport 層第二道明確允許(雙重確認,缺一不可)。

4. **LLM 絕對不可直接存取儲存裝置。**
   LLM 的唯一輸出是 Flow IR(YAML)。`core/executor.py`、`transport/`、
   `translate/` 內不可出現任何 LLM 呼叫;LLM 產生的 IR 與人寫的 IR
   走完全相同的 validator,沒有捷徑。你在開發或除錯時也一樣:
   不可繞過 executor 直接對裝置節點下指令「試試看」。

5. **裝置執行必須透過確定性的執行器。**
   同一份 Flow IR + 同一個裝置狀態 ⇒ 同一串指令序列。
   executor 內不可有隨機性、不可有隱式重試、不可有啟發式決策;
   重試次數、逾時、條件分支若有需要,必須宣告在 IR 裡,
   成為可 diff、可重播的一部分。這是除錯可重現性的基礎。

6. **每一個指令編碼器／解碼器都必須有對應的測試。**
   新增或修改任何 encoder(LogicalCommand → wire)或 decoder
   (bytes → 結構化資料)時,必須同時提交測試:以 spec 排版的
   已知位元組向量做 roundtrip 驗證(參考 `tests/test_decode.py`)。
   沒有測試的 codec 視同不存在,不得合入。

7. **硬體測試必須與 mock 測試分開。**
   `tests/` 預設全部不需要硬體,任何人 clone 下來 `pytest` 就要全綠。
   Phase 2 起的實機測試放 `tests/hw/`,標記 `@pytest.mark.hw`,
   預設不跑(需 `pytest -m hw` 明確啟動)。mock 測試不可因環境問題
   silently skip;硬體測試不可混進預設測試集。

8. **優先使用結構化資料,而非自由格式文字。**
   層與層之間只傳結構化資料:LogicalCommand、CommandResult、
   FlowResult、巢狀 dict(snake_case,可用 dot-path 存取)。
   不可讓任何一層去 parse 另一層印出來的文字。人類可讀的報告
   (`analyze/report.py`)是最末端的呈現層,永遠從結構化資料生成,
   而不是反過來。

9. **每一次分析結果都應包含證據。**
   任何 PASS/FAIL 判定都必須可回溯到:下了什麼指令(op + params)、
   裝置回了什麼狀態(status + raw_status)、原始 payload
   (`CommandResult.data`,分析時引用 offset 與 hex)、
   解碼後的值與 assertion 的期望值。報告裡不可出現
   「看起來正常」這種無證據的結論;raw bytes 必須保留在結果物件上,
   不可在 pipeline 中途丟棄。

10. **絕對不可自行發明協議欄位、opcodes、CDWs、CDBs 或暫存器定義。**
    每一個 offset、opcode、CDW 欄位、CDB 欄位、log page ID、
    暫存器定義,都必須來自對應規範,並在程式碼註解標明出處
    (規範名稱 + 章節/表格,例如 `# NVMe Base Spec 2.x, Fig. Identify
    Controller Data Structure, offset 4-23: SN`)。查不到出處的欄位
    一律不實作——回 `Status.UNSUPPORTED` 或丟 `TranslationUnsupported`,
    絕不用「合理猜測」補位。這條也適用於 mock 裝置:
    `transport/mock/device.py` 產出的 payload 必須符合 spec offset,
    decoder 對 mock 與真實裝置不做任何區分。

## 常用指令

```bash
pip install -e ".[dev]"                                # 安裝(開發模式)
pytest                                                 # mock 測試(必須全綠才能 commit)
pytest -m hw                                           # 實機測試(Phase 2 起,需硬體)
mazu validate examples/flows/identify_and_smart.yaml   # 只驗證流程
mazu run examples/flows/identify_and_smart.yaml        # 在 mock 裝置上執行
mazu run <flow.yaml> --json                            # JSON 報告輸出
```

## 架構與依賴方向

```
src/mazu/
├── core/       # command.py(LogicalCommand/Op/Status)、flow.py(IR 解析)、
│               # validate.py(語意驗證)、executor.py(確定性執行)、result.py
├── transport/  # base.py(Transport ABC)、mock/(可用)、
│               # nvme.py / scsi.py / usb4.py(Phase 2/3 stub,勿刪介面說明)
├── translate/  # base.py(Translator ABC)、sntl.py(LOGICAL_MAPPING = 語意真相)
├── decode/     # bytes → 結構化 dict;以邏輯 op 為 key,不以 transport 為 key
├── analyze/    # report.py(text/JSON 報告,從結構化資料生成)
└── cli.py      # mazu validate / run
```

依賴方向:`cli → core → transport → translate`;`decode`/`analyze` 只依賴
`core` 的資料模型。**transport 永遠不 import 上層**;core 只認
`transport/base.py` 的 `Transport` ABC,不 import 任何具體 transport。
Transport 對無法表達的指令回 `Status.UNSUPPORTED`,絕不默默替換。

## 開發階段(照順序,不跳段)

- **Phase 1(完成)**:mock-first pipeline 全通。
- **Phase 2(下一步)**:`NvmeTransport`(Linux `NVME_IOCTL_ADMIN_CMD`/`IO_CMD`)、
  `ScsiTransport`(SG_IO)。做完 SCSI,USB BOT/UAS 自動支援。
  需加:裝置列舉(sysfs)、transport 層唯讀預設、`tests/hw/` 基礎建設。
- **Phase 3**:USB4 隧道偵測、補齊 `sntl.py` 的 wire-level 映射
  (只翻有明確 spec 對應的子集)。
- **Phase 4**:NL → Flow IR(LLM frontend)、廠商指令 plugin 機制。

**現在不要做**:NL/LLM 整合、完整 SNTL 覆蓋、廠商指令、GUI/Web、
分散式執行、Windows 支援、效能測試(Mazu 是功能驗證工具,不是 benchmark)。

## 新增一個邏輯指令的標準流程(缺一不可)

1. `core/command.py`:加 Op;會改變裝置狀態就同時加入 `DESTRUCTIVE_OPS`。
2. `translate/sntl.py`:在 `LOGICAL_MAPPING` 定義它在 NVMe 與 SCSI 上的
   語意映射(含 spec 出處);某協議無對應就明確標 UNSUPPORTED。
3. `core/validate.py`:參數驗證(必要參數、範圍、危險性)。
4. 各 transport 的 dispatch(mock 先行,payload 依 spec offset)。
5. 需要時加 decoder(`decode/`,回傳 snake_case 巢狀 dict)。
6. 測試:codec roundtrip 測試 + validator 測試 + mock pipeline 測試。
7. 範例 flow(`examples/flows/`,必須在 mock transport 上 PASS)。

Commit 前:`pytest` 全綠 + 兩個 example flow `mazu run` 都 PASS。

## 其他慣例

- Python ≥ 3.10,標準 dataclass,不引入重量級框架;
  目前唯一 runtime 依賴是 PyYAML。
- wire format 相關的常數(offset、opcode、page ID)集中定義、
  註明 spec 出處,不散落在邏輯裡當 magic number。
- 錯誤處理:裝置層級的拒絕(如 LBA 越界)是 `Status.ERROR` + raw_status,
  不是 Python exception;exception 保留給程式錯誤與 transport 故障。
