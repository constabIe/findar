import React from "react"
import { Page, Card } from "@devfamily/admiral"

const Graphics: React.FC = () => {
  return (
    <Page title="Graphics">
      <Card>
        <h3>System Overview Dashboard</h3>
        <div style={{ width: "100%", height: "800px", border: "none" }}>
          <iframe
            src="http://localhost:3000/grafana/public-dashboards/bb70f78eeba7467c879ecce7e89bcc7d"
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
