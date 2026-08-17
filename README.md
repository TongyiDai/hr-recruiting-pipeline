# 招聘流水分析

<p align="center">
  <img src="https://img.shields.io/badge/Agent%20Skill-agentskills.io-2F6BFF" alt="Agent Skill">
  <img src="https://img.shields.io/badge/license-Apache%202.0-3fb950" alt="License Apache 2.0">
  <img src="https://img.shields.io/badge/python-%3E%3D3.8-3572A5" alt="Python >=3.8">
  <img src="https://img.shields.io/badge/works%20with-Codex%20|%20Claude%20|%20Cursor%20|%20TRAE-555" alt="Works with major agents">
</p>

`hr-recruiting-pipeline`

一个可复核、可本地运行、适配飞书的中文招聘流水 Skill。

## 价值与适用场景

它把分散的候选人状态整理成一份可复核的招聘漏斗，让招聘负责人快速看清当前阶段、转换损耗、处理时长和渠道效果。飞书负责提供授权数据，本地脚本负责聚合，人工保留招聘判断权。

适合这些工作：

- 周报或招聘例会前，快速汇总岗位招聘进展。
- 面试量上升后，定位哪个阶段出现积压。
- 比较内推、招聘网站等渠道的到面率和 Offer 接受率。
- 根据阶段历史估算招聘周期，发现数据缺口。
- 使用飞书 Base、Sheets 或脱敏 JSON/CSV 做只读分析。

它适合做进展判断和数据整理，候选人录用、淘汰、排序、薪酬和晋升判断仍由人工完成。

## 先看懂它

招聘数据先经过身份校验和字段映射，再进入本地聚合，最后输出阶段分布、转换率、时长和来源效果。默认只读，候选人级别的录用、淘汰与排序留给人工判断。

<p align="center">
  <img src="assets/boards/pipeline-flow.svg?v=2" alt="招聘流水从来源经过筛选和面试进入 Offer 与接受" />
</p>

## 这个 Skill

### `hr-recruiting-pipeline`

适用于招聘进展、候选人流水、面试阶段、Offer 进展和招聘漏斗分析。输入可以来自用户明确授权的飞书 Base、Sheets，或脱敏 JSON/CSV。

核心输出包括：

- 主阶段人数与占比：Sourced、Screen、Interview、Debrief、Offer、Accepted。
- 相邻阶段转换率、阶段中位停留时长和完整招聘周期。
- 按渠道统计候选人数、到达面试人数、接受 Offer 人数和接受率。
- 缺失字段、未知阶段、异常日期、重复编号和历史记录完整度。

## 工作方式

先确认“谁授权、读什么、看哪段时间”，再读取最小字段集。飞书 CLI 负责读取，分析脚本留在本地，结果只输出聚合数据和质量提示。

<p align="center">
  <img src="assets/boards/feishu-read.svg?v=2" alt="飞书用户身份经过资源解析后只读招聘数据" />
</p>

快速检查身份：

```bash
lark-cli auth status --json --verify
```

支持 `auth status --json --verify` 的环境必须确认 `identity=user`、`verified=true`。当前 CLI 构建若没有 `auth` 子命令，可退回 `contact +get-user --as user` 或 `task +get-my-tasks --as user` 做只读兼容探测。

读取 Base 字段与记录：

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

读取 Sheets：

```bash
lark-cli sheets +cells-get \
  --url "https://example.feishu.cn/sheets/shtXXXX" \
  --sheet-name "招聘流水" --range "A1:Z200" \
  --include value,formula --as user --json
```

本地聚合：

```bash
python3 scripts/analyze_pipeline.py \
  --input tests/fixtures/pipeline.json \
  --format markdown \
  --as-of 2026-08-12
```

## 数据如何变成结论

脚本保留三层证据：输入范围、规则计算、人工解释。它可以告诉你漏斗在哪一阶段变窄、哪个渠道样本达到面试或接受 Offer；它不会替招聘负责人决定谁该录用或淘汰。

<p align="center">
  <img src="assets/boards/evidence-gate.svg?v=2" alt="输入数据经过字段映射和聚合后形成可复核报告" />
</p>

## 安全边界

- 默认使用 `--as user`。支持 `auth status --json --verify` 的环境先确认 `identity=user` 与 `verified=true`；当前 CLI 构建若没有 `auth` 子命令，可退回 `contact +get-user --as user` 或 `task +get-my-tasks --as user` 做只读兼容探测。
- 默认只读，不更新候选人阶段、不发送消息、不创建面试、不发 Offer。
- 原始候选人数据不进入仓库、不上传外部服务、不写回飞书。
- 报告不输出姓名、邮箱、电话、简历正文等直接识别信息。
- 候选人排序、淘汰、录用、薪酬判断需要人工复核和明确规则。

<p align="center">
  <img src="assets/boards/human-boundary.svg?v=2" alt="聚合数据提供证据，人工负责招聘决策" />
</p>

详细边界见 [Skill 说明](SKILL.md)、[飞书 CLI 适配](references/feishu-cli.md) 和 [安全说明](references/safety-boundaries.md)。

## 验证

在仓库根目录运行：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
# 可选：若本机已安装 skill-creator 工具，可额外校验 SKILL.md frontmatter
# python3 "$SKILL_CREATOR/scripts/quick_validate.py" .
```

当前假数据测试覆盖阶段归一、转换、招聘周期、来源效果和候选人编号脱敏。飞书命令可用占位符执行 `--dry-run`，不会访问真实数据。

Agent 的触发条件、输入确认、执行顺序、输出格式和停止规则见 [Agent 使用须知](AGENT-GUIDE.md)。

## 上游与许可证

本项目以 [Anthropic Human Resources Plugin](https://github.com/anthropics/knowledge-work-plugins/tree/658e077ffd7bdd50a12c19ec5ff36fe34c88be8a/human-resources) 的 `recruiting-pipeline` 为上游参考。固定版本和差异记录在 [UPSTREAM.md](UPSTREAM.md)，项目保留 Apache License 2.0 文本，见 [许可证](LICENSE)。

中文说明、飞书适配、本地聚合脚本和测试属于本项目新增内容。本项目暂不代表 Anthropic 官方维护或背书。
