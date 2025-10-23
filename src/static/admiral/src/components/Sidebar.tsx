import React from 'react'

type PageKey = 'transactions' | 'rules' | 'profile' | 'graphics'

interface Props {
    active: PageKey
    onSelect: (page: PageKey) => void
}

const Sidebar: React.FC<Props> = ({ active, onSelect }) => {
    const items: { key: PageKey; label: string }[] = [
        { key: 'transactions', label: 'Transactions' },
        { key: 'rules', label: 'Rules' },
        { key: 'profile', label: 'Profile' },
        { key: 'graphics', label: 'Graphics' },
    ]

    return (
        <nav aria-label="Admin sidebar" style={{ width: 220, borderRight: '1px solid #eee', padding: 12 }}>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {items.map(item => (
                    <li key={item.key} style={{ marginBottom: 8 }}>
                        <button
                            onClick={() => onSelect(item.key)}
                            aria-pressed={active === item.key}
                            style={{
                                width: '100%',
                                padding: '10px 12px',
                                textAlign: 'left',
                                border: 'none',
                                background: active === item.key ? '#f0f6ff' : 'transparent',
                                cursor: 'pointer',
                                borderLeft: active === item.key ? '4px solid #2563eb' : '4px solid transparent',
                                borderRadius: 4,
                            }}
                        >
                            {item.label}
                        </button>
                    </li>
                ))}
            </ul>
        </nav>
    )
}

export default Sidebar
