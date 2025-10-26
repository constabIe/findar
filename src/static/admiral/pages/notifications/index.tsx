import React, { useState, useEffect } from "react"
import { Page, Card } from "@devfamily/admiral"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

interface NotificationTemplate {
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

interface NotificationTemplateWithId extends NotificationTemplate {
  id: string
  channel: "email" | "telegram"
}

interface TemplatesResponse {
  email_template: NotificationTemplateWithId
  telegram_template: NotificationTemplateWithId
}

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

interface ChannelSettings {
  email_enabled: boolean
  telegram_enabled: boolean
}

const Notifications: React.FC = () => {
  const [channel, setChannel] = useState<"email" | "telegram">("email")
  const [emailEnabled, setEmailEnabled] = useState(true)
  const [telegramEnabled, setTelegramEnabled] = useState(true)

  // Separate templates for email and telegram
  const [emailTemplate, setEmailTemplate] = useState<NotificationTemplate>({
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

  const [telegramTemplate, setTelegramTemplate] = useState<NotificationTemplate>({
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
  const [error, setError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")

  useEffect(() => {
    const initializeSettings = async () => {
      setLoading(true)
      const activeChannel = await loadChannelSettings()
      await loadTemplates(activeChannel)
      setLoading(false)
    }
    
    initializeSettings()
  }, [])

  const loadTemplates = async (currentChannel?: "email" | "telegram") => {
    try {
      const token = localStorage.getItem("admiral_global_admin_session_token")
      if (!token) {
        return
      }

      const response = await axios.get<TemplatesResponse>(
        `${API_URL}/users/notifications/templates`,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      )

      // Use provided channel or fall back to state
      const activeChannel = currentChannel || channel

      // Update email template
      if (response.data.email_template) {
        const { id, channel: ch, ...emailTemplateData } = response.data.email_template
        setEmailTemplate(emailTemplateData)
        
        // If email is the active channel, update settings immediately
        if (activeChannel === "email") {
          setSettings((prev) => ({ ...prev, ...emailTemplateData }))
        }
      }

      // Update telegram template
      if (response.data.telegram_template) {
        const { id, channel: ch, ...telegramTemplateData } = response.data.telegram_template
        setTelegramTemplate(telegramTemplateData)
        
        // If telegram is the active channel, update settings immediately
        if (activeChannel === "telegram") {
          setSettings((prev) => ({ ...prev, ...telegramTemplateData }))
        }
      }
    } catch (err: any) {
      console.error("Error loading templates:", err)
      // Don't show error to user on initial load, use defaults
    }
  }

  const loadChannelSettings = async () => {
    try {
      const token = localStorage.getItem("admiral_global_admin_session_token")
      if (!token) {
        setError("No authentication token found. Please login again.")
        return
      }

      const response = await axios.get<ChannelSettings>(`${API_URL}/users/notifications/channels`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      setEmailEnabled(response.data.email_enabled)
      setTelegramEnabled(response.data.telegram_enabled)

      // Set active channel based on what's enabled and return it
      let activeChannel: "email" | "telegram" = "email"
      if (response.data.email_enabled) {
        activeChannel = "email"
        setChannel("email")
      } else if (response.data.telegram_enabled) {
        activeChannel = "telegram"
        setChannel("telegram")
      }
      
      return activeChannel
    } catch (err: any) {
      console.error("Error loading channel settings:", err)
      // Don't show error to user on initial load, use defaults
      return "email" as "email" | "telegram"
    }
  }

  const handleChannelChange = async (newChannel: "email" | "telegram") => {
    try {
      const token = localStorage.getItem("admiral_global_admin_session_token")
      if (!token) {
        setError("No authentication token found. Please login again.")
        return
      }

      // Update channel settings on server
      const channelData: ChannelSettings = {
        email_enabled: newChannel === "email",
        telegram_enabled: newChannel === "telegram"
      }

      await axios.patch(`${API_URL}/users/notifications/channels`, channelData, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      // Update local state
      setChannel(newChannel)
      setEmailEnabled(channelData.email_enabled)
      setTelegramEnabled(channelData.telegram_enabled)

      // Switch to the appropriate template
      const template = newChannel === "email" ? emailTemplate : telegramTemplate
      setSettings((prev) => ({ ...prev, channel: newChannel, ...template }))

      // Reload settings from server to confirm
      await loadChannelSettings()

      setSuccessMessage(`Switched to ${newChannel} notifications successfully!`)
      setTimeout(() => setSuccessMessage(""), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update notification channel.")
      console.error("Error updating channel:", err)
    }
  }

  const handleToggle = async (field: keyof Omit<NotificationSettings, "channel">) => {
    const token = localStorage.getItem("admiral_global_admin_session_token")
    if (!token) {
      setError("No authentication token found. Please login again.")
      return
    }

    // Get current template based on active channel
    const currentTemplate = channel === "email" ? emailTemplate : telegramTemplate
    
    // Calculate new value
    const newValue = !currentTemplate[field]

    try {
      // Prepare template data with updated field
      const templateData: NotificationTemplate = {
        ...currentTemplate,
        [field]: newValue
      }

      // Update local state first for immediate UI feedback
      setSettings((prev) => ({
        ...prev,
        [field]: newValue
      }))

      // Send PATCH request to the appropriate endpoint based on active channel
      const endpoint =
        channel === "email"
          ? `${API_URL}/users/notifications/templates/email`
          : `${API_URL}/users/notifications/templates/telegram`

      await axios.patch(endpoint, templateData, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      // Update the appropriate template state
      if (channel === "email") {
        setEmailTemplate(templateData)
      } else {
        setTelegramTemplate(templateData)
      }

      setSuccessMessage(
        `${channel.charAt(0).toUpperCase() + channel.slice(1)} template updated successfully!`
      )
      setTimeout(() => setSuccessMessage(""), 2000)
    } catch (err: any) {
      // Revert the change on error
      setSettings((prev) => ({
        ...prev,
        [field]: !newValue
      }))
      setError(err.response?.data?.detail || "Failed to update template.")
      console.error("Error updating template:", err)
      setTimeout(() => setError(""), 3000)
    }
  }

  const renderToggleField = (field: keyof Omit<NotificationSettings, "channel">, label: string) => {
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
        <label style={{ color: "var(--color-typo-primary)", fontSize: "14px" }}>{label}</label>
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={settings[field]}
            onChange={() => handleToggle(field)}
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
                  className={`channel-button ${emailEnabled ? "active" : ""}`}
                  onClick={() => handleChannelChange("email")}
                >
                  Email {emailEnabled && "✓"}
                </button>
                <button
                  className={`channel-button ${telegramEnabled ? "active" : ""}`}
                  onClick={() => handleChannelChange("telegram")}
                >
                  Telegram {telegramEnabled && "✓"}
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
          </div>
        )}
      </Card>
    </Page>
  )
}

export default Notifications
