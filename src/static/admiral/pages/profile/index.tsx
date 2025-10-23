import React, { useState } from 'react'
import { Page, Card, TextInput, Button } from '@devfamily/admiral'

interface ProfileData {
    email: string
    tgAccount: string
    name: string
}

const Profile: React.FC = () => {
    const [formData, setFormData] = useState<ProfileData>({
        email: 'user@example.com', // This should come from authentication
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
        // Handle form submission here
        console.log('Profile updated:', formData)
        // You can call your API here to update the profile
    }

    return (
        <Page title="Profile">
            <Card>
                <form onSubmit={handleSubmit}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        {/* Name Input */}
                        <TextInput
                            label="Name"
                            name="name"
                            placeholder="Enter your name"
                            value={formData.name}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                handleInputChange('name', e.target.value)
                            }
                        />

                        {/* Email Input (Disabled) */}
                        <TextInput
                            label="Email"
                            name="email"
                            placeholder="Email address"
                            value={formData.email}
                            disabled
                        />

                        {/* Telegram Account Input */}
                        <TextInput
                            label="Telegram Account"
                            name="tgAccount"
                            placeholder="@username"
                            value={formData.tgAccount}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                handleInputChange('tgAccount', e.target.value)
                            }
                        />

                        {/* Submit Button */}
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
