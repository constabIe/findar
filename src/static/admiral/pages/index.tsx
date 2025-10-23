import React from 'react'
import { Page, Card } from '@devfamily/admiral'

const Home: React.FC = () => {
    return (
        <Page title="Welcome">
            <Card>
                <h2>Admin Panel</h2>
                <p>Use the sidebar menu to navigate between sections:</p>
                <ul>
                    <li>Transactions</li>
                    <li>Rules</li>
                    <li>Profile</li>
                    <li>Graphics</li>
                </ul>
            </Card>
        </Page>
    )
}

export default Home
