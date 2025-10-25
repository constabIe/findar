import React, { useState, useMemo, useEffect } from "react"
import { Page, Card, Button, Form, Input, Switch } from "@devfamily/admiral"
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

interface Notification {
  id: number
  message: string
  type: "success" | "error"
}

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
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false)
  const [transactionToReview, setTransactionToReview] = useState<Transaction | null>(null)
  const [reviewStatus, setReviewStatus] = useState(true) // true = accepted, false = rejected
  const [reviewComment, setReviewComment] = useState("")
  const [submittingReview, setSubmittingReview] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])

  const itemsPerPage = 10

  const showNotification = (message: string, type: "success" | "error") => {
    const id = Date.now()
    setNotifications((prev) => [...prev, { id, message, type }])

    // Auto-remove notification after 3 seconds
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id))
    }, 3000)
  }

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
      showNotification("Transaction created with test status for review feature", "success")
    } catch (err: any) {
      showNotification(err.response?.data?.detail || "Failed to create transaction.", "error")
      console.error("Error creating transaction:", err)
    } finally {
      setCreating(false)
    }
  }

  const handleOpenReviewModal = (transaction: Transaction) => {
    setTransactionToReview(transaction)
    setReviewStatus(true) // Default to accepted
    setReviewComment("")
    setIsReviewModalOpen(true)
  }

  const handleCloseReviewModal = () => {
    setIsReviewModalOpen(false)
    setTransactionToReview(null)
    setReviewStatus(true)
    setReviewComment("")
  }

  const handleSubmitReview = async () => {
    if (!transactionToReview) return

    try {
      setSubmittingReview(true)

      const token = localStorage.getItem("admiral_global_admin_session_token")

      if (!token) {
        showNotification("No authentication token found. Please login again.", "error")
        return
      }

      await axios.post(
        `${API_URL}/transactions/${transactionToReview.id}/review`,
        {
          status: reviewStatus ? "accepted" : "rejected",
          comment: reviewComment
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        }
      )

      // Update the transaction in the local state
      setAllTransactions((prev) =>
        prev.map((t) =>
          t.id === transactionToReview.id
            ? { ...t, status: reviewStatus ? "APPROVED" : "REJECTED" }
            : t
        )
      )

      showNotification(
        `Transaction ${reviewStatus ? "accepted" : "rejected"} successfully!`,
        "success"
      )

      handleCloseReviewModal()
    } catch (err: any) {
      showNotification(err.response?.data?.detail || "Failed to submit review.", "error")
      console.error("Error submitting review:", err)
    } finally {
      setSubmittingReview(false)
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
      {/* Notifications */}
      <div
        style={{
          position: "fixed",
          top: "20px",
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          minWidth: "300px",
          maxWidth: "500px"
        }}
      >
        {notifications.map((notification) => (
          <div
            key={notification.id}
            style={{
              backgroundColor: notification.type === "success" ? "#2d3e2f" : "#4a2828",
              color: "#ffffff",
              padding: "16px 20px",
              borderRadius: "8px",
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              animation: "slideIn 0.3s ease-out"
            }}
          >
            <div
              style={{
                width: "24px",
                height: "24px",
                borderRadius: "50%",
                backgroundColor: notification.type === "success" ? "#4caf50" : "#f44336",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0
              }}
            >
              {notification.type === "success" ? "✓" : "✕"}
            </div>
            <span style={{ flex: 1 }}>{notification.message}</span>
            <button
              onClick={() =>
                setNotifications((prev) => prev.filter((n) => n.id !== notification.id))
              }
              style={{
                background: "none",
                border: "none",
                color: "#ffffff",
                cursor: "pointer",
                fontSize: "20px",
                padding: 0,
                width: "20px",
                height: "20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <Card>
        <style>
          {`
            @keyframes slideIn {
              from {
                transform: translateY(-20px);
                opacity: 0;
              }
              to {
                transform: translateY(0);
                opacity: 1;
              }
            }
          `}
        </style>
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
                      onClick={() => {
                        if (
                          transaction.status.toUpperCase() === "FLAGGED" ||
                          transaction.status.toUpperCase() === "FAILED"
                        ) {
                          handleOpenReviewModal(transaction)
                        }
                      }}
                      style={{
                        borderBottom: "1px solid #eee",
                        backgroundColor:
                          transaction.status.toUpperCase() === "FLAGGED"
                            ? "rgba(255, 152, 0, 0.15)"
                            : "transparent",
                        borderLeft: transaction.status.toUpperCase() === "FLAGGED" ? "4px solid #ff9800" : "none",
                        cursor:
                          transaction.status.toUpperCase() === "FLAGGED" || transaction.status.toUpperCase() === "FAILED"
                            ? "pointer"
                            : "default",
                        transition: "background-color 0.2s"
                      }}
                      onMouseEnter={(e) => {
                        if (
                          transaction.status.toUpperCase() === "FLAGGED" ||
                          transaction.status.toUpperCase() === "FAILED"
                        ) {
                          e.currentTarget.style.backgroundColor = "rgba(255, 152, 0, 0.25)"
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor =
                          transaction.status.toUpperCase() === "FLAGGED"
                            ? "rgba(255, 152, 0, 0.15)"
                            : "transparent"
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
                            fontWeight: transaction.status.toUpperCase() === "FLAGGED" ? "bold" : "normal",
                            backgroundColor:
                              transaction.status.toUpperCase() === "COMPLETED" || transaction.status.toUpperCase() === "APPROVED"
                                ? "#d4edda"
                                : transaction.status.toUpperCase() === "PENDING"
                                  ? "#fff3cd"
                                  : transaction.status.toUpperCase() === "FLAGGED"
                                    ? "#ff9800"
                                    : "#f8d7da",
                            color:
                              transaction.status.toUpperCase() === "COMPLETED" || transaction.status.toUpperCase() === "APPROVED"
                                ? "#155724"
                                : transaction.status.toUpperCase() === "PENDING"
                                  ? "#856404"
                                  : transaction.status.toUpperCase() === "FLAGGED"
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

      {/* Review Modal */}
      {isReviewModalOpen && transactionToReview && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000
          }}
          onClick={handleCloseReviewModal}
        >
          <div
            style={{
              backgroundColor: "var(--color-bg-default)",
              color: "var(--color-typo-primary)",
              padding: "32px",
              borderRadius: "8px",
              maxWidth: "500px",
              width: "90%",
              maxHeight: "90vh",
              overflowY: "auto"
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0, marginBottom: "24px", color: "var(--color-typo-primary)" }}>
              Review Transaction
            </h2>

            <div style={{ marginBottom: "16px" }}>
              <p style={{ margin: "4px 0" }}>
                <strong>Transaction ID:</strong> {transactionToReview.id}
              </p>
              <p style={{ margin: "4px 0" }}>
                <strong>Amount:</strong> {transactionToReview.currency}{" "}
                {transactionToReview.amount.toFixed(2)}
              </p>
              <p style={{ margin: "4px 0" }}>
                <strong>From:</strong> {transactionToReview.from_account}
              </p>
              <p style={{ margin: "4px 0" }}>
                <strong>To:</strong> {transactionToReview.to_account}
              </p>
              <p style={{ margin: "4px 0" }}>
                <strong>Status:</strong> {transactionToReview.status}
              </p>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSubmitReview()
              }}
            >
              <Form.Item label="Decision" required>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontWeight: reviewStatus ? "normal" : "bold" }}>Reject</span>
                  <Switch checked={reviewStatus} onChange={(checked) => setReviewStatus(checked)} />
                  <span style={{ fontWeight: reviewStatus ? "bold" : "normal" }}>Accept</span>
                </div>
              </Form.Item>

              <Form.Item label="Comment" required>
                <Input
                  value={reviewComment}
                  onChange={(e: any) => setReviewComment(e.target.value)}
                  placeholder="Enter your review comment"
                  required
                />
              </Form.Item>

              <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end", marginTop: "24px" }}>
                <Button
                  type="button"
                  onClick={handleCloseReviewModal}
                  style={{
                    padding: "10px 20px"
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={submittingReview || !reviewComment.trim()}
                  style={{
                    padding: "10px 20px",
                    backgroundColor: reviewStatus ? "#4caf50" : "#f44336",
                    color: "#ffffff"
                  }}
                >
                  {submittingReview ? "Submitting..." : reviewStatus ? "Accept" : "Reject"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Page>
  )
}

export default Transactions
