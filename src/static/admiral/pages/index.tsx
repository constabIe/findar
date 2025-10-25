import React from "react"
import { Page, Card } from "@devfamily/admiral"

const Home: React.FC = () => {
  return (
    <Page title="Welcome to the Findar project!">
      <Card>
        <h2>Admin Panel</h2>
        <p>Use the sidebar menu to navigate between sections</p>
      </Card>
    </Page>
  )
}

export default Home
