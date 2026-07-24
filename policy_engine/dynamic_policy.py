#!/usr/bin/env python3
"""Dynamic policy simulation for capability updates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CAPABILITIES = ROOT_DIR / "blue_team_agent" / "capabilities.json"


def load_task_graph(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_capabilities(task_graph: dict[str, Any]) -> dict[str, bool]:
    allowed = {"network": False, "file_write": False}

    for task in task_graph.get("tasks", []):
        if not task.get("approved", False):
            continue
        for capability in task.get("requires", []):
            if capability in allowed:
                allowed[capability] = True

    return allowed


def persist_capabilities(path: Path, capabilities: dict[str, bool]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(capabilities, handle, indent=2)
        handle.write("\n")


def simulate_ebpf_map_updates(capabilities: dict[str, bool], pid: int | None) -> None:
    pid_text = str(pid) if pid is not None else "<target-pid>"
    print("Simulated eBPF map updates:")
    print(f"  target_pid[0]        = {pid_text}")
    print(f"  allow_network[0]     = {int(capabilities['network'])}")
    print(f"  allow_file_write[0]  = {int(capabilities['file_write'])}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dynamic policy update simulator")
    parser.add_argument("--task-graph", type=Path, required=True, help="JSON task graph")
    parser.add_argument(
        "--capabilities-file",
        type=Path,
        default=DEFAULT_CAPABILITIES,
        help="capabilities.json output path",
    )
    parser.add_argument("--pid", type=int, help="target pid for map update simulation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_graph = load_task_graph(args.task_graph)
    capabilities = evaluate_capabilities(task_graph)
    persist_capabilities(args.capabilities_file, capabilities)

    print(f"Updated {args.capabilities_file} -> {capabilities}")
    simulate_ebpf_map_updates(capabilities, args.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
