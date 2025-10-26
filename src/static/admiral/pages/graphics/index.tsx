import React from "react"
import { Page, Card } from "@devfamily/admiral"

const Graphics: React.FC = () => {
  return (
    <Page title="Graphics">
      <Card>
        <h3>System Overview Dashboard</h3>
        <div style={{ width: "100%", height: "800px", border: "none" }}>
          <iframe
            src="http://localhost:3014/public-dashboards/4491f1be4d0a48aab440e8b3f1d6e512"
            width="100%"
            height="100%"
            frameBorder="0"
            title="Grafana Dashboard"
          />
        </div>
      </Card>
    </Page>
  )
}

export default Graphics
