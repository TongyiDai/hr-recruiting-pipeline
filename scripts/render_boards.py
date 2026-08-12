#!/usr/bin/env python3
"""Render Geometry Board Scene JSON files into deterministic, local SVGs."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


W, H = 1200, 675
BLACK = "#111111"
LINE = "#222222"
GRAY = "#666666"
LIGHT = "#E8E8E8"
FILL = "#F5F5F5"
BLUE = "#2F6BFF"
FONT = "-apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans CJK SC',sans-serif"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(x: float, y: float, value: str, size: int, fill: str = BLACK, anchor: str = "middle", weight: int = 400) -> str:
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}px" font-weight="{weight}" fill="{fill}">{esc(value)}</text>'


def line(x1: float, y1: float, x2: float, y2: float, dashed: bool = False) -> str:
    dash = ' stroke-dasharray="6 8"' if dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LINE}" stroke-width="1.5"{dash} marker-end="url(#arrow)" />'


def node_shape(node: dict, x: float, y: float, width: float = 128, height: float = 64) -> str:
    label = node.get("label", "")
    accent = bool(node.get("accent"))
    stroke = BLUE if accent else LINE
    fill = "#FFFFFF" if accent else FILL
    node_type = node.get("type")
    if node_type == "point":
        return f'<circle cx="{x}" cy="{y}" r="18" fill="{BLUE if accent else "#FFFFFF"}" stroke="{stroke}" stroke-width="2" data-node="{esc(node["id"])}" />' + text(x, y + 54, label, 16, BLACK, weight=600)
    if node_type == "circle":
        return f'<circle cx="{x}" cy="{y}" r="42" fill="{fill}" stroke="{stroke}" stroke-width="1.5" data-node="{esc(node["id"])}" />' + text(x, y + 6, label, 16, BLACK, weight=600)
    if node_type == "frame":
        return f'<rect x="{x - width / 2}" y="{y - height / 2}" width="{width}" height="{height}" fill="none" stroke="{stroke}" stroke-width="1.5" stroke-dasharray="6 8" data-node="{esc(node["id"])}" />' + text(x, y + 6, label, 16, BLACK, weight=600)
    if node_type == "cube":
        front = f'<rect x="{x - width / 2}" y="{y - height / 2}" width="{width}" height="{height}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" data-node="{esc(node["id"])}" />'
        top = f'<path d="M {x - width / 2} {y - height / 2} l 18 -14 h {width - 18} l -18 14" fill="none" stroke="{stroke}" stroke-width="1.5" />'
        return top + front + text(x, y + 6, label, 16, BLACK, weight=600)
    return f'<rect x="{x - width / 2}" y="{y - height / 2}" width="{width}" height="{height}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" data-node="{esc(node["id"])}" />' + text(x, y + 6, label, 16, BLACK, weight=600)


def title(scene: dict) -> str:
    return text(96, 76, scene["intent"]["core_message"], 28, BLACK, anchor="start", weight=600) + text(96, 104, "HR Open Skills · recruiting-pipeline", 12, GRAY, anchor="start")


def render_axis(scene: dict) -> str:
    nodes = scene["nodes"]
    positions = {node["id"]: (144 + index * 182, 340) for index, node in enumerate(nodes)}
    body = [title(scene), '<line x1="112" y1="340" x2="1088" y2="340" stroke="#B8B8B8" stroke-width="1" />']
    for left, right in zip(nodes, nodes[1:]):
        x1, y1 = positions[left["id"]]
        x2, y2 = positions[right["id"]]
        body.append(line(x1 + 22, y1, x2 - 22, y2))
    for node in nodes:
        body.append(node_shape(node, *positions[node["id"]]))
    return "".join(body)


def render_input_output(scene: dict) -> str:
    positions = {"scope": (170, 250), "fields": (170, 430), "aggregate": (600, 340), "report": (980, 250), "review": (980, 430)}
    body = [title(scene), '<line x1="360" y1="176" x2="360" y2="504" stroke="#E8E8E8" stroke-width="1" />', '<line x1="820" y1="176" x2="820" y2="504" stroke="#E8E8E8" stroke-width="1" />']
    body.extend([line(245, 250, 530, 340), line(245, 430, 530, 340), line(670, 340, 910, 250), line(670, 340, 910, 430)])
    by_id = {node["id"]: node for node in scene["nodes"]}
    for node_id, pos in positions.items():
        body.append(node_shape(by_id[node_id], *pos, width=160 if node_id != "aggregate" else 190, height=76))
    return "".join(body)


def render_layered(scene: dict) -> str:
    nodes = scene["nodes"]
    positions = {node["id"]: (600, 150 + index * 112) for index, node in enumerate(nodes)}
    body = [title(scene), '<line x1="600" y1="130" x2="600" y2="590" stroke="#B8B8B8" stroke-width="1" />']
    for top, bottom in zip(nodes, nodes[1:]):
        x1, y1 = positions[top["id"]]
        x2, y2 = positions[bottom["id"]]
        body.append(line(x1, y1 + 38, x2, y2 - 38))
    for index, node in enumerate(nodes):
        width = 320 - index * 28
        body.append(node_shape(node, *positions[node["id"]], width=width, height=68))
    return "".join(body)


def render_tension(scene: dict) -> str:
    positions = {"facts": (180, 340), "rules": (500, 250), "judgment": (940, 340), "boundary": (940, 340)}
    body = [title(scene), '<path d="M 250 340 C 340 340 390 270 420 250" fill="none" stroke="#222222" stroke-width="1.5" marker-end="url(#arrow)" />', '<path d="M 580 250 C 700 250 770 340 850 340" fill="none" stroke="#222222" stroke-width="1.5" marker-end="url(#arrow)" />']
    body.append('<rect x="770" y="176" width="330" height="330" fill="none" stroke="#B8B8B8" stroke-width="1" stroke-dasharray="6 8" />')
    body.append(text(790, 204, "只到这里", 12, GRAY, anchor="start"))
    by_id = {node["id"]: node for node in scene["nodes"]}
    body.append(node_shape(by_id["facts"], *positions["facts"], width=180, height=84))
    body.append(node_shape(by_id["rules"], *positions["rules"], width=180, height=84))
    body.append(node_shape(by_id["judgment"], *positions["judgment"], width=180, height=84))
    return "".join(body)


def render(scene: dict) -> str:
    composition = scene["intent"]["composition"]
    if composition == "axis-flow":
        body = render_axis(scene)
    elif composition == "input-process-output":
        body = render_input_output(scene)
    elif composition == "layered-architecture":
        body = render_layered(scene)
    elif composition == "tension-contrast":
        body = render_tension(scene)
    else:
        raise ValueError(f"unsupported composition: {composition}")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>{esc(scene["intent"]["core_message"])}</title>
  <desc>Geometry Blue board generated from Scene JSON.</desc>
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="{LINE}" />
    </marker>
  </defs>
  <rect width="1200" height="675" fill="#FFFFFF" />
  {body}
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for scene_path in sorted(args.scene_dir.glob("*.json")):
        scene = json.loads(scene_path.read_text(encoding="utf-8"))
        output_path = args.output_dir / f"{scene_path.stem}.svg"
        output_path.write_text(render(scene), encoding="utf-8")
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
