import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, getMe } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import { Building2 } from 'lucide-react'
import { Button, Input, Card } from '../../components/ui'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await login(email, password)
      // Fetch user profile
      const meRes = await getMe()
      setAuth(data.access_token, meRes.data)
      const role = meRes.data.role
      navigate(role === 'LANDLORD' || role === 'ADMIN' ? '/landlord' : '/tenant')
    } catch (err) {
      setError(err.response?.data?.detail || 'Anmeldung fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100 p-4">
      <Card className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-blue-600 p-3 rounded-xl mb-4">
            <Building2 className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">RentalManager</h1>
          <p className="text-gray-500 text-sm mt-1">Bitte melden Sie sich an</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="E-Mail"
            type="email"
            placeholder="name@beispiel.de"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            label="Passwort"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full" size="lg" disabled={loading}>
            {loading ? 'Wird angemeldet…' : 'Anmelden'}
          </Button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Noch kein Konto?{' '}
          <Link to="/register" className="text-blue-600 hover:underline font-medium">
            Registrieren
          </Link>
        </p>
      </Card>
    </div>
  )
}
