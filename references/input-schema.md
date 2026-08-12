# 招聘流水输入结构

脚本接受 JSON 数组、包含 `candidates` 数组的 JSON 对象，或带标题行的 CSV。字段名可以是英文规范名，也可以是常见中文列名。

## 推荐 JSON

```json
[
  {
    "candidate_id": "c-001",
    "stage": "Interview",
    "entered_at": "2026-08-01T09:00:00+08:00",
    "updated_at": "2026-08-05T18:00:00+08:00",
    "source": "Referral",
    "job": "产品经理",
    "recruiter": "recruiter-a",
    "accepted_at": null,
    "stage_history": [
      {"stage": "Sourced", "entered_at": "2026-08-01T09:00:00+08:00", "exited_at": "2026-08-02T10:00:00+08:00"},
      {"stage": "Screen", "entered_at": "2026-08-02T10:00:00+08:00", "exited_at": "2026-08-03T15:00:00+08:00"},
      {"stage": "Interview", "entered_at": "2026-08-03T15:00:00+08:00", "exited_at": null}
    ]
  }
]
```

## 字段要求

- `candidate_id`：推荐必填，用于去重与候选人级关联；报告不会输出原值。
- `stage`：推荐必填；无法识别时记为 `unknown`。
- `entered_at`：用于流程起点和阶段时长。
- `updated_at`：用于判断当前数据时点。
- `source`：用于渠道分组；缺失时记为 `unknown`。
- `stage_history`：可选；没有历史时只能分析当前阶段分布。
- `accepted_at`：可选；没有该字段时无法计算完整招聘周期。

## 日期格式

支持 ISO-8601 日期时间、`YYYY-MM-DD`、`YYYY/MM/DD` 和 Unix 秒/毫秒时间戳。无法解析的日期进入数据质量报告，不参与时长计算。

## 阶段别名

脚本会把常见中英文别名归一到 `sourced`、`screen`、`interview`、`debrief`、`offer`、`accepted`。`rejected`、`withdrawn` 和 `on_hold` 保留为旁路状态。
