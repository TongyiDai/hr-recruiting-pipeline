#!/usr/bin/env python3
"""Aggregate a de-identified recruiting pipeline export.

The script is deliberately local-only: standard library, no network, no Feishu
write-back, and no candidate-level records in the report.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MAIN_STAGES = ["sourced", "screen", "interview", "debrief", "offer", "accepted"]
TERMINAL_STAGES = {"rejected", "withdrawn", "on_hold"}
STAGE_ALIASES = {
    "sourced": "sourced",
    "source": "sourced",
    "prospect": "sourced",
    "发现": "sourced",
    "人才库": "sourced",
    "screen": "screen",
    "screening": "screen",
    "resume screen": "screen",
    "简历筛选": "screen",
    "初筛": "screen",
    "interview": "interview",
    "interviewing": "interview",
    "面试": "interview",
    "debrief": "debrief",
    "feedback": "debrief",
    "面试反馈": "debrief",
    "评估": "debrief",
    "offer": "offer",
    "offer stage": "offer",
    "发放offer": "offer",
    "录用沟通": "offer",
    "accepted": "accepted",
    "hired": "accepted",
    "offer accepted": "accepted",
    "已接受": "accepted",
    "已录用": "accepted",
    "rejected": "rejected",
    "reject": "rejected",
    "拒绝": "rejected",
    "淘汰": "rejected",
    "withdrawn": "withdrawn",
    "withdraw": "withdrawn",
    "撤回": "withdrawn",
    "on hold": "on_hold",
    "on_hold": "on_hold",
    "hold": "on_hold",
    "暂停": "on_hold",
}

FIELD_ALIASES = {
    "candidate_id": ["candidate_id", "candidateId", "候选人ID", "候选人编号", "申请编号", "id"],
    "stage": ["stage", "current_stage", "当前阶段", "阶段", "招聘状态", "状态"],
    "entered_at": ["entered_at", "enteredAt", "进入时间", "申请时间", "创建时间", "流程开始时间"],
    "updated_at": ["updated_at", "updatedAt", "更新时间", "状态更新时间", "最近更新时间"],
    "accepted_at": ["accepted_at", "acceptedAt", "接受Offer时间", "接受 Offer 时间", "录用确认时间"],
    "source": ["source", "来源", "渠道", "投递来源"],
    "job": ["job", "role", "职位", "岗位", "招聘岗位"],
    "recruiter": ["recruiter", "招聘人", "HR", "负责人"],
    "stage_history": ["stage_history", "stageHistory", "阶段历史", "状态历史"],
}


def clean_key(value: Any) -> str:
    return str(value).strip().casefold() if value is not None else ""


def first_value(item: dict[str, Any], logical_name: str) -> Any:
    for key in FIELD_ALIASES[logical_name]:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    text = str(value).strip()
    if text.isdigit():
        return parse_time(int(text))
    normalized = text.replace("/", "-")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(normalized, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_time(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def canonical_stage(value: Any) -> str:
    key = clean_key(value)
    return STAGE_ALIASES.get(key, "unknown")


def parse_history(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.casefold() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("candidates", "records", "data"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    raise ValueError("JSON must be an array or contain candidates/records/data array")


def median_or_none(values: Iterable[float]) -> float | None:
    values = list(values)
    return round(statistics.median(values), 2) if values else None


def days_between(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end or end < start:
        return None
    return round((end - start).total_seconds() / 86400, 2)


def normalize_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    quality = {
        "missing_fields": Counter(),
        "unknown_stages": Counter(),
        "invalid_dates": 0,
        "incomplete_histories": 0,
        "duplicate_candidate_ids": 0,
    }
    seen_ids: set[str] = set()
    for index, raw in enumerate(records, start=1):
        candidate_id = first_value(raw, "candidate_id")
        candidate_key = str(candidate_id).strip() if candidate_id not in (None, "") else f"row-{index}"
        if candidate_key in seen_ids and candidate_id not in (None, ""):
            quality["duplicate_candidate_ids"] += 1
        seen_ids.add(candidate_key)
        raw_stage = first_value(raw, "stage")
        stage = canonical_stage(raw_stage)
        if raw_stage in (None, ""):
            quality["missing_fields"]["stage"] += 1
        if stage == "unknown" and raw_stage not in (None, ""):
            quality["unknown_stages"][str(raw_stage)] += 1
        if candidate_id in (None, ""):
            quality["missing_fields"]["candidate_id"] += 1
        entered_at = parse_time(first_value(raw, "entered_at"))
        updated_at = parse_time(first_value(raw, "updated_at"))
        accepted_at = parse_time(first_value(raw, "accepted_at"))
        for field_name in ("entered_at", "updated_at", "accepted_at"):
            value = first_value(raw, field_name)
            if value not in (None, "") and parse_time(value) is None:
                quality["invalid_dates"] += 1
        history = []
        for entry in parse_history(first_value(raw, "stage_history")):
            entry_stage = canonical_stage(entry.get("stage"))
            entry_start = parse_time(entry.get("entered_at") or entry.get("enteredAt"))
            entry_end = parse_time(entry.get("exited_at") or entry.get("exitedAt"))
            if entry_stage == "unknown":
                quality["unknown_stages"][str(entry.get("stage"))] += 1
            if entry_start is None:
                quality["incomplete_histories"] += 1
            history.append({"stage": entry_stage, "entered_at": entry_start, "exited_at": entry_end})
        history.sort(key=lambda entry: entry["entered_at"] or datetime.max.replace(tzinfo=timezone.utc))
        if stage == "unknown" and history:
            known = [entry["stage"] for entry in history if entry["stage"] != "unknown"]
            if known:
                stage = known[-1]
        normalized.append({
            "id": candidate_key,
            "stage": stage,
            "entered_at": entered_at,
            "updated_at": updated_at,
            "accepted_at": accepted_at,
            "source": str(first_value(raw, "source") or "unknown").strip() or "unknown",
            "job": str(first_value(raw, "job") or "unknown").strip() or "unknown",
            "recruiter": str(first_value(raw, "recruiter") or "unknown").strip() or "unknown",
            "history": history,
        })
    quality["missing_fields"] = dict(quality["missing_fields"])
    quality["unknown_stages"] = dict(quality["unknown_stages"])
    return normalized, quality


def reached_stages(record: dict[str, Any]) -> set[str]:
    stages = {record["stage"]}
    stages.update(entry["stage"] for entry in record["history"])
    order = {stage: index for index, stage in enumerate(MAIN_STAGES)}
    if record["stage"] in order:
        stages.update(MAIN_STAGES[: order[record["stage"]] + 1])
    return stages


def analyze(records: list[dict[str, Any]], as_of: datetime | None = None) -> dict[str, Any]:
    normalized, quality = normalize_records(records)
    as_of = as_of or datetime.now(timezone.utc)
    stage_counter = Counter(record["stage"] for record in normalized)
    total = len(normalized)
    stage_counts = [
        {"stage": stage, "count": stage_counter.get(stage, 0), "share": round(stage_counter.get(stage, 0) / total, 4) if total else 0}
        for stage in MAIN_STAGES
    ]
    extras = [
        {"stage": stage, "count": count, "share": round(count / total, 4) if total else 0}
        for stage, count in sorted(stage_counter.items())
        if stage not in MAIN_STAGES
    ]

    transition_counts: Counter[tuple[str, str]] = Counter()
    from_counts: Counter[str] = Counter()
    duration_values: dict[str, list[float]] = defaultdict(list)
    for record in normalized:
        history = record["history"]
        for left, right in zip(history, history[1:]):
            if left["stage"] != "unknown" and right["stage"] != "unknown" and left["stage"] != right["stage"]:
                transition_counts[(left["stage"], right["stage"])] += 1
                from_counts[left["stage"]] += 1
        if history:
            for entry in history:
                end = entry["exited_at"] or (as_of if entry["entered_at"] else None)
                duration = days_between(entry["entered_at"], end)
                if duration is not None and entry["stage"] in MAIN_STAGES:
                    duration_values[entry["stage"]].append(duration)
        elif record["entered_at"] and record["stage"] in MAIN_STAGES:
            duration = days_between(record["entered_at"], record["updated_at"] or as_of)
            if duration is not None:
                duration_values[record["stage"]].append(duration)

    transitions = [
        {
            "from_stage": from_stage,
            "to_stage": to_stage,
            "count": count,
            "rate": round(count / from_counts[from_stage], 4) if from_counts[from_stage] else None,
        }
        for (from_stage, to_stage), count in sorted(transition_counts.items())
    ]
    stage_duration_days = [
        {"stage": stage, "sample_size": len(duration_values.get(stage, [])), "median_days": median_or_none(duration_values.get(stage, []))}
        for stage in MAIN_STAGES
    ]

    fill_values = [days_between(record["entered_at"], record["accepted_at"]) for record in normalized]
    fill_values = [value for value in fill_values if value is not None]
    source_stats: dict[str, dict[str, Any]] = {}
    for record in normalized:
        source = record["source"]
        stats = source_stats.setdefault(source, {"candidate_count": 0, "interview_reached": 0, "accepted_count": 0})
        stats["candidate_count"] += 1
        if reached_stages(record).intersection({"interview", "debrief", "offer", "accepted"}):
            stats["interview_reached"] += 1
        if "accepted" in reached_stages(record) or record["accepted_at"]:
            stats["accepted_count"] += 1
    source_effectiveness = []
    for source, stats in sorted(source_stats.items()):
        source_effectiveness.append({
            "source": source,
            **stats,
            "interview_rate": round(stats["interview_reached"] / stats["candidate_count"], 4) if stats["candidate_count"] else None,
            "accepted_rate": round(stats["accepted_count"] / stats["candidate_count"], 4) if stats["candidate_count"] else None,
        })

    present_fields = sorted({key for record in records for key in record.keys()})
    quality_report = {
        "missing_fields": quality["missing_fields"],
        "unknown_stages": quality["unknown_stages"],
        "invalid_dates": quality["invalid_dates"],
        "incomplete_histories": quality["incomplete_histories"],
        "duplicate_candidate_ids": quality["duplicate_candidate_ids"],
    }
    return {
        "schema_version": "1.0",
        "as_of": iso_time(as_of),
        "scope": {
            "record_count": total,
            "unique_candidate_count": len({record["id"] for record in normalized}),
            "fields_present": present_fields,
        },
        "stage_counts": stage_counts,
        "additional_statuses": extras,
        "transitions": transitions,
        "stage_duration_days": stage_duration_days,
        "fill_time_days": {"sample_size": len(fill_values), "median_days": median_or_none(fill_values)},
        "source_effectiveness": source_effectiveness,
        "quality": quality_report,
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# 招聘漏斗分析",
        "",
        f"- 截止时间：{report['as_of']}",
        f"- 记录数：{report['scope']['record_count']}",
        f"- 唯一候选人编号数：{report['scope']['unique_candidate_count']}",
        "",
        "## 阶段分布",
        "",
        "| 阶段 | 人数 | 占比 |",
        "|---|---:|---:|",
    ]
    for item in report["stage_counts"] + report["additional_statuses"]:
        lines.append(f"| {item['stage']} | {item['count']} | {item['share']:.1%} |")
    lines.extend(["", "## 阶段时长", "", "| 阶段 | 样本量 | 中位天数 |", "|---|---:|---:|"])
    for item in report["stage_duration_days"]:
        median = "NA" if item["median_days"] is None else item["median_days"]
        lines.append(f"| {item['stage']} | {item['sample_size']} | {median} |")
    fill = report["fill_time_days"]
    lines.extend(["", "## 招聘周期", "", f"从流程起点到接受 Offer：样本量 {fill['sample_size']}，中位天数 {fill['median_days'] if fill['median_days'] is not None else 'NA'}。", "", "## 来源效果", "", "| 来源 | 候选人数 | 到达面试 | 接受 Offer | 接受率 |", "|---|---:|---:|---:|---:|"])
    for item in report["source_effectiveness"]:
        rate = "NA" if item["accepted_rate"] is None else f"{item['accepted_rate']:.1%}"
        lines.append(f"| {item['source']} | {item['candidate_count']} | {item['interview_reached']} | {item['accepted_count']} | {rate} |")
    lines.extend(["", "## 数据质量", "", "```json", json.dumps(report["quality"], ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--as-of", help="ISO-8601 cutoff for open stages, useful for reproducible runs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        records = load_records(args.input)
        as_of = parse_time(args.as_of) if args.as_of else None
        report = analyze(records, as_of=as_of)
        output = json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else markdown_report(report)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
