"""Wire fixture whose inventory changes without restarting its process."""
import json
from pathlib import Path
import sys

inventory, calls = map(Path, sys.argv[1:])
for line in sys.stdin:
    request = json.loads(line)
    if "id" not in request:
        continue
    if request["method"] == "initialize":
        result = {"protocolVersion": request["params"]["protocolVersion"], "capabilities": {"tools": {}},
                  "serverInfo": {"name": "changing-tools", "version": "1"}}
    elif request["method"] == "tools/list":
        result = {"tools": [{"name": name, "inputSchema": {"type": "object"}} for name in json.loads(inventory.read_text())]}
    elif request["method"] == "tools/call":
        with calls.open("a") as stream:
            stream.write(request["params"]["name"] + "\n")
        result = {"content": [{"type": "text", "text": "ok"}]}
    else:
        result = {}
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
