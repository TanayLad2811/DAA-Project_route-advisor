import { describe, it, expect } from 'vitest'
import { screenToImageCoords, imageToScreenCoords, zoomAtPoint, calculateFitTransform } from './coords'

describe('coords transformations', () => {
  it('round-trips screen and image coordinates with offset and scale', () => {
    const transform = { scale: 2.5, offsetX: 100, offsetY: 50 }
    const imgX = 320
    const imgY = 240

    const [screenX, screenY] = imageToScreenCoords(imgX, imgY, transform)
    expect(screenX).toBe(320 * 2.5 + 100)
    expect(screenY).toBe(240 * 2.5 + 50)

    const [roundX, roundY] = screenToImageCoords(screenX, screenY, transform)
    expect(roundX).toBeCloseTo(imgX)
    expect(roundY).toBeCloseTo(imgY)
  })

  it('calculates fit transform centered within container', () => {
    const fit = calculateFitTransform(1000, 800, 2000, 1000, 0)
    expect(fit.scale).toBe(0.5) // 1000 / 2000 = 0.5
    expect(fit.offsetX).toBe(0)
    expect(fit.offsetY).toBe((800 - 500) / 2) // 150
  })

  it('zooms smoothly around focal point without moving focal image pixel', () => {
    const initial = { scale: 1.0, offsetX: 0, offsetY: 0 }
    const focalX = 400
    const focalY = 300
    const [imgFocalBefore] = screenToImageCoords(focalX, focalY, initial)

    const zoomed = zoomAtPoint(initial, 2.0, focalX, focalY)
    expect(zoomed.scale).toBe(2.0)
    const [imgFocalAfter] = screenToImageCoords(focalX, focalY, zoomed)
    expect(imgFocalAfter).toBeCloseTo(imgFocalBefore)
  })
})

