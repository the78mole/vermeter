import { useEffect, useState } from 'react'
import { getTenants } from '../../api/client'
import { Card, Badge, Spinner } from '../../components/ui'
import { User } from 'lucide-react'

export default function TenantsPage() {
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTenants().then((r) => setTenants(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mieter</h1>
        <p className="text-gray-500 mt-1">Alle Mieter mit aktiven oder abgelaufenen Verträgen.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {tenants.map((t) => (
          <Card key={t.id} className="flex items-center gap-4">
            <div className="bg-blue-100 p-3 rounded-xl">
              <User className="h-5 w-5 text-blue-700" />
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-gray-900 truncate">{t.full_name}</p>
              <p className="text-sm text-gray-500 truncate">{t.email}</p>
            </div>
            <Badge color={t.is_active ? 'green' : 'gray'}>
              {t.is_active ? 'Aktiv' : 'Inaktiv'}
            </Badge>
          </Card>
        ))}

        {tenants.length === 0 && (
          <div className="col-span-3 text-center py-12 text-gray-400">Keine Mieter gefunden.</div>
        )}
      </div>
    </div>
  )
}
