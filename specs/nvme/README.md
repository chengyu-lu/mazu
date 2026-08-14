# specs/nvme/ — 權威 NVMe 規格文件存放區

此資料夾存放專案的**權威 NVMe 規格文件(Markdown)**。
依架構規則(docs/skills-design.md、.claude/skills/_shared/spec-pins.md):

- 這裡的規格文件是 NVMe 協議知識的**唯一權威來源**。
- skill 與 references 檔案**不得**複製其內容,只能引用/導覽。
- 模型記憶永遠不能覆蓋這裡的內容。

## 待補(規格文件到位後)

1. 將規格 Markdown 放入本資料夾(單檔或多檔皆可;若為多檔,
   建議附上原始檔名與章節對應)。
2. 更新 `.claude/skills/_shared/spec-pins.md`:
   - `nvme_base.revision`:填入文件內宣告的版本(不可用猜的)
   - `nvme_base.source`:指向本資料夾的實際檔案路徑
   - 若包含 NVM Command Set Specification,同步更新
     `nvme_nvm_command_set` 條目
3. 檢視文件結構後,生成導覽索引(標題索引/指令索引),
   供 NVMe skill 精準查找 — 索引形式待文件結構確認後決定。

## 注意

- 規格文件的再散布可能受 NVM Express 授權條款限制。
  將本資料夾內容 push 到公開 repo 前,請先確認授權允許。
- 在規格文件與版本資訊到位前,`spec-pins.md` 維持 TBD,
  所有需要精確欄位/opcode/狀態碼的問題一律回答
  "Authoritative specification reference required"。
