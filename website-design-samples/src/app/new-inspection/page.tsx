"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { 
  Video, Upload, X, CheckCircle, AlertTriangle, 
  Loader2, RotateCcw, Download, Play, Square, 
  FlipHorizontal, Settings, Pause, Clock, Eye
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"

interface Detection {
  x1: number
  y1: number
  x2: number
  y2: number
  confidence: number
  label: string
}

interface DetectionEvent {
  timestamp: Date
  frameNumber: number
  detections: Detection[]
  defectDetected: boolean
}

export default function NewInspectionPage() {
  const [mode, setMode] = useState<"live" | "video">("live")
  
  // Live detection state
  const [isLiveActive, setIsLiveActive] = useState(false)
  const [isDetecting, setIsDetecting] = useState(false)
  const [facingMode, setFacingMode] = useState<"user" | "environment">("environment")
  const [detectionInterval, setDetectionInterval] = useState(500) // ms between detections
  const [currentDetections, setCurrentDetections] = useState<Detection[]>([])
  const [detectionHistory, setDetectionHistory] = useState<DetectionEvent[]>([])
  const [totalFramesProcessed, setTotalFramesProcessed] = useState(0)
  const [defectsFound, setDefectsFound] = useState(0)
  const [fps, setFps] = useState(0)
  
  // Video upload state
  const [selectedVideo, setSelectedVideo] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [isProcessingVideo, setIsProcessingVideo] = useState(false)
  const [videoProgress, setVideoProgress] = useState(0)
  const [videoResults, setVideoResults] = useState<DetectionEvent[]>([])
  
  const [error, setError] = useState<string | null>(null)
  
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const detectionLoopRef = useRef<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadedVideoRef = useRef<HTMLVideoElement>(null)
  const lastDetectionTime = useRef<number>(0)
  const frameCount = useRef<number>(0)
  const fpsStartTime = useRef<number>(0)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopLiveDetection()
      if (videoUrl) URL.revokeObjectURL(videoUrl)
    }
  }, [])

  // Start live camera feed
  const startLiveDetection = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } }
      })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
        setIsLiveActive(true)
        setError(null)
        setDetectionHistory([])
        setTotalFramesProcessed(0)
        setDefectsFound(0)
        frameCount.current = 0
        fpsStartTime.current = performance.now()
      }
    } catch (err) {
      setError("Failed to access camera. Please ensure camera permissions are granted.")
      console.error("Camera error:", err)
    }
  }

  // Stop live detection
  const stopLiveDetection = () => {
    if (detectionLoopRef.current) {
      cancelAnimationFrame(detectionLoopRef.current)
      detectionLoopRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsLiveActive(false)
    setIsDetecting(false)
    setCurrentDetections([])
  }

  // Toggle detection on/off
  const toggleDetection = () => {
    if (isDetecting) {
      if (detectionLoopRef.current) {
        cancelAnimationFrame(detectionLoopRef.current)
        detectionLoopRef.current = null
      }
      setIsDetecting(false)
      setCurrentDetections([])
    } else {
      setIsDetecting(true)
      lastDetectionTime.current = 0
      runDetectionLoop()
    }
  }

  // Detection loop
  const runDetectionLoop = () => {
    const loop = async () => {
      const now = performance.now()
      
      // Calculate FPS
      frameCount.current++
      const elapsed = now - fpsStartTime.current
      if (elapsed >= 1000) {
        setFps(Math.round(frameCount.current * 1000 / elapsed))
        frameCount.current = 0
        fpsStartTime.current = now
      }
      
      // Run detection at specified interval
      if (now - lastDetectionTime.current >= detectionInterval) {
        lastDetectionTime.current = now
        await detectFrame()
      }
      
      // Draw overlay
      drawOverlay()
      
      if (isDetecting) {
        detectionLoopRef.current = requestAnimationFrame(loop)
      }
    }
    
    detectionLoopRef.current = requestAnimationFrame(loop)
  }

  // Detect objects in current frame
  const detectFrame = async () => {
    if (!videoRef.current || !canvasRef.current) return
    
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    
    ctx.drawImage(video, 0, 0)
    const imageData = canvas.toDataURL("image/jpeg", 0.8)
    
    try {
      const response = await fetch("http://localhost:8000/api/predict/base64", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          image_base64: imageData,
          filename: `frame_${totalFramesProcessed}.jpg`
        }),
      })
      
      if (response.ok) {
        const data = await response.json()
        const detections: Detection[] = data.bounding_boxes || []
        setCurrentDetections(detections)
        setTotalFramesProcessed(prev => prev + 1)
        
        if (data.defect_detected) {
          setDefectsFound(prev => prev + 1)
          
          // Add to history
          const event: DetectionEvent = {
            timestamp: new Date(),
            frameNumber: totalFramesProcessed,
            detections,
            defectDetected: true
          }
          setDetectionHistory(prev => [event, ...prev].slice(0, 50)) // Keep last 50
        }
      }
    } catch (err) {
      console.error("Detection error:", err)
    }
  }

  // Draw detection overlay on video
  const drawOverlay = () => {
    if (!videoRef.current || !overlayCanvasRef.current) return
    
    const video = videoRef.current
    const canvas = overlayCanvasRef.current
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    // Draw bounding boxes
    currentDetections.forEach(det => {
      const color = det.label.toLowerCase().includes("defect") ? "#ef4444" : "#22c55e"
      
      // Box
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(det.x1, det.y1, det.x2 - det.x1, det.y2 - det.y1)
      
      // Label background
      const label = `${det.label} ${(det.confidence * 100).toFixed(0)}%`
      ctx.font = "14px monospace"
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = color
      ctx.fillRect(det.x1, det.y1 - 22, textWidth + 8, 22)
      
      // Label text
      ctx.fillStyle = "#ffffff"
      ctx.fillText(label, det.x1 + 4, det.y1 - 6)
    })
    
    // Draw status indicator
    if (isDetecting) {
      ctx.fillStyle = "#22c55e"
      ctx.beginPath()
      ctx.arc(20, 20, 8, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = "#ffffff"
      ctx.font = "12px monospace"
      ctx.fillText("DETECTING", 35, 25)
    }
  }

  // Toggle camera facing mode
  const toggleFacingMode = () => {
    const wasDetecting = isDetecting
    if (isDetecting) toggleDetection()
    stopLiveDetection()
    setFacingMode(prev => prev === "user" ? "environment" : "user")
    setTimeout(() => {
      startLiveDetection().then(() => {
        if (wasDetecting) setTimeout(toggleDetection, 500)
      })
    }, 100)
  }

  // Handle video file selection
  const handleVideoSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      if (!file.type.startsWith("video/")) {
        setError("Please select a video file")
        return
      }
      if (videoUrl) URL.revokeObjectURL(videoUrl)
      setSelectedVideo(file)
      setVideoUrl(URL.createObjectURL(file))
      setVideoResults([])
      setVideoProgress(0)
      setError(null)
    }
  }

  // Handle video drop
  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    const file = event.dataTransfer.files[0]
    if (file && file.type.startsWith("video/")) {
      if (videoUrl) URL.revokeObjectURL(videoUrl)
      setSelectedVideo(file)
      setVideoUrl(URL.createObjectURL(file))
      setVideoResults([])
      setVideoProgress(0)
      setError(null)
    }
  }, [videoUrl])

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
  }, [])

  // Process uploaded video frame by frame
  const processVideo = async () => {
    if (!uploadedVideoRef.current || !canvasRef.current) return
    
    setIsProcessingVideo(true)
    setVideoResults([])
    setVideoProgress(0)
    setError(null)
    
    const video = uploadedVideoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    
    const duration = video.duration
    const frameInterval = 0.5 // Process every 0.5 seconds
    let currentTime = 0
    let frameNumber = 0
    const results: DetectionEvent[] = []
    
    const processFrame = async (): Promise<void> => {
      return new Promise((resolve) => {
        video.currentTime = currentTime
        
        video.onseeked = async () => {
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight
          ctx.drawImage(video, 0, 0)
          
          const imageData = canvas.toDataURL("image/jpeg", 0.8)
          
          try {
            const response = await fetch("http://localhost:8000/api/predict/base64", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ 
                image_base64: imageData,
                filename: `video_frame_${frameNumber}.jpg`
              }),
            })
            
            if (response.ok) {
              const data = await response.json()
              if (data.defect_detected) {
                results.push({
                  timestamp: new Date(currentTime * 1000),
                  frameNumber,
                  detections: data.bounding_boxes || [],
                  defectDetected: true
                })
              }
            }
          } catch (err) {
            console.error("Frame processing error:", err)
          }
          
          frameNumber++
          currentTime += frameInterval
          setVideoProgress(Math.min((currentTime / duration) * 100, 100))
          
          resolve()
        }
      })
    }
    
    while (currentTime < duration) {
      await processFrame()
    }
    
    setVideoResults(results)
    setIsProcessingVideo(false)
    setVideoProgress(100)
  }

  // Reset video analysis
  const resetVideo = () => {
    if (videoUrl) URL.revokeObjectURL(videoUrl)
    setSelectedVideo(null)
    setVideoUrl(null)
    setVideoResults([])
    setVideoProgress(0)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  // Download results as JSON
  const downloadResults = () => {
    const data = mode === "live" ? detectionHistory : videoResults
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `detection_results_${new Date().toISOString()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString()
  }

  return (
    <DashboardLayout>
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-black dark:text-white mb-2">
            Video Inspection
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Real-time defect detection using live camera feed or video upload
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => { stopLiveDetection(); setMode("live") }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              mode === "live"
                ? "bg-black dark:bg-white text-white dark:text-black"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            <Video className="h-4 w-4" />
            Live Detection
          </button>
          <button
            onClick={() => { stopLiveDetection(); setMode("video") }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              mode === "video"
                ? "bg-black dark:bg-white text-white dark:text-black"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            <Upload className="h-4 w-4" />
            Video Upload
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <span className="text-red-700 dark:text-red-400">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="h-4 w-4 text-red-500" />
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Video Area */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
              {mode === "live" ? (
                // Live Detection Mode
                <div>
                  <div className="relative bg-black aspect-video">
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full h-full object-contain"
                    />
                    <canvas
                      ref={overlayCanvasRef}
                      className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                    />
                    {!isLiveActive && (
                      <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
                        <div className="text-center">
                          <Video className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                          <p className="text-gray-400">Camera not active</p>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Live Controls */}
                  <div className="p-4 border-t border-gray-200 dark:border-gray-800">
                    <div className="flex flex-wrap items-center gap-3">
                      {!isLiveActive ? (
                        <button
                          onClick={startLiveDetection}
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                        >
                          <Play className="h-4 w-4" />
                          Start Camera
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={toggleDetection}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                              isDetecting
                                ? "bg-red-600 hover:bg-red-700 text-white"
                                : "bg-green-600 hover:bg-green-700 text-white"
                            }`}
                          >
                            {isDetecting ? (
                              <>
                                <Pause className="h-4 w-4" />
                                Stop Detection
                              </>
                            ) : (
                              <>
                                <Eye className="h-4 w-4" />
                                Start Detection
                              </>
                            )}
                          </button>
                          <button
                            onClick={stopLiveDetection}
                            className="flex items-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
                          >
                            <Square className="h-4 w-4" />
                            Stop Camera
                          </button>
                          <button
                            onClick={toggleFacingMode}
                            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                            title="Flip camera"
                          >
                            <FlipHorizontal className="h-4 w-4" />
                          </button>
                        </>
                      )}
                      
                      {/* Detection interval setting */}
                      <div className="flex items-center gap-2 ml-auto">
                        <Settings className="h-4 w-4 text-gray-500" />
                        <select
                          value={detectionInterval}
                          onChange={(e) => setDetectionInterval(Number(e.target.value))}
                          className="px-2 py-1 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded text-sm text-black dark:text-white"
                          disabled={isDetecting}
                        >
                          <option value={200}>5 FPS</option>
                          <option value={500}>2 FPS</option>
                          <option value={1000}>1 FPS</option>
                          <option value={2000}>0.5 FPS</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                // Video Upload Mode
                <div>
                  {!videoUrl ? (
                    <div
                      onDrop={handleDrop}
                      onDragOver={handleDragOver}
                      onClick={() => fileInputRef.current?.click()}
                      className="aspect-video flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                      <Upload className="h-16 w-16 text-gray-400 mb-4" />
                      <p className="text-gray-600 dark:text-gray-400 font-medium mb-2">
                        Drop video file here or click to browse
                      </p>
                      <p className="text-gray-400 dark:text-gray-500 text-sm">
                        Supports MP4, WebM, MOV
                      </p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="video/*"
                        onChange={handleVideoSelect}
                        className="hidden"
                      />
                    </div>
                  ) : (
                    <div className="relative bg-black aspect-video">
                      <video
                        ref={uploadedVideoRef}
                        src={videoUrl}
                        controls
                        className="w-full h-full object-contain"
                      />
                    </div>
                  )}
                  
                  {/* Video Controls */}
                  {videoUrl && (
                    <div className="p-4 border-t border-gray-200 dark:border-gray-800">
                      <div className="flex flex-wrap items-center gap-3">
                        <button
                          onClick={processVideo}
                          disabled={isProcessingVideo}
                          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg transition-colors"
                        >
                          {isProcessingVideo ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Processing...
                            </>
                          ) : (
                            <>
                              <Play className="h-4 w-4" />
                              Analyze Video
                            </>
                          )}
                        </button>
                        <button
                          onClick={resetVideo}
                          disabled={isProcessingVideo}
                          className="flex items-center gap-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                        >
                          <RotateCcw className="h-4 w-4" />
                          Reset
                        </button>
                        
                        {isProcessingVideo && (
                          <div className="flex-1 ml-4">
                            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-blue-600 transition-all duration-300"
                                style={{ width: `${videoProgress}%` }}
                              />
                            </div>
                            <p className="text-xs text-gray-500 mt-1">{videoProgress.toFixed(0)}% complete</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Stats & History Panel */}
          <div className="space-y-6">
            {/* Stats */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
              <h3 className="font-semibold text-black dark:text-white mb-4">
                {mode === "live" ? "Live Stats" : "Analysis Results"}
              </h3>
              
              {mode === "live" ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">FPS</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{fps}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">Frames</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{totalFramesProcessed}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">Defects Found</p>
                    <p className="text-2xl font-bold text-red-500">{defectsFound}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">Current</p>
                    <p className="text-2xl font-bold text-black dark:text-white">{currentDetections.length}</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 dark:text-gray-400">Defects Found</span>
                    <span className="text-xl font-bold text-red-500">{videoResults.length}</span>
                  </div>
                  {videoResults.length > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 dark:text-gray-400">First Detection</span>
                      <span className="text-sm text-black dark:text-white">
                        Frame {videoResults[0]?.frameNumber}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Detection History */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-black dark:text-white">
                  Detection History
                </h3>
                {((mode === "live" && detectionHistory.length > 0) || 
                  (mode === "video" && videoResults.length > 0)) && (
                  <button
                    onClick={downloadResults}
                    className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                  >
                    <Download className="h-4 w-4" />
                    Export
                  </button>
                )}
              </div>
              
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {(mode === "live" ? detectionHistory : videoResults).length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">
                    No defects detected yet
                  </p>
                ) : (
                  (mode === "live" ? detectionHistory : videoResults).map((event, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
                    >
                      <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-red-700 dark:text-red-400">
                          {event.detections.length} defect(s) detected
                        </p>
                        <p className="text-xs text-red-600 dark:text-red-500">
                          {mode === "live" ? formatTime(event.timestamp) : `Frame ${event.frameNumber}`}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Current Detections (Live mode only) */}
            {mode === "live" && currentDetections.length > 0 && (
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
                <h3 className="font-semibold text-black dark:text-white mb-4">
                  Current Frame
                </h3>
                <div className="space-y-2">
                  {currentDetections.map((det, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded"
                    >
                      <span className="text-sm text-black dark:text-white">{det.label}</span>
                      <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                        {(det.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Hidden canvas for frame capture */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </DashboardLayout>
  )
}
