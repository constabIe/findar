import React, { useState, useEffect } from 'react'
import '../assets/auth.scss'

const Login: React.FC = () => {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [theme, setTheme] = useState<'light' | 'dark'>('light')

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

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        // Demo mode - just navigate to main page
        window.location.href = '/'
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
                        />
                    </div>

                    <button type="submit" className="auth-button auth-button-primary">
                        Login
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
