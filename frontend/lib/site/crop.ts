export type CropValues = {
  crop_left: number;
  crop_top: number;
  crop_size: number;
};

export function defaultCenterCrop(width: number, height: number): CropValues {
  const side = Math.min(width, height);
  const left = (width - side) / 2;
  const top = (height - side) / 2;
  return {
    crop_size: 1,
    crop_left: width > side ? left / (width - side) : 0,
    crop_top: height > side ? top / (height - side) : 0,
  };
}

export function cropSidePx(width: number, height: number, crop_size: number): number {
  return crop_size * Math.min(width, height);
}

export function cropOffsetPx(
  width: number,
  height: number,
  crop: CropValues,
): { left: number; top: number; side: number } {
  const side = cropSidePx(width, height, crop.crop_size);
  const maxLeft = width - side;
  const maxTop = height - side;
  return {
    side,
    left: maxLeft > 0 ? crop.crop_left * maxLeft : 0,
    top: maxTop > 0 ? crop.crop_top * maxTop : 0,
  };
}

export function cropPreviewStyle(
  width: number,
  height: number,
  crop: CropValues,
  frameSize: number,
): { width: number; height: number; transform: string } {
  const { left, top, side } = cropOffsetPx(width, height, crop);
  const scale = frameSize / side;
  return {
    width: width * scale,
    height: height * scale,
    transform: `translate(${-left * scale}px, ${-top * scale}px)`,
  };
}

export function centerCrop(crop: CropValues): CropValues {
  return { ...crop, crop_left: 0.5, crop_top: 0.5 };
}

export function panCrop(
  width: number,
  height: number,
  start: CropValues,
  dxScreen: number,
  dyScreen: number,
  frameSize: number,
): CropValues {
  const { left, top, side } = cropOffsetPx(width, height, start);
  const maxLeft = width - side;
  const maxTop = height - side;
  if (maxLeft <= 0 && maxTop <= 0) return start;
  const ratio = side / frameSize;
  const leftPx = left - dxScreen * ratio;
  const topPx = top - dyScreen * ratio;
  return {
    ...start,
    crop_left: maxLeft > 0 ? Math.min(1, Math.max(0, leftPx / maxLeft)) : 0,
    crop_top: maxTop > 0 ? Math.min(1, Math.max(0, topPx / maxTop)) : 0,
  };
}

export function zoomCrop(
  width: number,
  height: number,
  crop: CropValues,
  crop_size: number,
): CropValues {
  const { left, top, side } = cropOffsetPx(width, height, crop);
  const centerX = left + side / 2;
  const centerY = top + side / 2;
  const newSide = cropSidePx(width, height, crop_size);
  const maxLeft = width - newSide;
  const maxTop = height - newSide;
  let newLeft = centerX - newSide / 2;
  let newTop = centerY - newSide / 2;
  if (maxLeft > 0) {
    newLeft = Math.min(maxLeft, Math.max(0, newLeft));
  } else {
    newLeft = 0;
  }
  if (maxTop > 0) {
    newTop = Math.min(maxTop, Math.max(0, newTop));
  } else {
    newTop = 0;
  }
  return {
    crop_size,
    crop_left: maxLeft > 0 ? newLeft / maxLeft : 0,
    crop_top: maxTop > 0 ? newTop / maxTop : 0,
  };
}
