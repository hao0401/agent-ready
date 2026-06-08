#!/usr/bin/env python3
"""Compatibility wrapper for the Agent Ready CLI implementation."""

from agent_ready.cli import *  # noqa: F403
from agent_ready.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
