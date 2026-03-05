import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../../api/client'
import { Building2 } from 'lucide-react'
import { Button, Input, Select, Card } from '../../components/ui'

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'TENANT' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
      navigate('/login')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registrierung fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100 p-4">
      <Card className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-blue-600 p-3 rounded-xl mb-4">
            <Building2 className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Konto erstellen</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Vollständiger Name" value={form.full_name} onChange={set('full_name')} required />
          <Input label="E-Mail" type="email" value={form.email} onChange={set('email')} required />
          <Input label="Passwort" type="password" value={form.password} onChange={set('password')} required />
          <Select label="Rolle" value={form.role} onChange={set('role')}>
            <option value="TENANT">Mieter</option>
            <option value="LANDLORD">Vermieter</option>
          </Select>

          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full" size="lg" disabled={loading}>
            {loading ? 'Wird registriert…' : 'Registrieren'}
          </Button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Bereits registriert?{' '}
          <Link to="/login" className="text-blue-600 hover:underline font-medium">
            Anmelden
          </Link>
        </p>
      </Card>
    </div>
  )
}
