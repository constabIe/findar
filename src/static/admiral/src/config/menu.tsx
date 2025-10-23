import React, { useEffect, useState } from 'react'
import { Menu, MenuItemLink } from '@devfamily/admiral'
import '../../assets/menu.scss'

const CustomMenu = () => {
    const [isDark, setIsDark] = useState(false)

    useEffect(() => {
        // Check theme on mount and listen for changes
        const checkTheme = () => {
            const htmlElement = document.documentElement
            const bodyElement = document.body
            const isDarkTheme = 
                htmlElement.getAttribute('data-theme') === 'dark' ||
                bodyElement.classList.contains('dark') ||
                htmlElement.classList.contains('dark') ||
                bodyElement.getAttribute('data-theme') === 'dark'
            setIsDark(isDarkTheme)
        }

        checkTheme()

        // Observer for theme changes
        const observer = new MutationObserver(checkTheme)
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] })
        observer.observe(document.body, { attributes: true, attributeFilter: ['data-theme', 'class'] })

        return () => observer.disconnect()
    }, [])

    const handleLogout = () => {
        // Demo mode - redirect to login page
        window.location.href = '/login'
    }

    return (
        <Menu>
            <MenuItemLink name="Transactions" to="/transactions" icon="FiCreditCard" />
            <MenuItemLink name="Rules" to="/rules" icon="FiSettings" />
            <MenuItemLink name="Profile" to="/profile" icon="FiUser" />
            <MenuItemLink name="Graphics" to="/graphics" icon="FiBarChart2" />
            
            <div style={{ marginTop: 'auto' }} onClick={handleLogout}>
                <MenuItemLink 
                    name="Logout" 
                    to="/login" 
                    icon="FiLogOut"
                />
            </div>
        </Menu>
    )
}

export default CustomMenu
