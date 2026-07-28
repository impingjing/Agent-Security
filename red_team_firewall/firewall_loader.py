#!/usr/bin/env python3
"""BCC loader for eBPF capability firewall."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

try:
    from bcc import BPF
except ImportError:  # pragma: no cover - runtime dependency
    BPF = None

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CAPABILITIES_FILE = ROOT_DIR / "blue_team_agent" / "capabilities.json"
EBPF_FILE = BASE_DIR / "ebpf_interceptor.c"


def load_capabilities(path: Path) -> dict[str, bool]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {
        "network": bool(data.get("network", False)),
        "file_write": bool(data.get("file_write", False)),
    }


def update_map_u32(bpf: BPF, map_name: str, key: int, value: int) -> None:
    bpf_map = bpf[map_name]
    bpf_map[bpf_map.Key(key)] = bpf_map.Leaf(value)


def attach_firewall(target_pid: int, kill_on_violation: bool, capabilities_file: Path) -> BPF:
    if BPF is None:
        raise RuntimeError("bcc is not installed. Install dependencies from requirements.txt")

    capabilities = load_capabilities(capabilities_file)
    program_text = EBPF_FILE.read_text(encoding="utf-8")

    bpf = BPF(text=program_text)
    bpf.attach_kprobe(event=bpf.get_syscall_fnname("openat"), fn_name="trace_openat")
    bpf.attach_kprobe(event=bpf.get_syscall_fnname("connect"), fn_name="trace_connect")

    update_map_u32(bpf, "target_pid", 0, target_pid)
    update_map_u32(bpf, "allow_network", 0, int(capabilities["network"]))
    update_map_u32(bpf, "allow_file_write", 0, int(capabilities["file_write"]))
    update_map_u32(bpf, "kill_on_violation", 0, int(kill_on_violation))

    return bpf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attach eBPF firewall to target agent PID")
    parser.add_argument("--pid", type=int, required=True, help="PID to enforce")
    parser.add_argument(
        "--capabilities",
        type=Path,
        default=CAPABILITIES_FILE,
        help="path to capabilities.json",
    )
    parser.add_argument(
        "--kill-on-violation",
        action="store_true",
        help="send SIGKILL in addition to forcing -EPERM",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        bpf = attach_firewall(args.pid, args.kill_on_violation, args.capabilities)
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        print(f"failed to load firewall: {exc}", file=sys.stderr)
        return 1

    print(f"Firewall attached to pid={args.pid}. Press Ctrl+C to detach.")

    def _stop(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        bpf.cleanup()
        print("Firewall detached.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
