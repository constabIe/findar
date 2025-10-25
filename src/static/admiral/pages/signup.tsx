import React, { useState, useEffect } from "react"
import "../assets/auth.scss"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001/api/v1"

const SignUp: React.FC = () => {
  const [email, setEmail] = useState("")
  const [tgAlias, setTgAlias] = useState("")
  const [password, setPassword] = useState("")
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [theme, setTheme] = useState<"light" | "dark">("light")

  useEffect(() => {
    // Get theme from localStorage or default to light
    const savedTheme = localStorage.getItem("theme") as "light" | "dark" | null
    if (savedTheme) {
      setTheme(savedTheme)
      document.documentElement.setAttribute("data-theme", savedTheme)
    }
  }, [])

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light"
    setTheme(newTheme)
    localStorage.setItem("theme", newTheme)
    document.documentElement.setAttribute("data-theme", newTheme)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      await axios.post(`${API_URL}/users/register`, {
        email,
        password,
        telegram_alias: tgAlias
      })

      // Show success message and redirect to login
      setSuccess(true)
      setTimeout(() => {
        window.location.href = "/login"
      }, 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed. Please try again.")
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <button onClick={toggleTheme} className="theme-toggle" aria-label="Toggle theme">
        {theme === "light" ? "🌙" : "☀️"}
      </button>
      <div className="auth-card">
        <h1 className="auth-title">Sign Up</h1>
        <form onSubmit={handleSubmit} className="auth-form">
          {success && (
            <div className="auth-success">
              Account created successfully! Redirecting to login...
            </div>
          )}
          {error && (
            <div className="auth-error" style={{ color: "red", marginBottom: "1rem" }}>
              {error}
            </div>
          )}
          <div className="auth-input-group">
            <label htmlFor="email" className="auth-label">
              Email
            </label>
            <input
              type="email"
              id="email"
              className="auth-input"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading || success}
            />
          </div>

          <div className="auth-input-group">
            <label htmlFor="tgAlias" className="auth-label">
              Telegram Alias
            </label>
            <input
              type="text"
              id="tgAlias"
              className="auth-input"
              placeholder="@username"
              value={tgAlias}
              onChange={(e) => setTgAlias(e.target.value)}
              required
              disabled={loading || success}
            />
          </div>

          <div className="auth-input-group">
            <label htmlFor="password" className="auth-label">
              Password
            </label>
            <input
              type="password"
              id="password"
              className="auth-input"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading || success}
            />
          </div>

          <button
            type="submit"
            className="auth-button auth-button-primary"
            disabled={loading || success}
          >
            {loading ? "Signing Up..." : "Sign Up"}
          </button>

          <div className="auth-footer">
            <span className="auth-footer-text">Already have an account?</span>
            <a href="/login" className="auth-link">
              <button type="button" className="auth-button auth-button-secondary">
                Login
              </button>
            </a>
          </div>
        </form>
      </div>
    </div>
  )
}

export default SignUp
