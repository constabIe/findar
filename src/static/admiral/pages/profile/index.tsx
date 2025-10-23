import React, { useState } from 'react'
import { Page, Card, TextInput, Button } from '@devfamily/admiral'

interface ProfileData {
    email: string
    tgAccount: string
    name: string
}

const Profile: React.FC = () => {
    const [formData, setFormData] = useState<ProfileData>({
        email: 'user@example.com',
        tgAccount: '@username',
        name: 'John Doe',
    })

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
                <form onSubmit={handleSubmit}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <TextInput
                            label="Name"
                            name="name"
                            placeholder="Enter your name"
                            value={formData.name}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                handleInputChange('name', e.target.value)
                            }
                        />

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
            </Card>
        </Page>
    )
}

export default Profile
