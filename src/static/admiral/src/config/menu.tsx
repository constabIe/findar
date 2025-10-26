import React, { useEffect, useState } from "react"
import { Menu, MenuItemLink } from "@devfamily/admiral"
import "../../assets/menu.scss"

const CustomMenu = () => {
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    // Check theme on mount and listen for changes
    const checkTheme = () => {
      const htmlElement = document.documentElement
      const bodyElement = document.body
      const isDarkTheme =
        htmlElement.getAttribute("data-theme") === "dark" ||
        bodyElement.classList.contains("dark") ||
        htmlElement.classList.contains("dark") ||
        bodyElement.getAttribute("data-theme") === "dark"
      setIsDark(isDarkTheme)
    }

    checkTheme()

    // Observer for theme changes
    const observer = new MutationObserver(checkTheme)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme", "class"]
    })
    observer.observe(document.body, { attributes: true, attributeFilter: ["data-theme", "class"] })

    return () => observer.disconnect()
  }, [])

<<<<<<< HEAD
  const handleLogout = () => {
    // Clear authentication token
    localStorage.removeItem("admiral_global_admin_session_token")
    // Redirect to login page
    window.location.href = "/login"
  }

=======
>>>>>>> 9d7e7d9c862ca0ddbfbb724981d065be1dc9bd39
  return (
    <Menu>
      <MenuItemLink name="Transactions" to="/transactions" icon="FiCreditCard" />
      <MenuItemLink name="Rules" to="/rules" icon="FiSettings" />
      <MenuItemLink name="Profile" to="/profile" icon="FiUser" />
      <MenuItemLink name="Notifications" to="/notifications" icon="FiBell" />
      <MenuItemLink name="Graphics" to="/graphics" icon="FiBarChart2" />
    </Menu>
  )
}

export default CustomMenu
