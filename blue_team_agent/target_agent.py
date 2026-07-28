#!/usr/bin/env python3
"""Simulated LLM agent with file/network tools guarded by capabilities.json."""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent
CAPABILITIES_FILE = BASE_DIR / "capabilities.json"


class CapabilityError(PermissionError):
    """Raised when a tool call violates configured capabilities."""


def load_capabilities(path: Path = CAPABILITIES_FILE) -> Dict[str, bool]:
    with path.open("r", encoding="utf-8") as handle:
        data: Dict[str, Any] = json.load(handle)
    return {
        "network": bool(data.get("network", False)),
        "file_write": bool(data.get("file_write", False)),
    }


def write_local_file(target: Path, content: str, capabilities: Dict[str, bool]) -> str:
    if not capabilities.get("file_write", False):
        raise CapabilityError("file_write capability is disabled")
    target.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to {target}"


def network_ping(host: str, port: int, capabilities: Dict[str, bool], timeout: float = 2.0) -> str:
    if not capabilities.get("network", False):
        raise CapabilityError("network capability is disabled")
    with socket.create_connection((host, port), timeout=timeout):
        pass
    return f"connected to {host}:{port}"


def run_demo(args: argparse.Namespace) -> None:
    capabilities = load_capabilities()
    print(f"Loaded capabilities: {capabilities}")

    if args.try_file:
        target = BASE_DIR / "agent_output.txt"
        try:
            print(write_local_file(target, "agent generated output\n", capabilities))
        except CapabilityError as exc:
            print(f"[DENIED] file tool: {exc}")

    if args.try_network:
        try:
            print(network_ping(args.host, args.port, capabilities))
        except (CapabilityError, OSError) as exc:
            print(f"[DENIED/FAILED] network tool: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulated target agent")
    parser.add_argument("--try-file", action="store_true", help="attempt local file write")
    parser.add_argument("--try-network", action="store_true", help="attempt tcp connect")
    parser.add_argument("--host", default="127.0.0.1", help="host for --try-network")
    parser.add_argument("--port", type=int, default=80, help="port for --try-network")
    return parser.parse_args()


if __name__ == "__main__":
    run_demo(parse_args())
