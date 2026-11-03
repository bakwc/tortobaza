#!/usr/bin/env python3
import json
from pathlib import Path

HOST_NAME = "com.tortobaza.firefox_bridge"
EXTENSION_ID = "firefox-bridge@tortobaza.local"


def main():
    host_path = Path(__file__).resolve().parent / "firefox_bridge_host.py"
    host_path.chmod(0o755)
    manifest = {
        "name": HOST_NAME,
        "description": "Firefox Bridge TCP host",
        "path": str(host_path),
        "type": "stdio",
        "allowed_extensions": [EXTENSION_ID],
    }
    destination_dir = Path.home() / "Library" / "Application Support" / "Mozilla" / "NativeMessagingHosts"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / (HOST_NAME + ".json")
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
