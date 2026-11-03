def crop_tuple(left: float | None, top: float | None, size: float | None) -> tuple[float, float, float] | None:
    if left is None or top is None or size is None:
        return None
    return (left, top, size)


def crop_query(crop: tuple[float, float, float] | None) -> str:
    if crop is None:
        return ""
    left, top, size = crop
    return f"&crop={round(left, 4)},{round(top, 4)},{round(size, 4)}"


def parse_crop_param(raw: str) -> tuple[float, float, float] | None:
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 3:
        return None
    try:
        left, top, size = (round(float(parts[0]), 4), round(float(parts[1]), 4), round(float(parts[2]), 4))
    except ValueError:
        return None
    for value in (left, top, size):
        if value < 0 or value > 1:
            return None
    if size <= 0:
        return None
    return (left, top, size)


def crop_box(im_w: int, im_h: int, crop: tuple[float, float, float]) -> tuple[int, int, int, int]:
    left_n, top_n, size_n = crop
    side = max(1, int(round(size_n * min(im_w, im_h))))
    max_left = im_w - side
    max_top = im_h - side
    left = int(round(left_n * max_left)) if max_left > 0 else 0
    top = int(round(top_n * max_top)) if max_top > 0 else 0
    if left + side > im_w or top + side > im_h:
        raise ValueError("crop out of bounds")
    return (left, top, left + side, top + side)
