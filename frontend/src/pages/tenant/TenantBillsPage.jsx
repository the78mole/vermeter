import { useEffect, useState } from 'react'
import { myUtilityBills } from '../../api/client'
import { Card, Spinner, Badge } from '../../components/ui'
import { Download } from 'lucide-react'

const BILL_BADGE = { CALCULATING: 'blue', REVIEW_REQUIRED: 'yellow', SENT_TO_TENANT: 'purple', PAID: 'green', DISPUTED: 'red' }
const BILL_LABEL = { CALCULATING: 'Wird berechnet', REVIEW_REQUIRED: 'Prüfung', SENT_TO_TENANT: 'Gesendet', PAID: 'Bezahlt', DISPUTED: 'Strittig' }

export default function TenantBillsPage() {
  const [bills, setBills] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    myUtilityBills().then((r) => setBills(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Nebenkostenabrechnungen</h1>
        <p className="text-gray-500 mt-1">Ihre Nebenkostenabrechnungen im Überblick.</p>
      </div>

      {bills.map((b) => (
        <Card key={b.id}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="font-semibold text-gray-900">Abrechnungszeitraum</p>
              <p className="text-sm text-gray-500 mt-0.5">{b.billing_period_start} – {b.billing_period_end}</p>
            </div>
            <Badge color={BILL_BADGE[b.status]}>{BILL_LABEL[b.status]}</Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm mb-4">
            <div><p className="text-gray-500">Heizung</p><p className="font-medium">{parseFloat(b.heating_cost).toFixed(2)} €</p></div>
            <div><p className="text-gray-500">Wasser</p><p className="font-medium">{parseFloat(b.water_cost).toFixed(2)} €</p></div>
            <div><p className="text-gray-500">Vorauszahlungen</p><p className="font-medium">{parseFloat(b.advance_payments_total).toFixed(2)} €</p></div>
            <div>
              <p className="text-gray-500">Saldo</p>
              <p className={`font-bold ${parseFloat(b.balance) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {parseFloat(b.balance) >= 0
                  ? `Nachzahlung: ${parseFloat(b.balance).toFixed(2)} €`
                  : `Guthaben: ${Math.abs(parseFloat(b.balance)).toFixed(2)} €`}
              </p>
            </div>
          </div>

          {b.line_items.length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <p className="text-xs font-medium text-gray-500 mb-2">Kostenaufstellung</p>
              <div className="space-y-1">
                {b.line_items.map((item) => (
                  <div key={item.id} className="flex justify-between text-sm">
                    <span className="text-gray-700">{item.description}</span>
                    <span className="font-medium">{parseFloat(item.unit_share).toFixed(2)} €</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {b.pdf_url && (
            <div className="mt-3 flex justify-end">
              <a href={b.pdf_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
                <Download className="h-4 w-4" /> PDF herunterladen
              </a>
            </div>
          )}
        </Card>
      ))}

      {bills.length === 0 && (
        <div className="text-center py-12 text-gray-400">Noch keine Nebenkostenabrechnungen vorhanden.</div>
      )}
    </div>
  )
}
