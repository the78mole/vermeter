import { useEffect, useState } from 'react'
import { myContracts } from '../../api/client'
import { Card, Spinner, Badge } from '../../components/ui'
import { ContractTimeline } from '../../components/charts/ContractTimeline'

export default function TenantContractsPage() {
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    myContracts().then((r) => setContracts(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mein Mietvertrag</h1>
        <p className="text-gray-500 mt-1">Ihre Mietvertragsdetails und aktueller Status.</p>
      </div>

      {contracts.map((c) => (
        <Card key={c.id} className="space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-semibold text-gray-900">Vertrag #{c.id.slice(0, 8)}</p>
              <p className="text-sm text-gray-500 mt-0.5">{c.start_date} {c.end_date ? `– ${c.end_date}` : '(unbefristet)'}</p>
            </div>
            <Badge color={{ DRAFT: 'gray', PENDING_SIGNATURE: 'yellow', ACTIVE: 'green', TERMINATED: 'red', ARCHIVED: 'gray' }[c.status]}>
              {c.status}
            </Badge>
          </div>

          <ContractTimeline status={c.status} />

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm pt-2">
            <div><p className="text-gray-500">Kaltmiete</p><p className="font-medium">{parseFloat(c.monthly_rent).toFixed(2)} €/Monat</p></div>
            <div><p className="text-gray-500">Nebenkosten-Vorauszahlung</p><p className="font-medium">{parseFloat(c.advance_payment_utilities).toFixed(2)} €/Monat</p></div>
            {c.deposit && <div><p className="text-gray-500">Kaution</p><p className="font-medium">{parseFloat(c.deposit).toFixed(2)} €</p></div>}
          </div>
        </Card>
      ))}

      {contracts.length === 0 && (
        <div className="text-center py-12 text-gray-400">Noch kein Mietvertrag vorhanden.</div>
      )}
    </div>
  )
}
