"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight, Check, X, Skip } from "lucide-react";
import Link from "next/link";
import Image from "next/image";

interface QueueItem {
  id: number;
  image_id: string;
  image_path: string;
  timestamp: string;
  status: string;
  confidence_score: number;
  defect_detected: boolean;
  reason: string;
  model_version: string;
}

interface QueueStats {
  pending_count: number;
  labeled_count: number;
  approved_count: number;
  ready_for_training: number;
}

export default function LabelingQueuePage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchQueue();
    fetchStats();
    const interval = setInterval(fetchStats, 5000); // Refresh stats every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchQueue = async () => {
    try {
      const response = await fetch("/api/labeling/queue?status=pending&limit=100");
      if (response.ok) {
        const data = await response.json();
        setQueue(data);
        if (data.length === 0) {
          setMessage("All items labeled! Queue is empty.");
        }
      }
    } catch (error) {
      console.error("Error fetching queue:", error);
      setMessage("Error loading queue");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch("/api/labeling/stats");
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const handleSubmitLabel = async () => {
    if (!label) {
      setMessage("Please select a label");
      return;
    }

    if (currentIndex >= queue.length) {
      setMessage("No more items to label");
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch("/api/labeling/submit-label", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          queue_id: queue[currentIndex].id,
          label: label,
          reviewer_notes: notes,
        }),
      });

      if (response.ok) {
        setMessage("Label submitted successfully!");
        setLabel("");
        setNotes("");
        
        // Remove the current item from queue
        const newQueue = queue.filter((_, i) => i !== currentIndex);
        setQueue(newQueue);
        
        // Adjust current index
        if (currentIndex >= newQueue.length && currentIndex > 0) {
          setCurrentIndex(currentIndex - 1);
        }
        
        fetchStats();
        
        // Clear message after 2 seconds
        setTimeout(() => setMessage(""), 2000);
      } else {
        setMessage("Error submitting label");
      }
    } catch (error) {
      console.error("Error submitting label:", error);
      setMessage("Error submitting label");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkip = async () => {
    if (currentIndex >= queue.length) return;

    try {
      const response = await fetch(
        `/api/labeling/skip/${queue[currentIndex].id}`,
        { method: "GET" }
      );

      if (response.ok) {
        const newQueue = queue.filter((_, i) => i !== currentIndex);
        setQueue(newQueue);
        
        if (currentIndex >= newQueue.length && currentIndex > 0) {
          setCurrentIndex(currentIndex - 1);
        }
        
        setLabel("");
        setNotes("");
        setMessage("Item skipped");
        setTimeout(() => setMessage(""), 2000);
      }
    } catch (error) {
      console.error("Error skipping item:", error);
      setMessage("Error skipping item");
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setLabel("");
      setNotes("");
      setMessage("");
    }
  };

  const handleNext = () => {
    if (currentIndex < queue.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setLabel("");
      setNotes("");
      setMessage("");
    }
  };

  const currentItem = queue[currentIndex];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 text-white p-6">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="p-2 hover:bg-slate-700 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-3xl font-bold">Labeling Queue</h1>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-slate-700 rounded-lg p-4">
              <p className="text-slate-400 text-sm mb-1">Pending</p>
              <p className="text-2xl font-bold">{stats.pending_count}</p>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <p className="text-slate-400 text-sm mb-1">Labeled</p>
              <p className="text-2xl font-bold">{stats.labeled_count}</p>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <p className="text-slate-400 text-sm mb-1">Approved</p>
              <p className="text-2xl font-bold">{stats.approved_count}</p>
            </div>
            <div className="bg-blue-600/20 border border-blue-500 rounded-lg p-4">
              <p className="text-slate-400 text-sm mb-1">Ready for Training</p>
              <p className="text-2xl font-bold">{stats.ready_for_training}</p>
            </div>
          </div>
        )}

        {/* Message */}
        {message && (
          <div className="bg-blue-600/20 border border-blue-500 rounded-lg p-3 mb-6">
            {message}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto">
        {loading ? (
          <div className="text-center py-12">
            <p className="text-slate-400">Loading queue...</p>
          </div>
        ) : queue.length === 0 ? (
          <div className="text-center py-12 bg-slate-700 rounded-lg">
            <p className="text-xl text-slate-400">No items to label</p>
            <p className="text-slate-500 mt-2">
              All predictions have been reviewed or queue is empty
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Image Viewer */}
            <div className="lg:col-span-2">
              <div className="bg-slate-700 rounded-lg p-6">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold mb-2">Image Viewer</h2>
                  <p className="text-slate-400 text-sm">
                    {currentIndex + 1} of {queue.length}
                  </p>
                </div>

                {/* Image */}
                <div className="bg-black rounded-lg overflow-hidden mb-4 aspect-video flex items-center justify-center relative">
                  {currentItem.image_path ? (
                    <div className="relative w-full h-full">
                      <Image
                        src={currentItem.image_path}
                        alt={currentItem.image_id}
                        fill
                        className="object-cover"
                      />
                    </div>
                  ) : (
                    <div className="text-slate-500">No image available</div>
                  )}
                </div>

                {/* Item Details */}
                <div className="bg-slate-600 rounded-lg p-4 mb-4 space-y-2 text-sm">
                  <div>
                    <p className="text-slate-400">Image ID:</p>
                    <p className="font-mono text-blue-400">{currentItem.image_id}</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Model Confidence:</p>
                    <div className="flex items-center gap-2">
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            currentItem.confidence_score > 0.7
                              ? "bg-green-500"
                              : currentItem.confidence_score > 0.5
                              ? "bg-yellow-500"
                              : "bg-red-500"
                          }`}
                          style={{
                            width: `${currentItem.confidence_score * 100}%`,
                          }}
                        />
                      </div>
                      <span className="font-mono">
                        {(currentItem.confidence_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-slate-400">Reason:</p>
                    <p>{currentItem.reason}</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Model Version:</p>
                    <p>{currentItem.model_version}</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Timestamp:</p>
                    <p>{new Date(currentItem.timestamp).toLocaleString()}</p>
                  </div>
                </div>

                {/* Navigation */}
                <div className="flex gap-2">
                  <button
                    onClick={handlePrevious}
                    disabled={currentIndex === 0}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-slate-600 hover:bg-slate-500 disabled:bg-slate-800 disabled:text-slate-600 rounded-lg transition"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Previous
                  </button>
                  <button
                    onClick={handleNext}
                    disabled={currentIndex === queue.length - 1}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-slate-600 hover:bg-slate-500 disabled:bg-slate-800 disabled:text-slate-600 rounded-lg transition"
                  >
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Labeling Panel */}
            <div className="lg:col-span-1">
              <div className="bg-slate-700 rounded-lg p-6 sticky top-6">
                <h3 className="text-lg font-semibold mb-4">Add Label</h3>

                {/* Label Selection */}
                <div className="mb-4">
                  <label className="block text-sm text-slate-400 mb-2">
                    Defect Type
                  </label>
                  <div className="space-y-2">
                    {[
                      "no_defect",
                      "crack",
                      "scratch",
                      "dent",
                      "discoloration",
                      "uncertain",
                    ].map((option) => (
                      <button
                        key={option}
                        onClick={() => setLabel(option)}
                        className={`w-full text-left px-4 py-2 rounded-lg transition ${
                          label === option
                            ? "bg-blue-600 text-white"
                            : "bg-slate-600 text-slate-300 hover:bg-slate-500"
                        }`}
                      >
                        {option.replace("_", " ").toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Notes */}
                <div className="mb-4">
                  <label className="block text-sm text-slate-400 mb-2">
                    Notes (Optional)
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add any relevant notes..."
                    className="w-full bg-slate-600 text-white rounded-lg p-3 text-sm resize-none h-24 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Actions */}
                <div className="space-y-2">
                  <button
                    onClick={handleSubmitLabel}
                    disabled={submitting}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-500 disabled:bg-green-800 rounded-lg font-semibold transition"
                  >
                    <Check className="w-4 h-4" />
                    Submit Label
                  </button>
                  <button
                    onClick={handleSkip}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-600 hover:bg-slate-500 rounded-lg font-semibold transition"
                  >
                    <Skip className="w-4 h-4" />
                    Skip
                  </button>
                </div>

                {/* Progress */}
                <div className="mt-6 pt-6 border-t border-slate-600">
                  <p className="text-xs text-slate-400 mb-2">Progress</p>
                  <div className="w-full bg-slate-600 rounded-full h-2">
                    <div
                      className="h-2 bg-blue-500 rounded-full transition-all"
                      style={{
                        width: `${((currentIndex + 1) / queue.length) * 100}%`,
                      }}
                    />
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    {currentIndex + 1} of {queue.length} items
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
