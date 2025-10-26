import React from "react"
import { Page, Card } from "@devfamily/admiral"

const Home: React.FC = () => {
  return (
    <Page title="Welcome to the Findar project!">
      <Card>
        <h2>Findar</h2>
        <p>
          Findar is a lightweight admin interface to manage rules, show transactions and monitor the
          fraud detection system.
        </p>
      </Card>
    </Page>
  )
}

export default Home
