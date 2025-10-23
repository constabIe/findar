import React from 'react'
import { Menu, MenuItemLink } from '@devfamily/admiral'

const CustomMenu = () => {
    return (
        <Menu>
            <MenuItemLink name="Transactions" to="/transactions" icon="FiCreditCard" />
            <MenuItemLink name="Rules" to="/rules" icon="FiSettings" />
            <MenuItemLink name="Profile" to="/profile" icon="FiUser" />
            <MenuItemLink name="Graphics" to="/graphics" icon="FiBarChart2" />
        </Menu>
    )
}

export default CustomMenu
