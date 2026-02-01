"use client"

import { useState, useEffect } from "react"
import { 
  Settings as SettingsIcon, Sun, Moon, Monitor,
  Bell, Shield, Database, Palette, Globe,
  Save, RotateCcw, ChevronRight, Check,
  Server, Key, Mail, Sliders
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { useTheme } from "next-themes"

export default function SettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [activeSection, setActiveSection] = useState("appearance")
  const [saved, setSaved] = useState(false)
  const [mounted, setMounted] = useState(false)

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true)
  }, [])

  const [settings, setSettings] = useState({
    // Appearance
    accentColor: "blue",
    compactMode: false,
    animations: true,
    
    // Notifications
    emailNotifications: true,
    pushNotifications: true,
    driftAlerts: true,
    systemAlerts: true,
    weeklyReports: false,
    
    // API Configuration
    apiEndpoint: "http://localhost:8000",
    apiTimeout: 30,
    retryAttempts: 3,
    
    // Model Settings
    defaultConfidence: 0.7,
    batchSize: 32,
    autoRetrain: false,
    retrainThreshold: 0.2,
    
    // Data & Storage
    retentionDays: 90,
    autoCleanup: true,
    compressionEnabled: true,
  })

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const sections = [
    { id: "appearance", label: "Appearance", icon: Palette },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "api", label: "API Configuration", icon: Server },
    { id: "model", label: "Model Settings", icon: Sliders },
    { id: "data", label: "Data & Storage", icon: Database },
    { id: "security", label: "Security", icon: Shield },
  ]

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">Settings</h1>
          <p className="text-sm text-gray-500 mt-1">Manage your application preferences</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setSettings({
                accentColor: "blue",
                compactMode: false,
                animations: true,
                emailNotifications: true,
                pushNotifications: true,
                driftAlerts: true,
                systemAlerts: true,
                weeklyReports: false,
                apiEndpoint: "http://localhost:8000",
                apiTimeout: 30,
                retryAttempts: 3,
                defaultConfidence: 0.7,
                batchSize: 32,
                autoRetrain: false,
                retrainThreshold: 0.2,
                retentionDays: 90,
                autoCleanup: true,
                compressionEnabled: true,
              })
              setTheme("system")
            }}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
          >
            <RotateCcw className="h-4 w-4" />
            Reset to Default
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-lg text-sm font-medium"
          >
            {saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            {saved ? "Saved!" : "Save Changes"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="col-span-1">
          <nav className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors ${
                  activeSection === section.id
                    ? "bg-gray-100 dark:bg-gray-800 text-black dark:text-white"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <section.icon className="h-4 w-4" />
                  <span className="text-sm font-medium">{section.label}</span>
                </div>
                <ChevronRight className={`h-4 w-4 transition-transform ${activeSection === section.id ? "rotate-90" : ""}`} />
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="col-span-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          {activeSection === "appearance" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-black dark:text-white mb-4">Appearance</h3>
                
                {/* Theme */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Theme</label>
                  <div className="flex gap-3">
                    {[
                      { value: "light", label: "Light", icon: Sun },
                      { value: "dark", label: "Dark", icon: Moon },
                      { value: "system", label: "System", icon: Monitor },
                    ].map((option) => (
                      <button
                        key={option.value}
                        onClick={() => {
                          setTheme(option.value)
                        }}
                        className={`flex-1 flex items-center justify-center gap-2 p-4 rounded-lg border-2 transition-all ${
                          mounted && theme === option.value
                            ? "border-black dark:border-white bg-gray-50 dark:bg-gray-800"
                            : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                        }`}
                      >
                        <option.icon className="h-5 w-5" />
                        <span className="font-medium">{option.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Accent Color */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Accent Color</label>
                  <div className="flex gap-3">
                    {["blue", "green", "purple", "orange", "pink"].map((color) => (
                      <button
                        key={color}
                        onClick={() => setSettings({ ...settings, accentColor: color })}
                        className={`h-10 w-10 rounded-full transition-transform ${
                          color === "blue" ? "bg-blue-500" :
                          color === "green" ? "bg-green-500" :
                          color === "purple" ? "bg-purple-500" :
                          color === "orange" ? "bg-orange-500" : "bg-pink-500"
                        } ${settings.accentColor === color ? "ring-2 ring-offset-2 ring-black dark:ring-white scale-110" : ""}`}
                      />
                    ))}
                  </div>
                </div>

                {/* Toggle Options */}
                <ToggleSetting
                  label="Compact Mode"
                  description="Use a more compact layout with smaller spacing"
                  checked={settings.compactMode}
                  onChange={(checked) => setSettings({ ...settings, compactMode: checked })}
                />
                <ToggleSetting
                  label="Animations"
                  description="Enable smooth transitions and animations"
                  checked={settings.animations}
                  onChange={(checked) => setSettings({ ...settings, animations: checked })}
                />
              </div>
            </div>
          )}

          {activeSection === "notifications" && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-black dark:text-white mb-4">Notifications</h3>
              
              <ToggleSetting
                label="Email Notifications"
                description="Receive important updates via email"
                checked={settings.emailNotifications}
                onChange={(checked) => setSettings({ ...settings, emailNotifications: checked })}
              />
              <ToggleSetting
                label="Push Notifications"
                description="Get real-time notifications in your browser"
                checked={settings.pushNotifications}
                onChange={(checked) => setSettings({ ...settings, pushNotifications: checked })}
              />
              <ToggleSetting
                label="Drift Alerts"
                description="Notify when data drift exceeds thresholds"
                checked={settings.driftAlerts}
                onChange={(checked) => setSettings({ ...settings, driftAlerts: checked })}
              />
              <ToggleSetting
                label="System Health Alerts"
                description="Notify when system health degrades"
                checked={settings.systemAlerts}
                onChange={(checked) => setSettings({ ...settings, systemAlerts: checked })}
              />
              <ToggleSetting
                label="Weekly Reports"
                description="Receive weekly performance summaries"
                checked={settings.weeklyReports}
                onChange={(checked) => setSettings({ ...settings, weeklyReports: checked })}
              />
            </div>
          )}

          {activeSection === "api" && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-black dark:text-white mb-4">API Configuration</h3>
              
              <InputSetting
                label="API Endpoint"
                description="Base URL for the backend API"
                value={settings.apiEndpoint}
                onChange={(value) => setSettings({ ...settings, apiEndpoint: value })}
                placeholder="http://localhost:8000"
              />
              <NumberSetting
                label="Request Timeout"
                description="Maximum time to wait for API responses (seconds)"
                value={settings.apiTimeout}
                onChange={(value) => setSettings({ ...settings, apiTimeout: value })}
                min={5}
                max={120}
                unit="seconds"
              />
              <NumberSetting
                label="Retry Attempts"
                description="Number of times to retry failed requests"
                value={settings.retryAttempts}
                onChange={(value) => setSettings({ ...settings, retryAttempts: value })}
                min={0}
                max={10}
                unit="attempts"
              />
            </div>
          )}

          {activeSection === "model" && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-black dark:text-white mb-4">Model Settings</h3>
              
              <SliderSetting
                label="Default Confidence Threshold"
                description="Minimum confidence score for predictions"
                value={settings.defaultConfidence}
                onChange={(value) => setSettings({ ...settings, defaultConfidence: value })}
                min={0}
                max={1}
                step={0.05}
              />
              <NumberSetting
                label="Batch Size"
                description="Number of images to process at once"
                value={settings.batchSize}
                onChange={(value) => setSettings({ ...settings, batchSize: value })}
                min={1}
                max={128}
                unit="images"
              />
              <ToggleSetting
                label="Auto Retrain"
                description="Automatically trigger retraining when drift is detected"
                checked={settings.autoRetrain}
                onChange={(checked) => setSettings({ ...settings, autoRetrain: checked })}
              />
              <SliderSetting
                label="Retrain Threshold"
                description="Drift score that triggers automatic retraining"
                value={settings.retrainThreshold}
                onChange={(value) => setSettings({ ...settings, retrainThreshold: value })}
                min={0.1}
                max={0.5}
                step={0.05}
                disabled={!settings.autoRetrain}
              />
            </div>
          )}

          {activeSection === "data" && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-black dark:text-white mb-4">Data & Storage</h3>
              
              <NumberSetting
                label="Data Retention Period"
                description="How long to keep inspection data"
                value={settings.retentionDays}
                onChange={(value) => setSettings({ ...settings, retentionDays: value })}
                min={30}
                max={365}
                unit="days"
              />
              <ToggleSetting
                label="Auto Cleanup"
                description="Automatically delete data older than retention period"
                checked={settings.autoCleanup}
                onChange={(checked) => setSettings({ ...settings, autoCleanup: checked })}
              />
              <ToggleSetting
                label="Compression"
                description="Compress stored images to save space"
                checked={settings.compressionEnabled}
                onChange={(checked) => setSettings({ ...settings, compressionEnabled: checked })}
              />
              
              <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Storage Usage</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Used</span>
                    <span className="text-black dark:text-white font-medium">234 GB / 500 GB</span>
                  </div>
                  <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 w-[47%]" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "security" && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-black dark:text-white mb-4">Security</h3>
              
              <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3 mb-3">
                  <Key className="h-5 w-5 text-gray-500" />
                  <div>
                    <p className="font-medium text-black dark:text-white">API Key</p>
                    <p className="text-xs text-gray-500">Used for external integrations</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="password"
                    value="••••••••••••••••••••••••"
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-sm"
                  />
                  <button className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-700">
                    Copy
                  </button>
                  <button className="px-3 py-2 bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 rounded-lg text-sm hover:bg-red-200 dark:hover:bg-red-900/50">
                    Regenerate
                  </button>
                </div>
              </div>

              <div className="pt-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Active Sessions</h4>
                <div className="space-y-2">
                  <SessionItem device="Chrome on Windows" location="New York, US" current={true} />
                  <SessionItem device="Safari on macOS" location="San Francisco, US" current={false} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}

function ToggleSetting({ label, description, checked, onChange }: {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div>
        <p className="font-medium text-black dark:text-white">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-12 h-6 rounded-full transition-colors ${
          checked ? "bg-black dark:bg-white" : "bg-gray-200 dark:bg-gray-700"
        }`}
      >
        <span className={`absolute top-1 left-1 h-4 w-4 rounded-full transition-transform ${
          checked ? "translate-x-6 bg-white dark:bg-black" : "bg-white dark:bg-gray-400"
        }`} />
      </button>
    </div>
  )
}

function InputSetting({ label, description, value, onChange, placeholder }: {
  label: string
  description: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <div className="py-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="mb-2">
        <p className="font-medium text-black dark:text-white">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm"
      />
    </div>
  )
}

function NumberSetting({ label, description, value, onChange, min, max, unit }: {
  label: string
  description: string
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  unit: string
}) {
  return (
    <div className="py-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="mb-2">
        <p className="font-medium text-black dark:text-white">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          min={min}
          max={max}
          className="w-24 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm"
        />
        <span className="text-sm text-gray-500">{unit}</span>
      </div>
    </div>
  )
}

function SliderSetting({ label, description, value, onChange, min, max, step, disabled }: {
  label: string
  description: string
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step: number
  disabled?: boolean
}) {
  return (
    <div className={`py-4 border-b border-gray-100 dark:border-gray-800 last:border-0 ${disabled ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="font-medium text-black dark:text-white">{label}</p>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        <span className="text-lg font-semibold text-black dark:text-white">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
      />
    </div>
  )
}

function SessionItem({ device, location, current }: { device: string; location: string; current: boolean }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
      <div className="flex items-center gap-3">
        <Globe className="h-5 w-5 text-gray-400" />
        <div>
          <p className="text-sm font-medium text-black dark:text-white">
            {device}
            {current && <span className="ml-2 text-xs text-green-600 dark:text-green-400">(Current)</span>}
          </p>
          <p className="text-xs text-gray-500">{location}</p>
        </div>
      </div>
      {!current && (
        <button className="text-xs text-red-600 dark:text-red-400 hover:underline">
          Revoke
        </button>
      )}
    </div>
  )
}
