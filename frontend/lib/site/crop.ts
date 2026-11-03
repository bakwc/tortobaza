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
