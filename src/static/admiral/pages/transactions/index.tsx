import React, { useState, useMemo, useEffect } from "react"
import { Page, Card, Button } from "@devfamily/admiral"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

interface Transaction {
  id: string
  amount: number
  from_account: string
  to_account: string
  timestamp: string
  type: string
  correlation_id: string
  status: string
  currency: string
  description: string
  merchant_id: string
  location: string
  device_id: string
  ip_address: string
  created_at: string
  updated_at: string
}

interface TransactionsResponse {
  transactions: Transaction[]
  count: number
  limit: number
}

const Transactions: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(1)
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [creating, setCreating] = useState(false)

  const itemsPerPage = 10

  useEffect(() => {
    fetchTransactions()
  }, [])

  const fetchTransactions = async () => {
    try {
      setLoading(true)
      setError("")

      const token = localStorage.getItem("admiral_global_admin_session_token")

      if (!token) {
        setError("No authentication token found. Please login again.")
        setLoading(false)
        return
      }

      const response = await axios.get<TransactionsResponse>(`${API_URL}/transactions`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      setAllTransactions(response.data.transactions || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load transactions.")
      console.error("Error fetching transactions:", err)
    } finally {
      setLoading(false)
    }
  }

  const createTransaction = async () => {
    try {
      setCreating(true)
      setError("")

      const token = localStorage.getItem("admiral_global_admin_session_token")

      if (!token) {
        setError("No authentication token found. Please login again.")
        setCreating(false)
        return
      }

      const randomAmount = Math.floor(Math.random() * 5000) + 10
      const randomAccountFrom = `ACC-${Math.floor(Math.random() * 9000) + 1000}`
      const randomAccountTo = `ACC-${Math.floor(Math.random() * 9000) + 1000}`
      const types = ["TRANSFER", "PAYMENT", "WITHDRAWAL"]
      const randomType = types[Math.floor(Math.random() * types.length)]
      const currencies = ["USD", "EUR", "GBP"]
      const randomCurrency = currencies[Math.floor(Math.random() * currencies.length)]
      const descriptions = [
        "Payment for services",
        "Online purchase",
        "ATM withdrawal",
        "Restaurant payment",
        "Hotel booking"
      ]
      const randomDescription = descriptions[Math.floor(Math.random() * descriptions.length)]
      const locations = [
        "New York, USA",
        "London, UK",
        "Paris, France",
        "Berlin, Germany",
        "Tokyo, Japan"
      ]
      const randomLocation = locations[Math.floor(Math.random() * locations.length)]

      await axios.post(
        `${API_URL}/transactions`,
        {
          amount: randomAmount,
          from_account: randomAccountFrom,
          to_account: randomAccountTo,
          type: randomType,
          currency: randomCurrency,
          description: randomDescription,
          merchant_id: `MERCH-${Math.floor(Math.random() * 9000) + 1000}`,
          location: randomLocation,
          device_id: `DEV-${Math.floor(Math.random() * 900) + 100}`,
          ip_address: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      )

      await fetchTransactions()
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create transaction.")
      console.error("Error creating transaction:", err)
    } finally {
      setCreating(false)
    }
  }

  const totalPages = Math.ceil(allTransactions.length / itemsPerPage)
  const paginatedTransactions = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return allTransactions.slice(startIndex, startIndex + itemsPerPage)
  }, [currentPage, allTransactions])

  const exportToCSV = () => {
    const headers = [
      "ID",
      "Amount",
      "From Account",
      "To Account",
      "Timestamp",
      "Type",
      "Status",
      "Currency",
      "Description",
      "Merchant ID",
      "Location",
      "Device ID",
      "IP Address"
    ]

    const csvContent = [
      headers.join(","),
      ...allTransactions.map((t) =>
        [
          t.id,
          t.amount,
          t.from_account,
          t.to_account,
          t.timestamp,
          t.type,
          t.status,
          t.currency,
          `"${t.description}"`,
          t.merchant_id,
          `"${t.location}"`,
          t.device_id,
          t.ip_address
        ].join(",")
      )
    ].join("\n")

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const link = document.createElement("a")
    const url = URL.createObjectURL(blob)
    link.setAttribute("href", url)
    link.setAttribute("download", `transactions_${new Date().toISOString()}.csv`)
    link.style.visibility = "hidden"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <Page title="Transactions">
      <Card>
        {loading ? (
          <div style={{ padding: "20px", textAlign: "center" }}>Loading transactions...</div>
        ) : error ? (
          <div style={{ padding: "20px", color: "red" }}>{error}</div>
        ) : (
          <>
            <div style={{ marginBottom: "20px" }}>
              <Button onClick={createTransaction} disabled={creating}>
                {creating ? "Creating..." : "Create New Transaction"}
              </Button>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid #ddd" }}>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>ID</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Amount</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>From Account</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>To Account</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Timestamp</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Type</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Status</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Currency</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Description</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Merchant ID</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Location</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>Device ID</th>
                    <th style={{ padding: "12px 8px", textAlign: "left" }}>IP Address</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedTransactions.map((transaction) => (
                    <tr
                      key={transaction.id}
                      style={{
                        borderBottom: "1px solid #eee",
                        backgroundColor:
                          transaction.status === "FLAGGED"
                            ? "rgba(255, 152, 0, 0.15)"
                            : "transparent",
                        borderLeft: transaction.status === "FLAGGED" ? "4px solid #ff9800" : "none"
                      }}
                    >
                      <td style={{ padding: "12px 8px", fontSize: "12px" }}>
                        {transaction.id.substring(0, 8)}...
                      </td>
                      <td style={{ padding: "12px 8px" }}>{transaction.amount.toFixed(2)}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.from_account}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.to_account}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.timestamp}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.type}</td>
                      <td style={{ padding: "12px 8px" }}>
                        <span
                          style={{
                            padding: "4px 8px",
                            borderRadius: "4px",
                            fontSize: "12px",
                            fontWeight: transaction.status === "FLAGGED" ? "bold" : "normal",
                            backgroundColor:
                              transaction.status === "COMPLETED"
                                ? "#d4edda"
                                : transaction.status === "PENDING"
                                  ? "#fff3cd"
                                  : transaction.status === "FLAGGED"
                                    ? "#ff9800"
                                    : "#f8d7da",
                            color:
                              transaction.status === "COMPLETED"
                                ? "#155724"
                                : transaction.status === "PENDING"
                                  ? "#856404"
                                  : transaction.status === "FLAGGED"
                                    ? "#ffffff"
                                    : "#721c24"
                          }}
                        >
                          {transaction.status}
                        </span>
                      </td>
                      <td style={{ padding: "12px 8px" }}>{transaction.currency}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.description}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.merchant_id}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.location}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.device_id}</td>
                      <td style={{ padding: "12px 8px" }}>{transaction.ip_address}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "20px",
                flexWrap: "wrap",
                gap: "12px"
              }}
            >
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <Button
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <span style={{ padding: "0 12px" }}>
                  Page {currentPage} of {totalPages || 1}
                </span>
                <Button
                  onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages || totalPages === 0}
                >
                  Next
                </Button>
              </div>
              <div>
                <span style={{ marginRight: "12px" }}>
                  Total: {allTransactions.length} transactions
                </span>
                <Button style={{ marginTop: "12px" }} onClick={exportToCSV}>
                  Export to CSV
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </Page>
  )
}

export default Transactions
