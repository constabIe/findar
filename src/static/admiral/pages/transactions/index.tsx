import React, { useState, useMemo } from 'react'
import { Page, Card, Button } from '@devfamily/admiral'

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
}

const Transactions: React.FC = () => {
    const [currentPage, setCurrentPage] = useState(1)

    const itemsPerPage = 10

    const allTransactions: Transaction[] = [
        {
            id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            amount: 1250.50,
            from_account: 'ACC-1001',
            to_account: 'ACC-2045',
            timestamp: '2025-10-23 14:30:15',
            type: 'TRANSFER',
            correlation_id: 'COR-2025-001',
            status: 'COMPLETED',
            currency: 'USD',
            description: 'Payment for services',
            merchant_id: 'MERCH-5001',
            location: 'New York, USA',
            device_id: 'DEV-001',
            ip_address: '192.168.1.1',
        },
        {
            id: 'b2c3d4e5-f6a7-8901-bcde-f23456789012',
            amount: 75.00,
            from_account: 'ACC-1002',
            to_account: 'ACC-2046',
            timestamp: '2025-10-23 15:45:30',
            type: 'PAYMENT',
            correlation_id: 'COR-2025-002',
            status: 'PENDING',
            currency: 'USD',
            description: 'Online purchase',
            merchant_id: 'MERCH-5002',
            location: 'Los Angeles, USA',
            device_id: 'DEV-002',
            ip_address: '192.168.1.2',
        },
        {
            id: 'c3d4e5f6-a7b8-9012-cdef-345678901234',
            amount: 3500.00,
            from_account: 'ACC-1003',
            to_account: 'ACC-2047',
            timestamp: '2025-10-23 16:20:45',
            type: 'WITHDRAWAL',
            correlation_id: 'COR-2025-003',
            status: 'FLAGGED',
            currency: 'EUR',
            description: 'Suspicious ATM withdrawal',
            merchant_id: 'MERCH-5003',
            location: 'London, UK',
            device_id: 'DEV-003',
            ip_address: '192.168.1.3',
        },
        {
            id: 'd4e5f6a7-b8c9-0123-def4-56789012345',
            amount: 150.75,
            from_account: 'ACC-1004',
            to_account: 'ACC-2048',
            timestamp: '2025-10-23 17:10:00',
            type: 'PAYMENT',
            correlation_id: 'COR-2025-004',
            status: 'COMPLETED',
            currency: 'USD',
            description: 'Restaurant payment',
            merchant_id: 'MERCH-5004',
            location: 'Chicago, USA',
            device_id: 'DEV-004',
            ip_address: '192.168.1.4',
        },
        {
            id: 'e5f6a7b8-c9d0-1234-ef56-789012345678',
            amount: 2200.00,
            from_account: 'ACC-1005',
            to_account: 'ACC-2049',
            timestamp: '2025-10-23 18:05:20',
            type: 'TRANSFER',
            correlation_id: 'COR-2025-005',
            status: 'FLAGGED',
            currency: 'GBP',
            description: 'Unusual international transfer',
            merchant_id: 'MERCH-5005',
            location: 'Paris, France',
            device_id: 'DEV-005',
            ip_address: '192.168.1.5',
        },
        {
            id: 'f6a7b8c9-d0e1-2345-f678-90123456789a',
            amount: 9999.99,
            from_account: 'ACC-1006',
            to_account: 'ACC-2050',
            timestamp: '2025-10-23 19:30:00',
            type: 'TRANSFER',
            correlation_id: 'COR-2025-006',
            status: 'FAILED',
            currency: 'USD',
            description: 'Wire transfer',
            merchant_id: 'MERCH-5006',
            location: 'Miami, USA',
            device_id: 'DEV-006',
            ip_address: '192.168.1.6',
        },
        {
            id: 'a1a1a1a1-b2b2-3c3c-d4d4-e5e5e5e5e5e5',
            amount: 450.00,
            from_account: 'ACC-1007',
            to_account: 'ACC-2051',
            timestamp: '2025-10-23 20:15:30',
            type: 'PAYMENT',
            correlation_id: 'COR-2025-007',
            status: 'COMPLETED',
            currency: 'USD',
            description: 'Hotel booking',
            merchant_id: 'MERCH-5007',
            location: 'Boston, USA',
            device_id: 'DEV-007',
            ip_address: '192.168.1.7',
        },
        {
            id: 'b2b2b2b2-c3c3-4d4d-e5e5-f6f6f6f6f6f6',
            amount: 825.50,
            from_account: 'ACC-1008',
            to_account: 'ACC-2052',
            timestamp: '2025-10-23 21:30:45',
            type: 'TRANSFER',
            correlation_id: 'COR-2025-008',
            status: 'PENDING',
            currency: 'EUR',
            description: 'Rent payment',
            merchant_id: 'MERCH-5008',
            location: 'Berlin, Germany',
            device_id: 'DEV-008',
            ip_address: '192.168.1.8',
        },
        {
            id: 'c3c3c3c3-d4d4-5e5e-f6f6-a7a7a7a7a7a7',
            amount: 125.25,
            from_account: 'ACC-1009',
            to_account: 'ACC-2053',
            timestamp: '2025-10-23 22:45:00',
            type: 'PAYMENT',
            correlation_id: 'COR-2025-009',
            status: 'COMPLETED',
            currency: 'USD',
            description: 'Grocery shopping',
            merchant_id: 'MERCH-5009',
            location: 'Seattle, USA',
            device_id: 'DEV-009',
            ip_address: '192.168.1.9',
        },
        {
            id: 'd4d4d4d4-e5e5-6f6f-a7a7-b8b8b8b8b8b8',
            amount: 5600.00,
            from_account: 'ACC-1010',
            to_account: 'ACC-2054',
            timestamp: '2025-10-24 08:00:15',
            type: 'WITHDRAWAL',
            correlation_id: 'COR-2025-010',
            status: 'FLAGGED',
            currency: 'USD',
            description: 'Large ATM withdrawal',
            merchant_id: 'MERCH-5010',
            location: 'Las Vegas, USA',
            device_id: 'DEV-010',
            ip_address: '192.168.1.10',
        },
        {
            id: 'e5e5e5e5-f6f6-7a7a-b8b8-c9c9c9c9c9c9',
            amount: 299.99,
            from_account: 'ACC-1011',
            to_account: 'ACC-2055',
            timestamp: '2025-10-24 09:20:30',
            type: 'PAYMENT',
            correlation_id: 'COR-2025-011',
            status: 'COMPLETED',
            currency: 'GBP',
            description: 'Electronics purchase',
            merchant_id: 'MERCH-5011',
            location: 'Manchester, UK',
            device_id: 'DEV-011',
            ip_address: '192.168.1.11',
        },
        {
            id: 'f6f6f6f6-a7a7-8b8b-c9c9-d0d0d0d0d0d0',
            amount: 1750.00,
            from_account: 'ACC-1012',
            to_account: 'ACC-2056',
            timestamp: '2025-10-24 10:45:45',
            type: 'TRANSFER',
            correlation_id: 'COR-2025-012',
            status: 'FAILED',
            currency: 'EUR',
            description: 'Investment transfer',
            merchant_id: 'MERCH-5012',
            location: 'Amsterdam, Netherlands',
            device_id: 'DEV-012',
            ip_address: '192.168.1.12',
        },
    ]

    const totalPages = Math.ceil(allTransactions.length / itemsPerPage)
    const paginatedTransactions = useMemo(() => {
        const startIndex = (currentPage - 1) * itemsPerPage
        return allTransactions.slice(startIndex, startIndex + itemsPerPage)
    }, [currentPage])

    const exportToCSV = () => {
        const headers = [
            'ID',
            'Amount',
            'From Account',
            'To Account',
            'Timestamp',
            'Type',
            'Status',
            'Currency',
            'Description',
            'Merchant ID',
            'Location',
            'Device ID',
            'IP Address',
        ]

        const csvContent = [
            headers.join(','),
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
                    t.ip_address,
                ].join(',')
            ),
        ].join('\n')

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)
        link.setAttribute('href', url)
        link.setAttribute('download', `transactions_${new Date().toISOString()}.csv`)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    return (
        <Page title="Transactions">
            <Card>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '2px solid #ddd' }}>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>ID</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Amount</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>From Account</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>To Account</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Timestamp</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Type</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Status</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Currency</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Description</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Merchant ID</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Location</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>Device ID</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left' }}>IP Address</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginatedTransactions.map((transaction) => (
                                <tr
                                    key={transaction.id}
                                    style={{
                                        borderBottom: '1px solid #eee',
                                        backgroundColor:
                                            transaction.status === 'FLAGGED'
                                                ? 'rgba(255, 152, 0, 0.15)'
                                                : 'transparent',
                                        borderLeft:
                                            transaction.status === 'FLAGGED'
                                                ? '4px solid #ff9800'
                                                : 'none',
                                    }}
                                >
                                    <td style={{ padding: '12px 8px', fontSize: '12px' }}>
                                        {transaction.id.substring(0, 8)}...
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>
                                        {transaction.amount.toFixed(2)}
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.from_account}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.to_account}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.timestamp}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.type}</td>
                                    <td style={{ padding: '12px 8px' }}>
                                        <span
                                            style={{
                                                padding: '4px 8px',
                                                borderRadius: '4px',
                                                fontSize: '12px',
                                                fontWeight:
                                                    transaction.status === 'FLAGGED' ? 'bold' : 'normal',
                                                backgroundColor:
                                                    transaction.status === 'COMPLETED'
                                                        ? '#d4edda'
                                                        : transaction.status === 'PENDING'
                                                        ? '#fff3cd'
                                                        : transaction.status === 'FLAGGED'
                                                        ? '#ff9800'
                                                        : '#f8d7da',
                                                color:
                                                    transaction.status === 'COMPLETED'
                                                        ? '#155724'
                                                        : transaction.status === 'PENDING'
                                                        ? '#856404'
                                                        : transaction.status === 'FLAGGED'
                                                        ? '#ffffff'
                                                        : '#721c24',
                                            }}
                                        >
                                            {transaction.status}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.currency}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.description}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.merchant_id}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.location}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.device_id}</td>
                                    <td style={{ padding: '12px 8px' }}>{transaction.ip_address}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <div
                    style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginTop: '20px',
                        flexWrap: 'wrap',
                        gap: '12px',
                    }}
                >
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <Button
                            onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                            disabled={currentPage === 1}
                        >
                            Previous
                        </Button>
                        <span style={{ padding: '0 12px' }}>
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
                        <span style={{ marginRight: '12px' }}>
                            Total: {allTransactions.length} transactions
                        </span>
                        <Button style={{marginTop: '12px'}} onClick={exportToCSV}>Export to CSV</Button>
                    </div>
                </div>
            </Card>
        </Page>
    )
}

export default Transactions
