#!/usr/bin/env python3
"""
ThesisClaw Guardrail Hook — guard.py

Invoked by the agent before running any shell command or tool.
Blocks dangerous commands and asks for confirmation before destructive ones.

Cross-platform (macOS / Linux). No external dependencies.
"""
from __future__ import annotations

import json
import os
import re
import sys

# ── Patterns that are always blocked ──────────────────────────────────────────
BLOCKED_PATTERNS: list[tuple[str, str]] = [
    # Lambda billing trap
    (r"\bsudo\s+shutdown\b", "sudo shutdown puts Lambda instances in Alert status and keeps billing. Use the Lambda API to terminate."),
    (r"\bpoweroff\b",        "poweroff puts Lambda instances in Alert status and keeps billing. Use the Lambda API to terminate."),
    (r"\bhalt\b",            "halt puts Lambda instances in Alert status and keeps billing. Use the Lambda API to terminate."),
    # Force push
    (r"git\s+push\s+.*--force", "git push --force is blocked. Use --force-with-lease if you really need this."),
    # Secret patterns in output
    (r"nvapi-[A-Za-z0-9_\-]{20,}", "Command output contains what looks like an NVIDIA API key. Blocked."),
    (r"ghp_[A-Za-z0-9]{36,}",      "Command output contains what looks like a GitHub PAT. Blocked."),
    (r"github_pat_[A-Za-z0-9_]{80,}", "Command output contains what looks like a GitHub fine-grained PAT. Blocked."),
]

# ── Patterns that require confirmation ────────────────────────────────────────
CONFIRM_PATTERNS: list[tuple[str, str]] = [
    (r"\bterminate\b", "This command contains 'terminate'. It may delete resources permanently."),
    (r"\bdestroy\b",   "This command contains 'destroy'. It may delete resources permanently."),
    (r"\bdelete\b",   "This command contains 'delete'. It may delete resources permanently."),
    (r"\bdrop\b",     "This command contains 'drop'. It may delete a database or table."),
]


def check(command: str) -> None:
    """Check the command against all patterns. Exit non-zero to block."""
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"\n🛑  GUARDRAIL BLOCKED\n{reason}\n", file=sys.stderr)
            sys.exit(1)

    for pattern, reason in CONFIRM_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"\n⚠️   GUARDRAIL WARNING\n{reason}\n", file=sys.stderr)
            answer = input("Type YES to continue, anything else to abort: ").strip()
            if answer != "YES":
                print("Aborted by guardrail.", file=sys.stderr)
                sys.exit(1)
            break


def main() -> None:
    # The hook receives the proposed command via stdin as JSON or as argv[1].
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        payload = sys.stdin.read().strip()
        try:
            data = json.loads(payload)
            command = data.get("command", payload)
        except json.JSONDecodeError:
            command = payload

    check(command)


if __name__ == "__main__":
    main()
