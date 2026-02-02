/**
 * API client for backend communication
 */

const API_BASE = "http://localhost:8000/api"

export interface InspectionLog {
  id: number
  image_id: string
  image_path: string
  timestamp: string
  model_name: string
  model_version: string
  defect_detected: boolean
  confidence_score: number
  defect_type?: string
  inference_time_ms: number
  processing_notes?: string
  bounding_boxes?: string
}

export interface PredictionResult {
  image_id: string
  defect_detected: boolean
  confidence_score: number
  defect_type?: string
  bounding_boxes?: Array<{
    x1: number
    y1: number
    x2: number
    y2: number
    confidence: number
    label: string
  }>
  inference_time_ms: number
  timestamp: string
  annotated_image?: string
}

export interface Metrics {
  total_predictions: number
  defects_detected: number
  defect_rate: number
  avg_confidence?: number
  avg_inference_time_ms?: number
  latest_timestamp?: string
}

export interface ModelStatus {
  model_name?: string
  model_version?: string
  last_prediction_time?: string
  total_predictions: number
  defects_detected: number
}

// Inspection Logs API
export async function getInspectionLogs(params?: {
  limit?: number
  offset?: number
  defects_only?: boolean
  model_name?: string
  min_confidence?: number
  max_confidence?: number
  defect_type?: string
  start_date?: string
  end_date?: string
  days_back?: number
}): Promise<InspectionLog[]> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.append("limit", String(params.limit))
  if (params?.offset) searchParams.append("offset", String(params.offset))
  if (params?.defects_only) searchParams.append("defects_only", "true")
  if (params?.model_name) searchParams.append("model_name", params.model_name)
  if (params?.min_confidence !== undefined)
    searchParams.append("min_confidence", String(params.min_confidence))
  if (params?.max_confidence !== undefined)
    searchParams.append("max_confidence", String(params.max_confidence))
  if (params?.defect_type) searchParams.append("defect_type", params.defect_type)
  if (params?.start_date) searchParams.append("start_date", params.start_date)
  if (params?.end_date) searchParams.append("end_date", params.end_date)
  if (params?.days_back) searchParams.append("days_back", String(params.days_back))

  const response = await fetch(
    `${API_BASE}/inspection-logs?${searchParams.toString()}`
  )
  if (!response.ok) throw new Error("Failed to fetch inspection logs")
  return response.json()
}

export async function getLatestInspectionLogs(params?: {
  count?: number
  defects_only?: boolean
  model_name?: string
}): Promise<InspectionLog[]> {
  const searchParams = new URLSearchParams()
  if (params?.count) searchParams.append("count", String(params.count))
  if (params?.defects_only) searchParams.append("defects_only", "true")
  if (params?.model_name) searchParams.append("model_name", params.model_name)

  const response = await fetch(
    `${API_BASE}/inspection-logs/latest?${searchParams.toString()}`
  )
  if (!response.ok) throw new Error("Failed to fetch latest inspection logs")
  return response.json()
}

export async function getInspectionLog(id: number): Promise<InspectionLog> {
  const response = await fetch(`${API_BASE}/inspection-logs/${id}`)
  if (!response.ok) throw new Error("Failed to fetch inspection log")
  return response.json()
}

// Metrics API
export async function getMetrics(): Promise<Metrics> {
  const response = await fetch(`${API_BASE}/metrics`)
  if (!response.ok) throw new Error("Failed to fetch metrics")
  return response.json()
}

// Model Status API
export async function getModelStatus(): Promise<ModelStatus> {
  const response = await fetch(`${API_BASE}/model-status`)
  if (!response.ok) throw new Error("Failed to fetch model status")
  return response.json()
}

export async function getModelVersionsHistory(limit?: number) {
  const searchParams = new URLSearchParams()
  if (limit) searchParams.append("limit", String(limit))

  const response = await fetch(
    `${API_BASE}/model-status/versions/history?${searchParams.toString()}`
  )
  if (!response.ok) throw new Error("Failed to fetch model versions")
  return response.json()
}

export async function compareModelVersions(
  version1: string,
  version2: string
) {
  const searchParams = new URLSearchParams()
  searchParams.append("version1", version1)
  searchParams.append("version2", version2)

  const response = await fetch(
    `${API_BASE}/model-status/versions/compare?${searchParams.toString()}`
  )
  if (!response.ok) throw new Error("Failed to compare model versions")
  return response.json()
}

// Prediction API
export async function predictFromImage(
  file: File
): Promise<PredictionResult> {
  const formData = new FormData()
  formData.append("file", file)

  const response = await fetch(`${API_BASE}/predict/upload`, {
    method: "POST",
    body: formData,
  })
  if (!response.ok) throw new Error("Failed to predict from image")
  return response.json()
}

export async function predictFromBase64(
  imageBase64: string,
  filename?: string
): Promise<PredictionResult> {
  const response = await fetch(`${API_BASE}/predict/base64`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_base64: imageBase64,
      filename,
    }),
  })
  if (!response.ok) throw new Error("Failed to predict from base64")
  return response.json()
}

export async function predictBatch(
  files: File[]
): Promise<PredictionResult[]> {
  const formData = new FormData()
  files.forEach((file) => formData.append("files", file))

  const response = await fetch(`${API_BASE}/predict/batch`, {
    method: "POST",
    body: formData,
  })
  if (!response.ok) throw new Error("Failed to process batch prediction")
  return response.json()
}

export async function predictVideoFrames(
  file: File,
  skipFrames: number = 1
): Promise<{ frames_processed: number; results: PredictionResult[] }> {
  const formData = new FormData()
  formData.append("files", file)
  formData.append("skip_frames", String(skipFrames))

  const response = await fetch(`${API_BASE}/predict/video-frames`, {
    method: "POST",
    body: formData,
  })
  if (!response.ok) throw new Error("Failed to process video frames")
  return response.json()
}

// Export API
export async function exportInspectionLogsCSV(params?: {
  limit?: number
  offset?: number
  defects_only?: boolean
  model_name?: string
}): Promise<Blob> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.append("limit", String(params.limit))
  if (params?.offset) searchParams.append("offset", String(params.offset))
  if (params?.defects_only) searchParams.append("defects_only", "true")
  if (params?.model_name) searchParams.append("model_name", params.model_name)

  const response = await fetch(
    `${API_BASE}/export/inspection-logs/csv?${searchParams.toString()}`
  )
  if (!response.ok) throw new Error("Failed to export inspection logs")
  return response.blob()
}

export async function exportMetricsCSV(): Promise<Blob> {
  const response = await fetch(`${API_BASE}/export/metrics/csv`)
  if (!response.ok) throw new Error("Failed to export metrics")
  return response.blob()
}

export async function exportSummaryReport() {
  const response = await fetch(`${API_BASE}/export/summary-report`)
  if (!response.ok) throw new Error("Failed to export summary report")
  return response.json()
}

// Performance API
export async function getPerformanceMetrics(endpoint?: string) {
  const searchParams = new URLSearchParams()
  if (endpoint) searchParams.append("endpoint", endpoint)

  const response = await fetch(
    `${API_BASE}/performance/metrics?${searchParams.toString()}`
  )
  if (!response.ok) throw new Error("Failed to fetch performance metrics")
  return response.json()
}

export async function getPerformanceSummary() {
  const response = await fetch(`${API_BASE}/performance/metrics/summary`)
  if (!response.ok) throw new Error("Failed to fetch performance summary")
  return response.json()
}

// Health API
export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) throw new Error("Failed to fetch health status")
  return response.json()
}

// Utility function to download blob as file
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
