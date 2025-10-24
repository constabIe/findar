import React, { useState, useMemo, useEffect } from 'react'
import { Page, Card, Button, Form, Input, Select, Switch } from '@devfamily/admiral'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface Notification {
    id: number
    message: string
    type: 'success' | 'error'
}

interface Rule {
    id: string
    name: string
    type: string
    params: Record<string, any>
    enabled: boolean
    priority: number
    critical: boolean
    description: string
    created_by_user_id: string
    execution_count: number
    match_count: number
    created_at: string
    updated_at: string
}

interface RulesResponse {
    rules: Rule[]
}

const Rules: React.FC = () => {
    const [currentPage, setCurrentPage] = useState(1)
    const [ruleStates, setRuleStates] = useState<Record<string, boolean>>({})
    const [selectedType, setSelectedType] = useState<string | null>('threshold')
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [newRuleType, setNewRuleType] = useState('threshold')
    const [newRuleName, setNewRuleName] = useState('')
    const [newRuleDescription, setNewRuleDescription] = useState('')
    const [newRuleEnabled, setNewRuleEnabled] = useState(true)
    const [newRulePriority, setNewRulePriority] = useState(5)
    const [newRuleCritical, setNewRuleCritical] = useState(false)
    const [newRuleParams, setNewRuleParams] = useState<Record<string, any>>({})
    const [allRules, setAllRules] = useState<Rule[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [notifications, setNotifications] = useState<Notification[]>([])

    const itemsPerPage = 10

    const showNotification = (message: string, type: 'success' | 'error') => {
        const id = Date.now()
        setNotifications(prev => [...prev, { id, message, type }])
        
        // Auto-remove notification after 3 seconds
        setTimeout(() => {
            setNotifications(prev => prev.filter(n => n.id !== id))
        }, 3000)
    }

    useEffect(() => {
        if (selectedType) {
            fetchRules(selectedType)
        }
    }, [selectedType])

    const fetchRules = async (ruleType: string) => {
        try {
            setLoading(true)
            setError('')
            
            const token = localStorage.getItem('admiral_global_admin_session_token')
            
            if (!token) {
                setError('No authentication token found. Please login again.')
                setLoading(false)
                return
            }

            const response = await axios.get<Rule[]>(`${API_URL}/rules/type/${ruleType}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            setAllRules(response.data || [])
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load rules.')
            console.error('Error fetching rules:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleToggleRule = async (ruleId: string, currentValue: boolean) => {
        try {
            const token = localStorage.getItem('admiral_global_admin_session_token')
            
            if (!token) {
                showNotification('No authentication token found. Please login again.', 'error')
                return
            }

            // Determine the endpoint based on current state
            // If currently enabled (true), we want to deactivate, otherwise activate
            const endpoint = currentValue 
                ? `${API_URL}/rules/${ruleId}/deactivate`
                : `${API_URL}/rules/${ruleId}/activate`

            // Make POST request to activate or deactivate
            await axios.post(endpoint, {}, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            // Update local state after successful request
            setRuleStates((prev) => ({
                ...prev,
                [ruleId]: !currentValue,
            }))

            showNotification(`Rule ${currentValue ? 'deactivated' : 'activated'} successfully!`, 'success')
        } catch (err: any) {
            console.error('Error toggling rule:', err)
            showNotification(err.response?.data?.detail || 'Failed to toggle rule.', 'error')
        }
    }

    const getRuleApplyState = (ruleId: string, defaultValue: boolean) => {
        return ruleStates[ruleId] !== undefined ? ruleStates[ruleId] : defaultValue
    }

    const filteredRules = useMemo(() => {
        // Filter rules by selected type
        if (!selectedType) return []
        return allRules.filter(rule => rule.type === selectedType)
    }, [allRules, selectedType])

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
        setNewRuleType('threshold')
        setNewRuleName('')
        setNewRuleDescription('')
        setNewRuleEnabled(true)
        setNewRulePriority(5)
        setNewRuleCritical(false)
        setNewRuleParams({})
    }

    const handleCloseModal = () => {
        setIsModalOpen(false)
    }

    const handleRuleTypeChange = (value: string) => {
        setNewRuleType(value)
        setNewRuleParams({})
    }

    const handleSaveRule = async () => {
        // Validate required fields BEFORE try-catch
        const token = localStorage.getItem('admiral_global_admin_session_token')
        
        if (!token) {
            showNotification('No authentication token found. Please login again.', 'error')
            return
        }

        if (!newRuleName || newRuleName.trim() === '') {
            showNotification('Rule Name is required.', 'error')
            return
        }

        // Validate type-specific required fields
        if (newRuleType === 'pattern') {
            if (!newRuleParams.period || newRuleParams.period === '') {
                showNotification('Period is required for Pattern rules.', 'error')
                return
            }
        } else if (newRuleType === 'composite') {
            if (!newRuleParams.rules || newRuleParams.rules.length === 0) {
                showNotification('Rules field is required for Composite rules.', 'error')
                return
            }
        }

        try {
            // Filter params based on rule type
            let filteredParams: Record<string, any> = {}

            if (newRuleType === 'threshold') {
                // Only include threshold-specific parameters
                const thresholdKeys = [
                    'max_amount',
                    'min_amount',
                    'operator',
                    'time_window',
                    'allowed_hours_start',
                    'allowed_hours_end',
                    'allowed_locations',
                    'max_devices_per_account',
                    'max_ips_per_account',
                    'max_velocity_amount',
                    'max_transaction_types',
                    'max_transactions_per_account',
                    'max_transactions_to_account',
                    'max_transactions_per_ip'
                ]
                thresholdKeys.forEach(key => {
                    if (newRuleParams[key] !== undefined && newRuleParams[key] !== '' && newRuleParams[key] !== null) {
                        filteredParams[key] = newRuleParams[key]
                    }
                })
            } else if (newRuleType === 'pattern') {
                // Only include pattern-specific parameters
                const patternKeys = [
                    'period',
                    'count',
                    'amount_ceiling',
                    'same_recipient',
                    'unique_recipients',
                    'same_device',
                    'velocity_limit'
                ]
                patternKeys.forEach(key => {
                    if (newRuleParams[key] !== undefined && newRuleParams[key] !== '' && newRuleParams[key] !== null) {
                        filteredParams[key] = newRuleParams[key]
                    }
                })
            } else if (newRuleType === 'composite') {
                // Only include composite-specific parameters
                const compositeKeys = [
                    'composite_operator',
                    'rules'
                ]
                compositeKeys.forEach(key => {
                    if (newRuleParams[key] !== undefined && newRuleParams[key] !== '' && newRuleParams[key] !== null) {
                        filteredParams[key] = newRuleParams[key]
                    }
                })
            } else if (newRuleType === 'ml') {
                // Only include ML-specific parameters
                const mlKeys = [
                    'model_version',
                    'threshold',
                    'endpoint_url'
                ]
                mlKeys.forEach(key => {
                    if (newRuleParams[key] !== undefined && newRuleParams[key] !== '' && newRuleParams[key] !== null) {
                        filteredParams[key] = newRuleParams[key]
                    }
                })
            }

            // Build the request payload
            const payload = {
                name: newRuleName,
                type: newRuleType,
                params: filteredParams,
                enabled: newRuleEnabled,
                priority: newRulePriority,
                critical: newRuleCritical,
                description: newRuleDescription,
            }

            // POST request to create new rule
            await axios.post(`${API_URL}/rules`, payload, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })

            showNotification('Rule created successfully!', 'success')

            // Refresh the rules list after successful creation
            if (selectedType) {
                await fetchRules(selectedType)
            }

            handleCloseModal()
        } catch (err: any) {
            console.error('Error saving rule:', err)
            showNotification(err.response?.data?.detail || 'Failed to save rule.', 'error')
        }
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
            'Created By User ID',
            'Created At',
            'Updated At',
            'Execution Count',
            'Match Count',
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
                    r.created_by_user_id,
                    r.created_at,
                    r.updated_at,
                    r.execution_count,
                    r.match_count,
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
            {/* Notification Container */}
            <div style={{
                position: 'fixed',
                top: '20px',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: 9999,
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                minWidth: '300px',
                maxWidth: '500px',
            }}>
                {notifications.map(notification => (
                    <div
                        key={notification.id}
                        style={{
                            backgroundColor: notification.type === 'success' ? '#2d3e2f' : '#4a2828',
                            color: '#ffffff',
                            padding: '16px 20px',
                            borderRadius: '8px',
                            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            animation: 'slideIn 0.3s ease-out',
                        }}
                    >
                        <div style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            backgroundColor: notification.type === 'success' ? '#4caf50' : '#f44336',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                        }}>
                            {notification.type === 'success' ? '✓' : '✕'}
                        </div>
                        <span style={{ flex: 1 }}>{notification.message}</span>
                        <button
                            onClick={() => setNotifications(prev => prev.filter(n => n.id !== notification.id))}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: '#ffffff',
                                cursor: 'pointer',
                                fontSize: '20px',
                                padding: 0,
                                width: '20px',
                                height: '20px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
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

                        .modal-content {
                            background-color: var(--color-bg-default);
                            color: var(--color-typo-primary);
                        }
                        
                        .modal-content h2 {
                            color: var(--color-typo-primary);
                        }
                        
                        .nav-panel {
                            background-color: var(--color-bg-secondary);
                        }
                        
                        .nav-btn-active {
                            background-color: var(--color-control-bg-primary) !important;
                            color: var(--color-control-typo-primary) !important;
                        }
                        
                        .nav-btn-inactive {
                            background-color: var(--color-control-bg-ghost) !important;
                            color: var(--color-control-typo-ghost) !important;
                        }
                    `}
                </style>
                <div style={{ marginBottom: '24px' }}>
                    <div
                        className="nav-panel"
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: '12px',
                            padding: '16px',
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
                            onClick={() => handleTypeSelect('threshold')}
                            className={selectedType === 'threshold' ? 'nav-btn-active' : 'nav-btn-inactive'}
                            style={{
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'threshold' ? 'bold' : 'normal',
                            }}
                        >
                            Threshold
                        </Button>
                        <Button
                            onClick={() => handleTypeSelect('composite')}
                            className={selectedType === 'composite' ? 'nav-btn-active' : 'nav-btn-inactive'}
                            style={{
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'composite' ? 'bold' : 'normal',
                            }}
                        >
                            Composite
                        </Button>
                        <Button
                            onClick={() => handleTypeSelect('pattern')}
                            className={selectedType === 'pattern' ? 'nav-btn-active' : 'nav-btn-inactive'}
                            style={{
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'pattern' ? 'bold' : 'normal',
                            }}
                        >
                            Pattern
                        </Button>
                        <Button
                            onClick={() => handleTypeSelect('ml')}
                            className={selectedType === 'ml' ? 'nav-btn-active' : 'nav-btn-inactive'}
                            style={{
                                border: 'none',
                                padding: '10px 20px',
                                fontWeight: selectedType === 'ml' ? 'bold' : 'normal',
                            }}
                        >
                            ML
                        </Button>
                        </div>
                    <div>
                    <Button
                        onClick={handleOpenModal}
                        style={{
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
                        {loading ? (
                            <div style={{ padding: '20px', textAlign: 'center' }}>Loading rules...</div>
                        ) : error ? (
                            <div style={{ padding: '20px', color: 'red' }}>{error}</div>
                        ) : (
                            <>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid #ddd' }}>
                                        <th style={{ padding: '12px 8px', textAlign: 'center' }}>Apply rule</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>ID</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Name</th>
                                        
                                        {/* ALL possible parameter columns across all types */}
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max Amount</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Min Amount</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Operator</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Time Window</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Allowed Hours Start</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Allowed Hours End</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Allowed Locations</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max Devices/Account</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max IPs/Account</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max Velocity Amount</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max Transaction Types</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max Transactions/Account</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max Transactions to Account</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Max Transactions/IP</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Period</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Count</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Amount Ceiling</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Same Recipient</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Unique Recipients</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Same Device</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Velocity Limit</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Composite Operator</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Rules</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Model Version</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Threshold</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Endpoint URL</th>
                                        
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Enabled</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Priority</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Critical</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Description</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Created By</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Created At</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Updated At</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Execution Count</th>
                                        <th style={{ padding: '12px 8px', textAlign: 'left' }}>Match Count</th>
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
                                                checked={getRuleApplyState(rule.id, rule.enabled)}
                                                onChange={() => handleToggleRule(rule.id, getRuleApplyState(rule.id, rule.enabled))}
                                                style={{
                                                    width: '40px',
                                                    height: '20px',
                                                    appearance: 'none',
                                                    backgroundColor: getRuleApplyState(rule.id, rule.enabled) ? '#4caf50' : '#ccc',
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
                                    
                                    {/* ALL possible parameter columns - show "-" for missing values */}
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_amount || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.min_amount || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.operator || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.time_window || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.allowed_hours_start || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.allowed_hours_end || '-'}</td>
                                    <td style={{ padding: '12px 8px', maxWidth: '150px' }}>
                                        {rule.params.allowed_locations ? 
                                            (Array.isArray(rule.params.allowed_locations) ? 
                                                rule.params.allowed_locations.join(', ') : 
                                                rule.params.allowed_locations) : 
                                            '-'}
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_devices_per_account || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_ips_per_account || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_velocity_amount || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_transaction_types || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_transactions_per_account || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_transactions_to_account || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.max_transactions_per_ip || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.period || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.count || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.amount_ceiling || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>
                                        {rule.params.same_recipient !== undefined ? 
                                            <span
                                                style={{
                                                    padding: '4px 8px',
                                                    borderRadius: '4px',
                                                    fontSize: '12px',
                                                    backgroundColor: rule.params.same_recipient ? '#d4edda' : '#f8d7da',
                                                    color: rule.params.same_recipient ? '#155724' : '#721c24',
                                                }}
                                            >
                                                {rule.params.same_recipient ? 'Yes' : 'No'}
                                            </span>
                                            : '-'}
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.unique_recipients || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>
                                        {rule.params.same_device !== undefined ? 
                                            <span
                                                style={{
                                                    padding: '4px 8px',
                                                    borderRadius: '4px',
                                                    fontSize: '12px',
                                                    backgroundColor: rule.params.same_device ? '#d4edda' : '#f8d7da',
                                                    color: rule.params.same_device ? '#155724' : '#721c24',
                                                }}
                                            >
                                                {rule.params.same_device ? 'Yes' : 'No'}
                                            </span>
                                            : '-'}
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.velocity_limit || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>
                                        {rule.params.composite_operator ? 
                                            <span
                                                style={{
                                                    padding: '4px 8px',
                                                    borderRadius: '4px',
                                                    fontSize: '12px',
                                                    fontWeight: 'bold',
                                                    backgroundColor: rule.params.composite_operator === 'AND' ? '#e3f2fd' : 
                                                                    rule.params.composite_operator === 'OR' ? '#fff3e0' : '#ffebee',
                                                    color: rule.params.composite_operator === 'AND' ? '#1565c0' : 
                                                           rule.params.composite_operator === 'OR' ? '#ef6c00' : '#c62828',
                                                }}
                                            >
                                                {rule.params.composite_operator}
                                            </span>
                                            : '-'}
                                    </td>
                                    <td style={{ padding: '12px 8px', maxWidth: '200px' }}>
                                        {rule.params.rules ? 
                                            (Array.isArray(rule.params.rules) ? 
                                                rule.params.rules.join(', ') : 
                                                rule.params.rules) : 
                                            '-'}
                                    </td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.model_version || '-'}</td>
                                    <td style={{ padding: '12px 8px' }}>{rule.params.threshold || '-'}</td>
                                    <td style={{ padding: '12px 8px', maxWidth: '200px', fontSize: '11px' }}>
                                        {rule.params.endpoint_url || '-'}
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
                                    <td style={{ padding: '12px 8px' }}>{rule.created_by_user_id}</td>
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
                        className="modal-content"
                        style={{
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

                        <form onSubmit={(e) => { e.preventDefault(); handleSaveRule(); }}>
                            <div>
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
                                    <Select.Option value="threshold">Threshold</Select.Option>
                                    <Select.Option value="pattern">Pattern</Select.Option>
                                    <Select.Option value="composite">Composite</Select.Option>
                                    <Select.Option value="ml">ML</Select.Option>
                                </Select>
                            </Form.Item>

                            <Form.Item label="Description">
                                <Input
                                    value={newRuleDescription}
                                    onChange={(e: any) => setNewRuleDescription(e.target.value)}
                                    placeholder="Enter rule description"
                                />
                            </Form.Item>

                            {newRuleType === 'threshold' && (
                                <>
                                    <Form.Item label="Max Amount">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_amount || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_amount: parseFloat(e.target.value),
                                                })
                                            }
                                            placeholder="Maximum amount"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Min Amount">
                                        <Input
                                            type="number"
                                            value={newRuleParams.min_amount || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    min_amount: parseFloat(e.target.value),
                                                })
                                            }
                                            placeholder="Minimum amount"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Operator">
                                        <Select
                                            value={newRuleParams.operator || ''}
                                            onChange={(value: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    operator: value,
                                                })
                                            }
                                            style={{ width: '100%' }}
                                        >
                                            <Select.Option value="gt">Greater Than (gt)</Select.Option>
                                            <Select.Option value="lt">Less Than (lt)</Select.Option>
                                            <Select.Option value="eq">Equal (eq)</Select.Option>
                                            <Select.Option value="gte">Greater Than or Equal (gte)</Select.Option>
                                            <Select.Option value="lte">Less Than or Equal (lte)</Select.Option>
                                            <Select.Option value="ne">Not Equal (ne)</Select.Option>
                                            <Select.Option value="between">Between</Select.Option>
                                            <Select.Option value="not_between">Not Between</Select.Option>
                                        </Select>
                                    </Form.Item>
                                    <Form.Item label="Time Window">
                                        <Select
                                            value={newRuleParams.time_window || ''}
                                            onChange={(value: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    time_window: value,
                                                })
                                            }
                                            style={{ width: '100%' }}
                                        >
                                            <Select.Option value="1m">1 Minute</Select.Option>
                                            <Select.Option value="5m">5 Minutes</Select.Option>
                                            <Select.Option value="10m">10 Minutes</Select.Option>
                                            <Select.Option value="15m">15 Minutes</Select.Option>
                                            <Select.Option value="30m">30 Minutes</Select.Option>
                                            <Select.Option value="1h">1 Hour</Select.Option>
                                            <Select.Option value="6h">6 Hours</Select.Option>
                                            <Select.Option value="12h">12 Hours</Select.Option>
                                            <Select.Option value="1d">1 Day</Select.Option>
                                            <Select.Option value="1w">1 Week</Select.Option>
                                            <Select.Option value="1M">1 Month</Select.Option>
                                        </Select>
                                    </Form.Item>
                                    <Form.Item label="Allowed Hours Start">
                                        <Input
                                            type="number"
                                            value={newRuleParams.allowed_hours_start || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    allowed_hours_start: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 9 (9 AM)"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Allowed Hours End">
                                        <Input
                                            type="number"
                                            value={newRuleParams.allowed_hours_end || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    allowed_hours_end: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 17 (5 PM)"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Allowed Locations (comma-separated)">
                                        <Input
                                            value={newRuleParams.allowed_locations?.join(', ') || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    allowed_locations: e.target.value.split(',').map((loc: string) => loc.trim()).filter(Boolean),
                                                })
                                            }
                                            placeholder="e.g., US, UK, CA"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Max Devices per Account">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_devices_per_account || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_devices_per_account: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 5"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Max IPs per Account">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_ips_per_account || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_ips_per_account: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 3"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Max Velocity Amount">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_velocity_amount || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_velocity_amount: parseFloat(e.target.value),
                                                })
                                            }
                                            placeholder="Limit of sum transfer in period"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Max Transaction Types">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_transaction_types || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_transaction_types: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 5"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Max Transactions per Account">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_transactions_per_account || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_transactions_per_account: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 100"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Max Transactions to Account">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_transactions_to_account || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_transactions_to_account: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 50"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Max Transactions per IP">
                                        <Input
                                            type="number"
                                            value={newRuleParams.max_transactions_per_ip || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    max_transactions_per_ip: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="e.g., 10"
                                        />
                                    </Form.Item>
                                </>
                            )}

                            {newRuleType === 'pattern' && (
                                <>
                                    <Form.Item label="Period (required)" required>
                                        <Select
                                            value={newRuleParams.period || ''}
                                            onChange={(value: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    period: value,
                                                })
                                            }
                                            style={{ width: '100%' }}
                                        >
                                            <Select.Option value="1m">1 Minute</Select.Option>
                                            <Select.Option value="5m">5 Minutes</Select.Option>
                                            <Select.Option value="10m">10 Minutes</Select.Option>
                                            <Select.Option value="15m">15 Minutes</Select.Option>
                                            <Select.Option value="30m">30 Minutes</Select.Option>
                                            <Select.Option value="1h">1 Hour</Select.Option>
                                            <Select.Option value="6h">6 Hours</Select.Option>
                                            <Select.Option value="12h">12 Hours</Select.Option>
                                            <Select.Option value="1d">1 Day</Select.Option>
                                            <Select.Option value="1w">1 Week</Select.Option>
                                            <Select.Option value="1M">1 Month</Select.Option>
                                        </Select>
                                    </Form.Item>
                                    <Form.Item label="Count">
                                        <Input
                                            type="number"
                                            value={newRuleParams.count || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    count: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="Number of transactions in the period"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Amount Ceiling">
                                        <Input
                                            type="number"
                                            value={newRuleParams.amount_ceiling || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    amount_ceiling: parseFloat(e.target.value),
                                                })
                                            }
                                            placeholder="Maximum sum of transactions in period"
                                        />
                                    </Form.Item>
                                    <Form.Item>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <Switch 
                                                checked={newRuleParams.same_recipient || false} 
                                                onChange={(checked: boolean) =>
                                                    setNewRuleParams({
                                                        ...newRuleParams,
                                                        same_recipient: checked,
                                                    })
                                                } 
                                            />
                                            <span>Same Recipient (all transactions to one recipient)</span>
                                        </div>
                                    </Form.Item>
                                    <Form.Item label="Unique Recipients">
                                        <Input
                                            type="number"
                                            value={newRuleParams.unique_recipients || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    unique_recipients: parseInt(e.target.value),
                                                })
                                            }
                                            placeholder="Max number of unique recipients in period"
                                        />
                                    </Form.Item>
                                    <Form.Item>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <Switch 
                                                checked={newRuleParams.same_device || false} 
                                                onChange={(checked: boolean) =>
                                                    setNewRuleParams({
                                                        ...newRuleParams,
                                                        same_device: checked,
                                                    })
                                                } 
                                            />
                                            <span>Same Device (all transactions from one device)</span>
                                        </div>
                                    </Form.Item>
                                    <Form.Item label="Velocity Limit">
                                        <Input
                                            type="number"
                                            value={newRuleParams.velocity_limit || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    velocity_limit: parseFloat(e.target.value),
                                                })
                                            }
                                            placeholder="Max sum of transactions from one device in period"
                                        />
                                    </Form.Item>
                                </>
                            )}

                            {newRuleType === 'ml' && (
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
                                    <Form.Item label="Endpoint URL">
                                        <Input
                                            value={newRuleParams.endpoint_url || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    endpoint_url: e.target.value,
                                                })
                                            }
                                            placeholder="https://api.example.com/ml/predict"
                                        />
                                    </Form.Item>
                                </>
                            )}

                            {newRuleType === 'composite' && (
                                <>
                                    <Form.Item label="Composite Operator">
                                        <Select
                                            value={newRuleParams.composite_operator || 'AND'}
                                            onChange={(value: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    composite_operator: value,
                                                })
                                            }
                                            style={{ width: '100%' }}
                                        >
                                            <Select.Option value="AND">AND</Select.Option>
                                            <Select.Option value="OR">OR</Select.Option>
                                            <Select.Option value="NOT">NOT</Select.Option>
                                        </Select>
                                    </Form.Item>
                                    <Form.Item label="Rules (comma-separated IDs or Names)" required>
                                        <Input
                                            value={newRuleParams.rules?.join(', ') || ''}
                                            onChange={(e: any) =>
                                                setNewRuleParams({
                                                    ...newRuleParams,
                                                    rules: e.target.value.split(',').map((id: string) => id.trim()).filter(Boolean),
                                                })
                                            }
                                            placeholder="e.g., rule1, rule2, rule3"
                                        />
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
                            </Form.Item>                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
                                <Button onClick={handleCloseModal} style={{ padding: '8px 16px' }}>
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
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
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </Page>
    )
}

export default Rules
