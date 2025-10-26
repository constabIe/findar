import React, { useEffect, useState } from "react"
import { Admin, createRoutesFrom } from "@devfamily/admiral"
import menu from "./config/menu"
import dataProvider from "./config/dataProvider"
import authProvider from "./config/authProvider"
import "@devfamily/admiral/style.css"
import themeLight from "./config/theme/themeLight"
import themeDark from "./config/theme/themeDark"
import Login from "../pages/login"
import SignUp from "../pages/signup"

const apiUrl = import.meta.env.VITE_API_URL || "/api"
const Routes = createRoutesFrom(import.meta.globEager("../pages/**/*"))

function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check authentication status
    const token = localStorage.getItem("admiral_global_admin_session_token")
    setIsAuthenticated(!!token)
    setIsLoading(false)
  }, [])

  useEffect(() => {
    const handleLocationChange = () => {
      setCurrentPath(window.location.pathname)
    }

    window.addEventListener("popstate", handleLocationChange)
    return () => window.removeEventListener("popstate", handleLocationChange)
  }, [])

  // Show loading state while checking authentication
  if (isLoading) {
    return <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>Loading...</div>
  }

  // Render auth pages without Admin layout
  if (currentPath === "/login") {
    // If already authenticated, redirect to home
    if (isAuthenticated) {
      window.location.href = "/"
      return null
    }
    return <Login />
  }

  if (currentPath === "/signup") {
    // If already authenticated, redirect to home
    if (isAuthenticated) {
      window.location.href = "/"
      return null
    }
    return <SignUp />
  }

  // Protected routes - require authentication
  if (!isAuthenticated) {
    window.location.href = "/login"
    return null
  }

  return (
    <Admin
      dataProvider={dataProvider(apiUrl)}
      authProvider={authProvider(apiUrl)}
      menu={menu}
      themePresets={{ light: themeLight, dark: themeDark }}
    >
      <Routes />
    </Admin>
  )
}

export default App
