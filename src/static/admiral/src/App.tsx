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

  useEffect(() => {
    const handleLocationChange = () => {
      setCurrentPath(window.location.pathname)
    }

    window.addEventListener("popstate", handleLocationChange)
    return () => window.removeEventListener("popstate", handleLocationChange)
  }, [])

  // Render auth pages without Admin layout
  if (currentPath === "/login") {
    return <Login />
  }

  if (currentPath === "/signup") {
    return <SignUp />
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
