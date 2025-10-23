import React, { useState, useMemo } from 'react'
import { Page, Card, Button, Form, Input, Select, Switch } from '@devfamily/admiral'

interface Rule {
    id: string
    name: string
    type: string
    params: Record<string, any>
    enabled: boolean
    priority: number
    critical: boolean
    description: string
    created_by: string
    created_at: string
    updated_at: string
    execution_count: number
    match_count: number
    last_executed_at: string
    average_execution_time_ms: number
    apply: boolean
}

const Rules: React.FC = () => {
    const [currentPage, setCurrentPage] = useState(1)
    const [ruleStates, setRuleStates] = useState<Record<string, boolean>>({})
    const [selectedType, setSelectedType] = useState<string | null>('THRESHOLD')
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [newRuleType, setNewRuleType] = useState('THRESHOLD')
    const [newRuleName, setNewRuleName] = useState('')
    const [newRuleDescription, setNewRuleDescription] = useState('')
    const [newRuleEnabled, setNewRuleEnabled] = useState(true)
    const [newRulePriority, setNewRulePriority] = useState(5)
    const [newRuleCritical, setNewRuleCritical] = useState(false)
    const [newRuleCreatedBy, setNewRuleCreatedBy] = useState('admin')
    const [newRuleParams, setNewRuleParams] = useState<Record<string, any>>({})

    const itemsPerPage = 10

    const allRules: Rule[] = [
        {
            id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            name: 'High Amount Transfer',
            type: 'THRESHOLD',
            params: { amount_limit: 5000, currency: 'USD' },
            enabled: true,
            priority: 10,
            critical: true,
            description: 'Detects transfers exceeding $5000',
            created_by: 'admin',
            created_at: '2025-10-01 10:00:00',
            updated_at: '2025-10-15 14:30:00',
            execution_count: 1523,
            match_count: 87,
            last_executed_at: '2025-10-23 12:45:00',
            average_execution_time_ms: 45.2,
            apply: true,
        },
        {
            id: 'b2c3d4e5-f6a7-8901-bcde-f23456789012',
            name: 'Rapid Transaction Pattern',
            type: 'PATTERN',
            params: { time_window: 300, min_transactions: 5 },
            enabled: true,
            priority: 8,
            critical: false,
            description: 'Flags multiple transactions within 5 minutes',
            created_by: 'security_team',
            created_at: '2025-09-15 09:20:00',
            updated_at: '2025-10-10 11:00:00',
            execution_count: 2340,
            match_count: 134,
            last_executed_at: '2025-10-23 13:10:00',
            average_execution_time_ms: 67.8,
            apply: true,
        },
        {
            id: 'c3d4e5f6-a7b8-9012-cdef-345678901234',
            name: 'Unusual Location Check',
            type: 'PATTERN',
            params: { distance_km: 500, time_window: 3600 },
            enabled: true,
            priority: 7,
            critical: false,
            description: 'Detects transactions from geographically distant locations',
            created_by: 'fraud_analyst',
            created_at: '2025-08-20 15:30:00',
            updated_at: '2025-10-05 16:45:00',
            execution_count: 987,
            match_count: 23,
            last_executed_at: '2025-10-23 11:20:00',
            average_execution_time_ms: 89.3,
            apply: false,
        },
        {
            id: 'd4e5f6a7-b8c9-0123-def4-567890123456',
            name: 'ML Fraud Score',
            type: 'ML',
            params: { model_version: 'v2.1', threshold: 0.75 },
            enabled: true,
            priority: 9,
            critical: true,
            description: 'Machine learning based fraud detection',
            created_by: 'ml_team',
            created_at: '2025-09-01 08:00:00',
            updated_at: '2025-10-20 09:15:00',
            execution_count: 3456,
            match_count: 201,
            last_executed_at: '2025-10-23 13:45:00',
            average_execution_time_ms: 156.7,
            apply: true,
        },
        {
            id: 'e5f6a7b8-c9d0-1234-ef56-789012345678',
            name: 'Off-Hours Activity',
            type: 'PATTERN',
            params: { start_hour: 2, end_hour: 5, timezone: 'UTC' },
            enabled: true,
            priority: 5,
            critical: false,
            description: 'Monitors transactions during unusual hours',
            created_by: 'security_team',
            created_at: '2025-07-10 12:00:00',
            updated_at: '2025-09-25 14:30:00',
            execution_count: 1789,
            match_count: 56,
            last_executed_at: '2025-10-23 03:15:00',
            average_execution_time_ms: 34.5,
            apply: true,
        },
        {
            id: 'f6a7b8c9-d0e1-2345-f678-90123456789a',
            name: 'Composite Risk Assessment',
            type: 'COMPOSITE',
            params: { rule_ids: ['a1b2c3d4', 'b2c3d4e5', 'c3d4e5f6'], operator: 'AND' },
            enabled: true,
            priority: 6,
            critical: false,
            description: 'Combines multiple rules for comprehensive check',
            created_by: 'admin',
            created_at: '2025-10-10 10:30:00',
            updated_at: '2025-10-18 11:45:00',
            execution_count: 654,
            match_count: 12,
            last_executed_at: '2025-10-23 12:00:00',
            average_execution_time_ms: 123.4,
            apply: false,
        },
        {
            id: 'a1a1a1a1-b2b2-3c3c-d4d4-e5e5e5e5e5e5',
            name: 'New Account Activity',
            type: 'THRESHOLD',
            params: { account_age_days: 7, transaction_limit: 1000 },
            enabled: false,
            priority: 4,
            critical: false,
            description: 'Monitors transactions from newly created accounts',
            created_by: 'fraud_analyst',
            created_at: '2025-06-15 09:00:00',
            updated_at: '2025-10-01 10:15:00',
            execution_count: 432,
            match_count: 18,
            last_executed_at: '2025-10-15 14:30:00',
            average_execution_time_ms: 41.2,
            apply: false,
        },
        {
            id: 'b2b2b2b2-c3c3-4d4d-e5e5-f6f6f6f6f6f6',
            name: 'Currency Conversion Pattern',
            type: 'PATTERN',
            params: { conversion_count: 3, time_window: 1800 },
            enabled: true,
            priority: 5,
            critical: false,
            description: 'Detects multiple currency conversions in short period',
            created_by: 'security_team',
            created_at: '2025-08-05 11:20:00',
            updated_at: '2025-10-12 13:00:00',
            execution_count: 876,
            match_count: 34,
            last_executed_at: '2025-10-23 10:40:00',
            average_execution_time_ms: 52.8,
            apply: true,
        },
        {
            id: 'c3c3c3c3-d4d4-5e5e-f6f6-a7a7a7a7a7a7',
            name: 'Merchant Category Risk',
            type: 'THRESHOLD',
            params: { high_risk_categories: ['gambling', 'crypto'], amount_limit: 1000 },
            enabled: true,
            priority: 7,
            critical: true,
            description: 'Monitors transactions with high-risk merchants',
            created_by: 'compliance_team',
            created_at: '2025-09-20 14:45:00',
            updated_at: '2025-10-19 15:30:00',
            execution_count: 1234,
            match_count: 67,
            last_executed_at: '2025-10-23 13:20:00',
            average_execution_time_ms: 58.9,
            apply: true,
        },
        {
            id: 'd4d4d4d4-e5e5-6f6f-a7a7-b8b8b8b8b8b8',
            name: 'Velocity Check',
            type: 'PATTERN',
            params: { daily_limit: 10000, weekly_limit: 50000 },
            enabled: true,
            priority: 8,
            critical: false,
            description: 'Tracks transaction velocity over time periods',
            created_by: 'risk_management',
            created_at: '2025-07-25 10:10:00',
            updated_at: '2025-10-08 11:25:00',
            execution_count: 2567,
            match_count: 145,
            last_executed_at: '2025-10-23 13:50:00',
            average_execution_time_ms: 78.6,
            apply: true,
        },
        {
            id: 'e5e5e5e5-f6f6-7a7a-b8b8-c9c9c9c9c9c9',
            name: 'Device Fingerprint Mismatch',
            type: 'PATTERN',
            params: { check_device_history: true, threshold: 0.8 },
            enabled: true,
            priority: 6,
            critical: false,
            description: 'Detects unusual device usage patterns',
            created_by: 'fraud_analyst',
            created_at: '2025-08-30 13:15:00',
            updated_at: '2025-10-14 14:50:00',
            execution_count: 1890,
            match_count: 92,
            last_executed_at: '2025-10-23 12:30:00',
            average_execution_time_ms: 64.3,
            apply: false,
        },
        {
            id: 'f6f6f6f6-a7a7-8b8b-c9c9-d0d0d0d0d0d0',
            name: 'IP Reputation Check',
            type: 'THRESHOLD',
            params: { blacklist_check: true, reputation_score_min: 0.5 },
            enabled: false,
            priority: 3,
            critical: false,
            description: 'Validates IP address against reputation databases',
            created_by: 'security_team',
            created_at: '2025-06-01 08:30:00',
            updated_at: '2025-09-15 09:45:00',
            execution_count: 567,
            match_count: 28,
            last_executed_at: '2025-10-10 16:20:00',
            average_execution_time_ms: 95.1,
            apply: true,
        },
    ]

    const handleToggleRule = (ruleId: string, currentValue: boolean) => {
        setRuleStates((prev) => ({
            ...prev,
            [ruleId]: !currentValue,
        }))
    }

    const getRuleApplyState = (ruleId: string, defaultValue: boolean) => {
        return ruleStates[ruleId] !== undefined ? ruleStates[ruleId] : defaultValue
    }

    const filteredRules = useMemo(() => {
        if (!selectedType) return []
        return allRules.filter((rule) => rule.type === selectedType)
    }, [selectedType])

    const totalPages = Math.ceil(filteredRules.length / itemsPerPage)
    const paginatedRules = useMemo(() => {
        const startIndex = (currentPage - 1) * itemsPerPage
        return filteredRules.slice(startIndex, startIndex + itemsPerPage)
    }, [currentPage, filteredRules])

    const handleTypeSelect = (type: string) => {
        setSelectedType(type)
        setCurrentPage(1)
    }

    const handleOpenModal = () => {
        setIsModalOpen(true)
        setNewRuleType('THRESHOLD')
        setNewRuleName('')
        setNewRuleDescription('')
        setNewRuleEnabled(true)
        setNewRulePriority(5)
        setNewRuleCritical(false)
        setNewRuleCreatedBy('admin')
        setNewRuleParams({})
    }

    const handleCloseModal = () => {
        setIsModalOpen(false)
    }

    const handleRuleTypeChange = (value: string) => {
        setNewRuleType(value)
        setNewRuleParams({})
    }

    const handleSaveRule = () => {
        console.log('Saving rule:', {
            name: newRuleName,
            type: newRuleType,
            description: newRuleDescription,
            enabled: newRuleEnabled,
            priority: newRulePriority,
            critical: newRuleCritical,
            created_by: newRuleCreatedBy,
            params: newRuleParams,
        })
        handleCloseModal()
    }

    const exportToCSV = () => {
        const headers = [
            'ID',
            'Name',
            'Type',
            'Params',
            'Enabled',
            'Priority',
            'Critical',
            'Description',
            'Created By',
            'Created At',
            'Updated At',
            'Execution Count',
            'Match Count',
            'Last Executed At',
            'Avg Execution Time (ms)',
        ]

        const csvContent = [
            headers.join(','),
            ...allRules.map((r) =>
                [
                    r.id,
                    `"${r.name}"`,
                    r.type,
                    `"${JSON.stringify(r.params).replace(/"/g, '""')}"`,
                    r.enabled,
                    r.priority,
                    r.critical,
                    `"${r.description}"`,
                    r.created_by,
                    r.created_at,
                    r.updated_at,
                    r.execution_count,
                    r.match_count,
                    r.last_executed_at,
                    r.average_execution_time_ms,
                ].join(',')
            ),
        ].join('\n')

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)
        link.setAttribute('href', url)
        link.setAttribute('download', `rules_${new Date().toISOString()}.csv`)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    return (
        <Page title="Rules">
            <Card>
                <div style={{ marginBottom: '24px' }}>
                    <div
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: '12px',
                            padding: '16px',
                            backgroundColor: '#2d3748',
                            borderRadius: '8px',
                            flexWrap: 'wrap',
                        }}
                    >
                        <div style={{
                            display: 'flex',
                            gap: '12px',
                            flexWrap: 'wrap',
                        }}>
                        <Button
                            onClick={() => handleTypeSelect('THRESHOLD')}
                            style={{
                                backgroundColor: selectedType === 'THRESHOLD' ? '#1565c0' : '#4a5568',
                                color: '#ffffff',
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'THRESHOLD' ? 'bold' : 'normal',
                            }}
                        >
                            Threshold
                        </Button>
                        <Button
                            onClick={() => handleTypeSelect('PATTERN')}
                            style={{
                                backgroundColor: selectedType === 'PATTERN' ? '#1565c0' : '#4a5568',
                                color: '#ffffff',
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'PATTERN' ? 'bold' : 'normal',
                            }}
                        >
                            Pattern
                        </Button>
                        <Button
                            onClick={() => handleTypeSelect('ML')}
                            style={{
                                backgroundColor: selectedType === 'ML' ? '#1565c0' : '#4a5568',
                                color: '#ffffff',
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'ML' ? 'bold' : 'normal',
                            }}
                        >
                            ML
                        </Button>
                        <Button
                            onClick={() => handleTypeSelect('COMPOSITE')}
                            style={{
                                backgroundColor: selectedType === 'COMPOSITE' ? '#1565c0' : '#4a5568',
                                color: '#ffffff',
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'COMPOSITE' ? 'bold' : 'normal',
                            }}
                        >
                            Composite
                        </Button>
                        </div>
                    <div>
                    <Button
                        onClick={handleOpenModal}
                        style={{
                            backgroundColor: '#1565c0',
                            color: '#ffffff',
                            padding: '10px 20px',
                            fontWeight: 'bold',
                            border: 'none',
                        }}
                    >
                        ADD RULE
                    </Button>
                    </div>
                    </div>
                </div>

                {selectedType && (
                    <>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid #ddd' }}>
                                        <th style={{ padding: '12px 8px', textAlign: 'center' }}>Apply rule</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>ID</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Name</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Params</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Enabled</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Priority</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Critical</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Description</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Created By</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Created At</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Updated At</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Execution Count</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Match Count</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Last Executed</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Avg Time (ms)</th>
                                    </tr>
                                </thead>
                        <tbody>
                            {paginatedRules.map((rule) => (
                                <tr
                                    key={rule.id}
                                    style={{
                                        borderBottom: '1px solid #eee',
                                    }}
                                >
                                    <td style={{ padding: '12px 8px', textAlign: 'center' }}>
                                        <label style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer' }}>
                                            <input
                                                type="checkbox"
                                                checked={getRuleApplyState(rule.id, rule.apply)}
                                                onChange={() => handleToggleRule(rule.id, getRuleApplyState(rule.id, rule.apply))}
                                                style={{
                                                    width: '40px',
                                                    height: '20px',
                                                    appearance: 'none',
                                                    backgroundColor: getRuleApplyState(rule.id, rule.apply) ? '#4caf50' : '#ccc',
                                                    borderRadius: '10px',
                                                    position: 'relative',
                                                    cursor: 'pointer',
                                                    transition: 'background-color 0.3s',
                                                    outline: 'none',
                                                }}
                                            />
                                            <style>
                                                {`
                                                    input[type="checkbox"]::before {
                                                        content: '';
                                                        position: absolute;
                                                        width: 16px;
                                                        height: 16px;
                                                        border-radius: 50%;
                                                        background-color: white;
                                                        top: 2px;
                                                        left: 2px;
                                                        transition: transform 0.3s;
                                                    }
                                                    input[type="checkbox"]:checked::before {
                                                        transform: translateX(20px);
                                                    }
                                                `}
                                            </style>
                                        </label>
                                    </td>
                                    <td style={{ padding: '12px 8px', fontSize: '12px' }}>
                                        {rule.id.substring(0, 8)}...
                                    </td>
                                    <td style={{ padding: '12px 8px', fontWeight: 'bold' }}>{rule.name}</td>
                                    <td style={{ padding: '12px 8px', fontSize: '11px', maxWidth: '150px' }}>
                                        <pre
                                            style={{
                                                margin: 0,
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap',
                                            }}
                                        >
                                            {JSON.stringify(rule.params)}
                                        </pre>
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>
                                        <span
                                            style={{
                                                padding: '4px 8px',
                                                borderRadius: '4px',
                                                fontSize: '12px',
                                                backgroundColor: rule.enabled ? '#d4edda' : '#f8d7da',
                                                color: rule.enabled ? '#155724' : '#721c24',
                                            }}
                                        >
                                            {rule.enabled ? 'Yes' : 'No'}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 8px', textAlign: 'center' }}>
                                        <span
                                            style={{
                                                padding: '4px 8px',
                                                borderRadius: '50%',
                                                fontSize: '12px',
                                                fontWeight: 'bold',
                                                backgroundColor:
                                                    rule.priority >= 8
                                                        ? '#f44336'
                                                        : rule.priority >= 5
                                                        ? '#ff9800'
                                                        : '#4caf50',
                                                color: '#ffffff',
                                            }}
                                        >
                                            {rule.priority}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>
                                        <span
                                            style={{
                                                padding: '4px 8px',
                                                borderRadius: '4px',
                                                fontSize: '12px',
                                                fontWeight: rule.critical ? 'bold' : 'normal',
                                                backgroundColor: rule.critical ? '#f44336' : '#e0e0e0',
                                                color: rule.critical ? '#ffffff' : '#424242',
                                            }}
                                        >
                                            {rule.critical ? 'Yes' : 'No'}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 8px', maxWidth: '200px' }}>
                                        {rule.description}
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>{rule.created_by}</td>
                                    <td style={{ padding: '12px 8px', fontSize: '12px' }}>
                                        {rule.created_at}
                                    </td>
                                    <td style={{ padding: '12px 8px', fontSize: '12px' }}>
                                        {rule.updated_at}
                                    </td>
                                    <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                                        {rule.execution_count.toLocaleString()}
                                    </td>
                                    <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                                        <span
                                            style={{
                                                padding: '4px 8px',
                                                borderRadius: '4px',
                                                fontSize: '12px',
                                                backgroundColor:
                                                    rule.match_count > 100
                                                        ? '#ffebee'
                                                        : rule.match_count > 50
                                                        ? '#fff3e0'
                                                        : '#f1f8e9',
                                                color:
                                                    rule.match_count > 100
                                                        ? '#c62828'
                                                        : rule.match_count > 50
                                                        ? '#ef6c00'
                                                        : '#558b2f',
                                            }}
                                        >
                                            {rule.match_count.toLocaleString()}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 8px', fontSize: '12px' }}>
                                        {rule.last_executed_at}
                                    </td>
                                    <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                                        {rule.average_execution_time_ms.toFixed(1)}
                                    </td>
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
                            Total: {filteredRules.length} rules
                        </span>
                    </div>
                </div>
                    </>
                )}
            </Card>

            {isModalOpen && (
                <div
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(0, 0, 0, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 1000,
                    }}
                    onClick={handleCloseModal}
                >
                    <div
                        style={{
                            backgroundColor: '#ffffff',
                            padding: '32px',
                            borderRadius: '8px',
                            maxWidth: '600px',
                            width: '90%',
                            maxHeight: '90vh',
                            overflowY: 'auto',
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h2 style={{ marginTop: 0, marginBottom: '24px' }}>Add New Rule</h2>

                        <Form>
                            <Form.Item label="Rule Name" required>
                                <Input
                                    value={newRuleName}
                                    onChange={(e: any) => setNewRuleName(e.target.value)}
                                    placeholder="Enter rule name"
                                />
                            </Form.Item>

                            <Form.Item label="Rule Type" required>
                                <Select
                                    value={newRuleType}
                                    onChange={handleRuleTypeChange}
                                    style={{ width: '100%' }}
                                >
                                    <Select.Option value="THRESHOLD">Threshold</Select.Option>
                                    <Select.Option value="PATTERN">Pattern</Select.Option>
                                    <Select.Option value="ML">ML</Select.Option>
                                    <Select.Option value="COMPOSITE">Composite</Select.Option>
                                </Select>
                            </Form.Item>

                            <Form.Item label="Description">
                                <Input
                                    value={newRuleDescription}
                                    onChange={(e: any) => setNewRuleDescription(e.target.value)}
                                    placeholder="Enter rule description"
                                />
                            </Form.Item>

                            {newRuleType === 'THRESHOLD' && (
                                <>
                                    <Form.Item label="Amount Limit">
                                        <Input
                                            type="number"
                                            value={newRuleParams.amount_limit || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    amount_limit: parseFloat(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 5000"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Currency">
                                        <Input
                                            value={newRuleParams.currency || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    currency: e.target.value,
                                                })
                                            }
                                            placeholder="e.g., USD"
                                        />
                                    </Form.Item>
                                </>
                            )}

                            {newRuleType === 'PATTERN' && (
                                <>
                                    <Form.Item label="Time Window (seconds)">
                                        <Input
                                            type="number"
                                            value={newRuleParams.time_window || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    time_window: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 300"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Minimum Transactions">
                                        <Input
                                            type="number"
                                            value={newRuleParams.min_transactions || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    min_transactions: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 5"
                                        />
                                    </Form.Item>
                                </>
                            )}

                            {newRuleType === 'ML' && (
                                <>
                                    <Form.Item label="Model Version">
                                        <Input
                                            value={newRuleParams.model_version || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    model_version: e.target.value,
                                                })
                                            }
                                            placeholder="e.g., v2.1"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Threshold (0.0 - 1.0)">
                                        <Input
                                            type="number"
                                            step="0.01"
                                            value={newRuleParams.threshold || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    threshold: parseFloat(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 0.75"
                                        />
                                    </Form.Item>
                                </>
                            )}

                            {newRuleType === 'COMPOSITE' && (
                                <>
                                    <Form.Item label="Rule IDs (comma-separated)">
                                        <Input
                                            value={newRuleParams.rule_ids?.join(', ') || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    rule_ids: e.target.value.split(',').map((id: string) => id.trim()),
                                                })
                                            }
                                            placeholder="e.g., a1b2c3d4, b2c3d4e5"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Operator">
                                        <Select
                                            value={newRuleParams.operator || 'AND'}
                                            onChange={(value: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    operator: value,
                                                })
                                            }
                                            style={{ width: '100%' }}
                                        >
                                            <Select.Option value="AND">AND</Select.Option>
                                            <Select.Option value="OR">OR</Select.Option>
                                        </Select>
                                    </Form.Item>
                                </>
                            )}

                            <Form.Item label="Priority">
                                <Input
                                    type="number"
                                    value={newRulePriority}
                                    onChange={(e: any) => setNewRulePriority(parseInt(e.target.value))}
                                    placeholder="e.g., 5"
                                />
                            </Form.Item>

                            <Form.Item label="Created By">
                                <Input
                                    value={newRuleCreatedBy}
                                    onChange={(e: any) => setNewRuleCreatedBy(e.target.value)}
                                    placeholder="Enter creator name"
                                />
                            </Form.Item>

                            <Form.Item>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Switch checked={newRuleEnabled} onChange={setNewRuleEnabled} />
                                    <span>Enabled</span>
                                </div>
                            </Form.Item>

                            <Form.Item>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Switch checked={newRuleCritical} onChange={setNewRuleCritical} />
                                    <span>Critical</span>
                                </div>
                            </Form.Item>

                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
                                <Button onClick={handleCloseModal} style={{ padding: '8px 16px' }}>
                                    Cancel
                                </Button>
                                <Button
                                    onClick={handleSaveRule}
                                    style={{
                                        backgroundColor: '#1565c0',
                                        color: '#ffffff',
                                        padding: '8px 16px',
                                        border: 'none',
                                    }}
                                >
                                    Save Rule
                                </Button>
                            </div>
                        </Form>
                    </div>
                </div>
            )}
        </Page>
    )
}

export default Rules
