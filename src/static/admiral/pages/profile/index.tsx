import React, { useState, useEffect } from 'react'
import { Page, Card, TextInput, Button } from '@devfamily/admiral'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'

interface ProfileData {
    email: string
    tgAccount: string
}

interface UserResponse {
    id: string
    email: string
    telegram_alias: string
    telegram_id: number
    created_at: string
}

const Profile: React.FC = () => {
    const [formData, setFormData] = useState<ProfileData>({
        email: '',
        tgAccount: '',
    })
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        fetchProfile()
    }, [])

    const fetchProfile = async () => {
        try {
            setLoading(true)
            setError('')
            
            const token = localStorage.getItem('admiral_global_admin_session_token')
            
            if (!token) {
                setError('No authentication token found. Please login again.')
                setLoading(false)
                return
            }

            const response = await axios.get<UserResponse>(`${API_URL}/users/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            setFormData({
                email: response.data.email,
                tgAccount: response.data.telegram_alias,
            })
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load profile data.')
            console.error('Error fetching profile:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleInputChange = (name: keyof ProfileData, value: string) => {
        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }))
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        console.log('Profile updated:', formData)
    }

    return (
        <Page title="Profile">
            <Card>
                {loading ? (
                    <div style={{ padding: '20px', textAlign: 'center' }}>Loading profile...</div>
                ) : error ? (
                    <div style={{ padding: '20px', color: 'red' }}>{error}</div>
                ) : (
                    <form onSubmit={handleSubmit}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <TextInput
                                label="Email"
                                name="email"
                                placeholder="Email address"
                                value={formData.email}
                                disabled
                            />

                            <TextInput
                                label="Telegram Account"
                                name="tgAccount"
                                placeholder="@username"
                                value={formData.tgAccount}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                    handleInputChange('tgAccount', e.target.value)
                                }
                            />

                            <div style={{ marginTop: '16px' }}>
                                <Button type="submit">Save Changes</Button>
                            </div>
                        </div>
                    </form>
                )}
            </Card>
        </Page>
    )
}

export default Profile
