import React from "react"
import { Page, Card } from "@devfamily/admiral"

const Graphics: React.FC = () => {
  return (
    <Page title="Graphics">
      <Card>
        <h3>System Overview Dashboard</h3>
        <div style={{ width: "100%", height: "800px", border: "none" }}>
          <iframe
            src="http://localhost:3000/grafana/public-dashboards/b0e8ea5f83984b09a0777c4162941e2c"
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
