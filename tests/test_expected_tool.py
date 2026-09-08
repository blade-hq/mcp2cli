import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

import pytest


@pytest.mark.parametrize("persistent", [False, True])
def test_alias_drift_stops_before_call(tmp_path, persistent):
    inventory, calls = tmp_path / "tools.json", tmp_path / "calls"
    inventory.write_text(json.dumps(["foo-bar", "foo_bar"]))
    command = shlex.join([sys.executable, str(Path(__file__).with_name("mcp_changing_tools.py")), str(inventory), str(calls)])
    cache = tempfile.TemporaryDirectory(prefix="mcp-", dir="/tmp" if os.name == "posix" else None)
    env = dict(os.environ, MCP2CLI_CACHE_DIR=cache.name)
    cli = [sys.executable, "-m", "mcp2cli"]
    direct = ["--mcp-stdio", command, "--cache-ttl", "0"]
    def run(args, data=None):
        return subprocess.run(cli + args, input=data, env=env, capture_output=True, text=True, timeout=30)
    name = "expected-tool"
    try:
        if persistent:
            started = run(direct + ["--session-start", name])
            assert started.returncode == 0, started.stderr
        prefix = ["--session", name] if persistent else direct
        listed = run(prefix + ["--list", "--json"])
        assert listed.returncode == 0, listed.stderr
        alias = next(t["name"] for t in json.loads(listed.stdout) if t["toolName"] == "foo_bar")
        assert alias == "foo-bar-2"
        inventory.write_text(json.dumps(["foo-bar", "foo_bar", "foo-bar-2"]))
        rejected = run(prefix + ["--expect-tool-name", "foo_bar", alias, "--stdin"], "{}")
        assert rejected.returncode == 2, rejected.stderr
        assert "alias changed" in rejected.stderr
        assert not calls.exists(), "guard must run before sending tools/call"
        accepted = run(prefix + ["--expect-tool-name", "foo_bar", "foo-bar-3", "--stdin"], "{}")
        assert accepted.returncode == 0, accepted.stderr
        assert calls.read_text().splitlines() == ["foo_bar"]
    finally:
        if persistent:
            run(["--session-stop", name])
        cache.cleanup()
