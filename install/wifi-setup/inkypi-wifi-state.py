#!/usr/bin/env python3
"""Adjust startup state while InkyPi is stopped; never overwrite a running writer."""
import json
import sys
from pathlib import Path

path = Path("/usr/local/inkypi/src/config/device.json")
data = json.loads(path.read_text())
if sys.argv[1] == "read":
    print(str(data.get("startup", False)).lower())
else:
    data["startup"] = True if sys.argv[1] == "setup" else not bool(data.get("playlist_config", {}).get("active_playlist"))
    path.write_text(json.dumps(data, indent=4))
