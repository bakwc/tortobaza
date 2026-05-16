import hashlib
import io
import shutil
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from PIL import Image, ImageOps

ALLOWED_DIMENSIONS = (200, 400, 600, 800, 1200, 1600)


def cache_dir_for(relative_path: str) -> Path:
    digest = hashlib.sha256(relative_path.encode()).hexdigest()
    return Path(settings.MEDIA_ROOT) / "image_cache" / digest


def clear_image_cache(relative_path: str) -> None:
    d = cache_dir_for(relative_path)
    if d.is_dir():
        shutil.rmtree(d)


def _safe_source_path(relative_path: str) -> Path:
    if ".." in relative_path:
        raise Http404()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if relative_path.startswith("products/"):
        root = media_root / "products"
    elif relative_path.startswith("options/"):
        root = media_root / "options"
    else:
        raise Http404()
    raw = Path(settings.MEDIA_ROOT) / relative_path
    resolved = raw.resolve()
    if not resolved.is_relative_to(root):
        raise Http404()
    return resolved


def _cache_file_name(w: int | None, h: int | None) -> str:
    wk = w if w is not None else 0
    hk = h if h is not None else 0
    return f"w{wk}_h{hk}.webp"


def _scale_image(im: Image.Image, w: int | None, h: int | None) -> Image.Image:
    out = im.copy()
    if w is not None and h is not None:
        out.thumbnail((w, h), Image.Resampling.LANCZOS)
    elif w is not None:
        ow, oh = out.size
        nh = max(1, int(round(oh * w / ow)))
        out = out.resize((w, nh), Image.Resampling.LANCZOS)
    elif h is not None:
        ow, oh = out.size
        nw = max(1, int(round(ow * h / oh)))
        out = out.resize((nw, h), Image.Resampling.LANCZOS)
    return out


def _ensure_rgb_or_rgba(im: Image.Image) -> Image.Image:
    if im.mode in ("RGB", "RGBA"):
        return im
    if im.mode == "P":
        return im.convert("RGBA")
    return im.convert("RGB")


def _read_dim(request, key: str) -> int | None:
    if key not in request.GET:
        return None
    raw = request.GET.get(key) or ""
    if not raw.isdigit() or int(raw) == 0:
        return -1
    return int(raw)


@require_GET
def scaled_image(request, relative_path: str):
    w = _read_dim(request, "w")
    h = _read_dim(request, "h")
    if w == -1:
        return HttpResponseBadRequest("invalid w")
    if h == -1:
        return HttpResponseBadRequest("invalid h")
    if w is None:
        w = None if h is not None else 800
    if w is not None and w not in ALLOWED_DIMENSIONS:
        return HttpResponseBadRequest("invalid w")
    if h is not None and h not in ALLOWED_DIMENSIONS:
        return HttpResponseBadRequest("invalid h")
    source = _safe_source_path(relative_path)
    if not source.is_file():
        raise Http404()
    cache_dir = cache_dir_for(relative_path)
    cache_name = _cache_file_name(w, h)
    cache_path = cache_dir / cache_name
    if not cache_path.is_file():
        cache_dir.mkdir(parents=True, exist_ok=True)
        im = ImageOps.exif_transpose(Image.open(source))
        im = _ensure_rgb_or_rgba(im)
        im = _scale_image(im, w, h)
        buf = io.BytesIO()
        im.save(
            buf,
            format="WEBP",
            quality=82,
            method=6,
        )
        cache_path.write_bytes(buf.getvalue())
    resp = FileResponse(
        cache_path.open("rb"),
        content_type="image/webp",
    )
    resp["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp
