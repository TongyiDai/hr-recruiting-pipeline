# 飞书 CLI 读取适配

本 Skill 使用用户授权的飞书身份读取招聘流水。当前实现限定为只读查询；写入命令不属于默认流程。

## 身份检查

```bash
lark-cli auth status --json --verify
```

继续条件：响应中的 `identity` 为 `user`，`verified` 为 `true`，且 token 状态有效。命令失败、身份不符或租户不明确时停止。

## Base 读取顺序

```bash
lark-cli base +url-resolve \
  --url "https://example.feishu.cn/base/appXXXX?table=tblXXXX" \
  --as user --json

lark-cli base +field-list \
  --base-token "appXXXX" --table-id "tblXXXX" \
  --as user --json

lark-cli base +record-list \
  --base-token "appXXXX" --table-id "tblXXXX" \
  --limit 200 --as user --json
```

如需缩小读取范围，可使用字段过滤、视图、排序或分页参数。先确认字段 ID 与业务列名的对应关系，再把结果转为本 Skill 的输入结构。

## Sheets 读取顺序

```bash
lark-cli sheets +workbook-info \
  --url "https://example.feishu.cn/sheets/shtXXXX" \
  --as user --json

lark-cli sheets +cells-get \
  --url "https://example.feishu.cn/sheets/shtXXXX" \
  --sheet-name "招聘流水" --range "A1:Z200" \
  --include value,formula --as user --json
```

只读取标题行和必要数据区。遇到合并单元格、公式结果或多工作表时，记录实际读取范围和口径。

## 本地分析

飞书读取结果应保存为脱敏 JSON 或 CSV，再交给本地脚本：

```bash
python3 scripts/analyze_pipeline.py \
  --input tests/fixtures/pipeline.json \
  --format json \
  --output /tmp/hr-pipeline-report.json
```

脚本只使用标准库，不调用网络，不会写回飞书。

## 证据记录

每次分析保留：数据源类型、脱敏后的资源标识、读取时间、时间窗、过滤条件、字段映射、记录数和脚本版本。原始候选人数据应留在用户指定的受控目录，不复制到 Skill 包。
