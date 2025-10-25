import React, { useState, useEffect } from "react"
import { Page, Card, Button } from "@devfamily/admiral"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

interface NotificationSettings {
  channel: "email" | "telegram"
  show_transaction_id: boolean
  show_amount: boolean
  show_timestamp: boolean
  show_from_account: boolean
  show_to_account: boolean
  show_triggered_rules: boolean
  show_fraud_probability: boolean
  show_location: boolean
  show_device_info: boolean
}

const Notifications: React.FC = () => {
  const [channel, setChannel] = useState<"email" | "telegram">("email")
  const [settings, setSettings] = useState<NotificationSettings>({
    channel: "email",
    show_transaction_id: true,
    show_amount: true,
    show_timestamp: true,
    show_from_account: true,
    show_to_account: true,
    show_triggered_rules: true,
    show_fraud_probability: true,
    show_location: true,
    show_device_info: true
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError("")

      const token = localStorage.getItem("admiral_global_admin_session_token")
      if (!token) {
        setError("No authentication token found. Please login again.")
        setLoading(false)
        return
      }

      // Load notification settings from API
      // For now, we'll use default settings
      // You can implement API call here to fetch user's notification preferences
      
      setLoading(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load notification settings.")
      console.error("Error loading settings:", err)
      setLoading(false)
    }
  }

  const handleChannelChange = (newChannel: "email" | "telegram") => {
    setChannel(newChannel)
    setSettings((prev) => ({ ...prev, channel: newChannel }))
  }

  const handleToggle = (field: keyof Omit<NotificationSettings, "channel">) => {
    setSettings((prev) => ({
      ...prev,
      [field]: !prev[field]
    }))
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError("")
      setSuccessMessage("")

      const token = localStorage.getItem("admiral_global_admin_session_token")
      if (!token) {
        setError("No authentication token found. Please login again.")
        setSaving(false)
        return
      }

      // Save settings to API
      // Implement API call here
      await axios.post(
        `${API_URL}/notifications/settings`,
        settings,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      )

      setSuccessMessage("Notification settings saved successfully!")
      setTimeout(() => setSuccessMessage(""), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to save notification settings.")
      console.error("Error saving settings:", err)
    } finally {
      setSaving(false)
    }
  }

  const renderToggleField = (
    field: keyof Omit<NotificationSettings, "channel">,
    label: string
  ) => {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 0",
          borderBottom: "1px solid var(--color-bg-border)"
        }}
      >
        <label style={{ color: "var(--color-typo-primary)", fontSize: "14px" }}>
          {label}
        </label>
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={settings[field]}
            onChange={() => handleToggle(field)}
            disabled={saving}
          />
          <span className="toggle-slider"></span>
        </label>
      </div>
    )
  }

  return (
    <Page title="Notification Settings">
      <style>
        {`
          .toggle-switch {
            position: relative;
            display: inline-block;
            width: 48px;
            height: 24px;
          }

          .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
          }

          .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: 0.3s;
            border-radius: 24px;
          }

          .toggle-slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
          }

          input:checked + .toggle-slider {
            background-color: var(--color-bg-brand);
          }

          input:checked + .toggle-slider:before {
            transform: translateX(24px);
          }

          input:disabled + .toggle-slider {
            opacity: 0.5;
            cursor: not-allowed;
          }

          .channel-selector {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
          }

          .channel-button {
            flex: 1;
            padding: 12px 24px;
            border: 2px solid var(--color-bg-border);
            background-color: var(--color-bg-default);
            color: var(--color-typo-primary);
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
          }

          .channel-button:hover {
            border-color: var(--color-bg-brand);
          }

          .channel-button.active {
            background-color: var(--color-bg-brand);
            color: white;
            border-color: var(--color-bg-brand);
          }
        `}
      </style>

      <Card>
        {loading ? (
          <div style={{ padding: "20px", textAlign: "center" }}>Loading settings...</div>
        ) : (
          <div>
            {successMessage && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#10b981",
                  color: "white",
                  borderRadius: "6px",
                  marginBottom: "20px"
                }}
              >
                {successMessage}
              </div>
            )}
            {error && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#ef4444",
                  color: "white",
                  borderRadius: "6px",
                  marginBottom: "20px"
                }}
              >
                {error}
              </div>
            )}

            <div style={{ marginBottom: "32px" }}>
              <h3 style={{ marginBottom: "16px", color: "var(--color-typo-primary)" }}>
                Notification Channel
              </h3>
              <div className="channel-selector">
                <button
                  className={`channel-button ${channel === "email" ? "active" : ""}`}
                  onClick={() => handleChannelChange("email")}
                  disabled={saving}
                >
                  Email
                </button>
                <button
                  className={`channel-button ${channel === "telegram" ? "active" : ""}`}
                  onClick={() => handleChannelChange("telegram")}
                  disabled={saving}
                >
                  Telegram
                </button>
              </div>
            </div>

            <div style={{ marginBottom: "32px" }}>
              <h3 style={{ marginBottom: "16px", color: "var(--color-typo-primary)" }}>
                Notification Content
              </h3>
              <p
                style={{
                  fontSize: "13px",
                  color: "var(--color-typo-secondary)",
                  marginBottom: "16px"
                }}
              >
                Choose what information to include in your {channel} notifications:
              </p>

              <div style={{ backgroundColor: "var(--color-bg-default)", borderRadius: "8px" }}>
                {renderToggleField("show_transaction_id", "Show Transaction ID")}
                {renderToggleField("show_amount", "Show Transaction Amount")}
                {renderToggleField("show_timestamp", "Show Transaction Timestamp")}
                {renderToggleField("show_from_account", "Show Source Account")}
                {renderToggleField("show_to_account", "Show Destination Account")}
                {renderToggleField("show_triggered_rules", "Show Triggered Rules")}
                {renderToggleField("show_fraud_probability", "Show Fraud Probability")}
                {renderToggleField("show_location", "Show Transaction Location")}
                {renderToggleField("show_device_info", "Show Device Information")}
              </div>
            </div>

            <div>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : "Save Settings"}
              </Button>
            </div>
          </div>
        )}
      </Card>
    </Page>
  )
}

export default Notifications
