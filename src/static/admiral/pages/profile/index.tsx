import React, { useState, useEffect } from "react"
import { Page, Card, TextInput, Button } from "@devfamily/admiral"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001/api/v1"

interface ProfileData {
  email: string
  tgAccount: string
}

interface UserResponse {
  id: string
  email: string
  telegram_alias: string
  telegram_id: number
  created_at: string
}

const Profile: React.FC = () => {
  const [formData, setFormData] = useState<ProfileData>({
    email: "",
    tgAccount: ""
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")

  useEffect(() => {
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    try {
      setLoading(true)
      setError("")

      const token = localStorage.getItem("admiral_global_admin_session_token")

      if (!token) {
        setError("No authentication token found. Please login again.")
        setLoading(false)
        return
      }

      const response = await axios.get<UserResponse>(`${API_URL}/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const newFormData = {
        email: response.data.email || "",
        tgAccount: response.data.telegram_alias || ""
      }

      setFormData(newFormData)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load profile data.")
      console.error("Error fetching profile:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (name: keyof ProfileData, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccessMessage("")
    setSaving(true)

    try {
      const token = localStorage.getItem("admiral_global_admin_session_token")

      if (!token) {
        setError("No authentication token found. Please login again.")
        setSaving(false)
        return
      }

      // Send PATCH request to update telegram alias
      await axios.patch(
        `${API_URL}/users/me/telegram`,
        { telegram_alias: formData.tgAccount },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      )

      // Fetch updated profile data
      await fetchProfile()

      setSuccessMessage("Telegram alias updated successfully!")

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(""), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update telegram alias.")
      console.error("Error updating profile:", err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Page title="Profile">
      <Card>
        {loading ? (
          <div style={{ padding: "20px", textAlign: "center" }}>Loading profile...</div>
        ) : error ? (
          <div style={{ padding: "20px", color: "red" }}>{error}</div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {successMessage && (
                <div
                  style={{
                    padding: "12px",
                    backgroundColor: "#10b981",
                    color: "white",
                    borderRadius: "6px"
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
                    borderRadius: "6px"
                  }}
                >
                  {error}
                </div>
              )}

              <div>
                <label
                  style={{
                    display: "block",
                    marginBottom: "8px",
                    color: "var(--color-typo-primary)"
                  }}
                >
                  Email
                </label>
                <input
                  type="email"
                  name="email"
                  placeholder="Email address"
                  value={formData.email}
                  onChange={(e) => handleInputChange("email", e.target.value)}
                  disabled
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    backgroundColor: "var(--color-bg-default)",
                    border: "1px solid #000",
                    borderRadius: "6px",
                    color: "var(--color-typo-primary)",
                    fontSize: "14px",
                    outline: "none"
                  }}
                />
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    marginBottom: "8px",
                    color: "var(--color-typo-primary)"
                  }}
                >
                  Telegram Account
                </label>
                <input
                  type="text"
                  name="tgAccount"
                  placeholder="@username"
                  value={formData.tgAccount}
                  onChange={(e) => handleInputChange("tgAccount", e.target.value)}
                  disabled={saving}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    backgroundColor: "var(--color-bg-default)",
                    border: "1px solid #000",
                    borderRadius: "6px",
                    color: "var(--color-typo-primary)",
                    fontSize: "14px",
                    outline: "none"
                  }}
                />
              </div>

              <div style={{ marginTop: "16px" }}>
                <Button type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </div>
          </form>
        )}
      </Card>
    </Page>
  )
}

export default Profile
