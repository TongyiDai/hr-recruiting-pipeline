# 上游与许可证

## 来源

- 上游项目：[anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)
- 上游插件：[human-resources](https://github.com/anthropics/knowledge-work-plugins/tree/658e077ffd7bdd50a12c19ec5ff36fe34c88be8a/human-resources)
- 上游 Skill：[recruiting-pipeline](https://github.com/anthropics/knowledge-work-plugins/tree/658e077ffd7bdd50a12c19ec5ff36fe34c88be8a/human-resources/skills/recruiting-pipeline)
- 固定版本：`658e077ffd7bdd50a12c19ec5ff36fe34c88be8a`
- 核验时间：2026-08-12（Asia/Shanghai）
- 上游插件版本：`1.3.0`

## 复制范围

上游 `recruiting-pipeline` 主要描述招聘阶段、漏斗指标和 ATS 连接器方向。本包保留其核心概念，并补充：

- 中文工作流与字段口径。
- 飞书用户态 Base/Sheets 读取顺序。
- 本地脱敏聚合脚本和假数据测试。
- 只读、隐私、人工复核和证据记录边界。

## 上游目录事实

上游 README 提到 6 个自动触发的 HR Skill，并列出员工手册与薪酬基准等能力；在上述固定提交中，`human-resources/skills/` 实际可见 9 个 Skill 目录：`comp-analysis`、`draft-offer`、`interview-prep`、`onboarding`、`org-planning`、`people-report`、`performance-review`、`policy-lookup`、`recruiting-pipeline`。员工手册与薪酬基准目前出现在 README/连接器描述中，未作为独立 Skill 文件出现。

## 许可证

上游仓库根目录声明 Apache License 2.0。本包保留上游归属信息，并在 `LICENSE-APACHE-2.0` 中附带许可证文本。中文说明、飞书适配、分析脚本和测试属于本项目新增内容。

本包暂不声称得到 Anthropic 官方维护或背书。分发前应继续保留本文件、许可证文本和上游链接。
