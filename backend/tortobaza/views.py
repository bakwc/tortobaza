import subprocess
from pathlib import Path

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

BACKEND_DIR = Path(__file__).resolve().parent.parent
GIT_SHA = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=BACKEND_DIR,
    text=True,
).strip()


@api_view(["GET"])
def health(request: Request) -> Response:
    return Response({"status": "ok", "sha": GIT_SHA})
