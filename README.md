# Agent-oriented Least Privilege and Capability Firewall

This repository contains a starter scaffold for a **Zero-Trust AI agent** architecture using:
- **Python** for the agent runtime, policy engine, and firewall orchestration
- **C/eBPF (BCC)** for low-level syscall interception and enforcement

## Project Structure

```text
blue_team_agent/
  target_agent.py        # Simulated LLM agent with network/file tools
  capabilities.json      # Baseline least-privilege capability config

red_team_firewall/
  ebpf_interceptor.c     # eBPF program for syscall interception/blocking
  firewall_loader.py     # BCC loader that attaches enforcement to a PID

policy_engine/
  dynamic_policy.py      # Dynamic capability update simulation from task graph
```

## Architecture Overview

1. **Target agent (Blue Team)**
   - `blue_team_agent/target_agent.py` reads `capabilities.json` and gates access to local file-write and network-connect tools.
   - Baseline capabilities are denied by default:
     ```json
     {"network": false, "file_write": false}
     ```

2. **Capability firewall (Red Team)**
   - `red_team_firewall/ebpf_interceptor.c` intercepts `openat` and `connect` syscalls.
   - Enforcement model:
     - If syscall is from the monitored PID and violates policy, return **`-EPERM`**.
     - Optional strict mode sends **`SIGKILL`** on violation.
   - Policy values are stored in eBPF maps (`target_pid`, `allow_network`, `allow_file_write`, `kill_on_violation`).

3. **Dynamic policy engine**
   - `policy_engine/dynamic_policy.py` evaluates an approved task graph, updates `capabilities.json`, and simulates corresponding eBPF map updates.
   - This models short-lived privilege escalation and revocation per approved workflow/task.

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

> Note: eBPF/BCC needs kernel support, root privileges, and BCC installed in the runtime environment.

### 2) Run the target agent simulation

```bash
python blue_team_agent/target_agent.py --try-file --try-network
```

With default capabilities, both actions should be denied at the application layer.

### 3) Attach syscall firewall to agent process

Start the agent (or another target process), capture its PID, then:

```bash
sudo python red_team_firewall/firewall_loader.py --pid <PID>
```

Optional strict mode:

```bash
sudo python red_team_firewall/firewall_loader.py --pid <PID> --kill-on-violation
```

### 4) Dynamically update policy from a task graph

Example task-graph JSON:

```json
{
  "tasks": [
    {"id": "fetch-context", "approved": true, "requires": ["network"]},
    {"id": "write-report", "approved": false, "requires": ["file_write"]}
  ]
}
```

Apply it:

```bash
python policy_engine/dynamic_policy.py --task-graph /path/to/task_graph.json --pid <PID>
```

## Security Notes

- This scaffold demonstrates **deny-by-default** and **least privilege** patterns.
- eBPF enforcement is intentionally minimal and should be hardened for production usage (comprehensive syscall coverage, robust task identity, stronger audit trails, and rollback safety).
- Always test on non-production systems first.
