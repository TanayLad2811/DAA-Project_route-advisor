export interface ViewTransform {
  scale: number
  offsetX: number
  offsetY: number
}

/**
 * Converts a screen / container coordinate (pixels relative to canvas element)
 * to original image coordinates.
 */
export function screenToImageCoords(
  screenX: number,
  screenY: number,
  transform: ViewTransform
): [number, number] {
  const imageX = (screenX - transform.offsetX) / transform.scale
  const imageY = (screenY - transform.offsetY) / transform.scale
  return [imageX, imageY]
}

/**
 * Converts original image coordinates to screen coordinates.
 */
export function imageToScreenCoords(
  imageX: number,
  imageY: number,
  transform: ViewTransform
): [number, number] {
  const screenX = imageX * transform.scale + transform.offsetX
  const screenY = imageY * transform.scale + transform.offsetY
  return [screenX, screenY]
}

/**
 * Calculates initial view transform to center and fit image within container.
 */
export function calculateFitTransform(
  containerWidth: number,
  containerHeight: number,
  imageWidth: number,
  imageHeight: number,
  padding = 40
): ViewTransform {
  if (containerWidth <= 0 || containerHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
    return { scale: 1, offsetX: 0, offsetY: 0 }
  }

  const availW = Math.max(containerWidth - padding * 2, 100)
  const availH = Math.max(containerHeight - padding * 2, 100)
  const scale = Math.min(availW / imageWidth, availH / imageHeight, 1.0)
  const offsetX = (containerWidth - imageWidth * scale) / 2
  const offsetY = (containerHeight - imageHeight * scale) / 2

  return { scale, offsetX, offsetY }
}

/**
 * Calculates zoom transform centered around a focal point (e.g. mouse cursor).
 */
export function zoomAtPoint(
  current: ViewTransform,
  factor: number,
  focalScreenX: number,
  focalScreenY: number,
  minScale = 0.05,
  maxScale = 15.0
): ViewTransform {
  const nextScale = Math.min(Math.max(current.scale * factor, minScale), maxScale)
  const scaleRatio = nextScale / current.scale

  const offsetX = focalScreenX - (focalScreenX - current.offsetX) * scaleRatio
  const offsetY = focalScreenY - (focalScreenY - current.offsetY) * scaleRatio

  return { scale: nextScale, offsetX, offsetY }
}

