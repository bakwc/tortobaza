from catalog.crop import crop_query

LIST_WIDTHS = (200, 400, 600)
DETAIL_WIDTHS = (96, 200, 400, 800, 1200, 1600)


def _base(rel: str, public_base_url: str) -> str:
    rel = rel.lstrip("/")
    return f"{public_base_url.rstrip('/')}/api/img/{rel}"


def list_primary_image(
    rel: str | None,
    public_base_url: str,
    crop: tuple[float, float, float] | None = None,
) -> dict[str, str] | None:
    if not rel:
        return None
    b = _base(rel, public_base_url)
    cq = crop_query(crop)
    srcset = ", ".join(f"{b}?w={w}{cq} {w}w" for w in LIST_WIDTHS)
    return {"src": f"{b}?w=600{cq}", "srcset": srcset}


def detail_image(
    rel: str,
    public_base_url: str,
    crop: tuple[float, float, float] | None = None,
) -> dict[str, str]:
    b = _base(rel, public_base_url)
    cq = crop_query(crop)
    srcset = ", ".join(f"{b}?w={w}{cq} {w}w" for w in DETAIL_WIDTHS)
    return {"src": f"{b}?w=1200{cq}", "srcset": srcset}
