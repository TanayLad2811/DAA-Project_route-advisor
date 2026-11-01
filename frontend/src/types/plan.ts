export interface PlanMetadata {
  plan_id: string
  filename: string
  original_width: number
  original_height: number
  normalized_width: number
  normalized_height: number
  scale_factor: number
  meters_per_pixel?: number | null
  created_at: string
}

export interface PlanUploadResponse {
  plan_id: string
  width: number
  height: number
  image_url: string
  scale_factor: number
}

