import React, { useState, useEffect } from 'react'
import '../assets/auth.scss'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'

const Login: React.FC = () => {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [theme, setTheme] = useState<'light' | 'dark'>('light')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        // Get theme from localStorage or default to light
        const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
        if (savedTheme) {
            setTheme(savedTheme)
            document.documentElement.setAttribute('data-theme', savedTheme)
        }
    }, [])

    const toggleTheme = () => {
        const newTheme = theme === 'light' ? 'dark' : 'light'
        setTheme(newTheme)
        localStorage.setItem('theme', newTheme)
        document.documentElement.setAttribute('data-theme', newTheme)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const response = await axios.post(`${API_URL}/users/login`, {
                email,
                password
            })

            // Store the token if provided
            if (response.data.token || response.data.access_token) {
                const token = response.data.token || response.data.access_token
                localStorage.setItem('admiral_global_admin_session_token', token)
            }

            // Navigate to main page
            window.location.href = '/'
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Login failed. Please check your credentials.')
            setLoading(false)
        }
    }

    return (
        <div className="auth-container">
            <button 
                onClick={toggleTheme} 
                className="theme-toggle"
                aria-label="Toggle theme"
            >
                {theme === 'light' ? '🌙' : '☀️'}
            </button>
            <div className="auth-card">
                <h1 className="auth-title">Login</h1>
                <form onSubmit={handleSubmit} className="auth-form">
                    {error && <div className="auth-error" style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
                    
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
                            disabled={loading}
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
                            disabled={loading}
                        />
                    </div>

                    <button type="submit" className="auth-button auth-button-primary" disabled={loading}>
                        {loading ? 'Logging in...' : 'Login'}
                    </button>

                    <div className="auth-footer">
                        <span className="auth-footer-text">Don't have an account?</span>
                        <a href="/signup" className="auth-link">
                            <button
                                type="button"
                                className="auth-button auth-button-secondary"
                            >
                                Sign Up
                            </button>
                        </a>
                    </div>
                </form>
            </div>
        </div>
    )
}

export default Login
