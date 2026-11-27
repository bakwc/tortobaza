export async function resizeImageForUpload(file: File, maxSide: number): Promise<File> {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  const longSide = Math.max(bitmap.width, bitmap.height);
  if (longSide <= maxSide) {
    bitmap.close();
    return file;
  }
  const scale = maxSide / longSide;
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (context === null) {
    bitmap.close();
    throw new Error("canvas");
  }
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob((result) => resolve(result), "image/jpeg", 0.85);
  });
  if (blob === null) {
    throw new Error("blob");
  }
  const dot = file.name.lastIndexOf(".");
  const base = dot > 0 ? file.name.slice(0, dot) : file.name;
  return new File([blob], `${base}.jpg`, { type: "image/jpeg" });
}
