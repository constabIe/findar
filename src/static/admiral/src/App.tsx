import React from 'react'
import { Admin, createRoutesFrom } from '@devfamily/admiral'
import menu from './config/menu'
import dataProvider from './config/dataProvider'
import authProvider from './config/authProvider'
import '@devfamily/admiral/style.css'
// import themeLight from './config/theme/themeLight'
// import themeDark from './config/theme/themeDark'

const apiUrl = import.meta.env.VITE_API_URL || '/api'
const Routes = createRoutesFrom(import.meta.globEager('../pages/**/*'))

function App() {
    return (
        <Admin
            dataProvider={dataProvider(apiUrl)}
            authProvider={authProvider(apiUrl)}
            menu={menu}
            // themePresets={{ light: themeLight, dark: themeDark }}
        >
            <Routes />
        </Admin>
    )
}

export default App
