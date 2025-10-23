import React from 'react'
import { Menu, MenuItemLink } from '@devfamily/admiral'

const CustomMenu = () => {
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
            
            <div style={{ 
                marginTop: 'auto', 
                padding: '16px', 
                borderTop: '1px solid rgba(0, 0, 0, 0.1)' 
            }}>
                <button 
                    onClick={handleLogout}
                    style={{
                        width: '100%',
                        padding: '12px',
                        backgroundColor: 'rgba(0, 0, 0, 0.05)',
                        border: 'none',
                        borderRadius: '8px',
                        color: '#333',
                        cursor: 'pointer',
                        fontSize: '14px',
                        fontWeight: '500',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        transition: 'background-color 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.1)'
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.05)'
                    }}
                >
                    <span>🚪</span>
                    Logout
                </button>
            </div>
        </Menu>
    )
}

export default CustomMenu
