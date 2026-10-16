#!/usr/bin/env python3
"""Run one experiment step and append a reproducible, hash-linked event record."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--display-command")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")

    stdout_path, stderr_path = Path(args.stdout), Path(args.stderr)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    started = now()
    interrupted = False
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        try:
            return_code = process.wait()
        except KeyboardInterrupt:
            interrupted = True
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return_code = 130
    ended = now()
    event = {
        "name": args.name,
        "started_at": started,
        "ended_at": ended,
        "cwd": os.getcwd(),
        "command": args.display_command or command,
        "exit_code": return_code,
        "interrupted": interrupted,
        "stdout": str(stdout_path),
        "stdout_sha256": digest(stdout_path),
        "stderr": str(stderr_path),
        "stderr_sha256": digest(stderr_path),
    }
    events = Path(args.events)
    events.parent.mkdir(parents=True, exist_ok=True)
    with events.open("a") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps(event, ensure_ascii=False))
    return return_code


if __name__ == "__main__":
    sys.exit(main())
