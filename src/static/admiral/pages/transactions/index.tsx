import React from 'react'
import { Page, Card } from '@devfamily/admiral'

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
    const mockTransactions: Transaction[] = [
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
    ]

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
                            {mockTransactions.map((transaction) => (
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
            </Card>
        </Page>
    )
}

export default Transactions
