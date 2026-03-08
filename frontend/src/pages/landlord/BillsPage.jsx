import { useEffect, useState } from 'react'
import { getUtilityBills, updateBillStatus, generateBillPdf } from '../../api/client'
import { Card, Button, Badge, Spinner } from '../../components/ui'
import { Download, Send } from 'lucide-react'

const BILL_BADGE = {
  CALCULATING: 'blue',
  REVIEW_REQUIRED: 'yellow',
  SENT_TO_TENANT: 'purple',
  PAID: 'green',
  DISPUTED: 'red',
}

const BILL_LABEL = {
  CALCULATING: 'Wird berechnet',
  REVIEW_REQUIRED: 'Prüfung erforderlich',
  SENT_TO_TENANT: 'An Mieter gesendet',
  PAID: 'Bezahlt',
  DISPUTED: 'Strittig',
}

export default function BillsPage() {
  const [bills, setBills] = useState([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(null)

  const load = () => getUtilityBills().then((r) => setBills(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const sendToTenant = async (id) => {
    setWorking(id)
    try { await updateBillStatus(id, 'SENT_TO_TENANT'); load() }
    finally { setWorking(null) }
  }

  const markPaid = async (id) => {
    setWorking(id)
    try { await updateBillStatus(id, 'PAID'); load() }
    finally { setWorking(null) }
  }

  const triggerPdf = async (id) => {
    setWorking(id)
    try { await generateBillPdf(id) }
    finally { setWorking(null) }
  }

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Nebenkostenabrechnungen</h1>
        <p className="text-gray-500 mt-1">Verwalten Sie den Status Ihrer Abrechnungen.</p>
      </div>

      <div className="space-y-4">
        {bills.map((b) => (
          <Card key={b.id}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="font-semibold text-gray-900">
                  Abrechnungszeitraum: {b.billing_period_start} – {b.billing_period_end}
                </p>
                <p className="text-sm text-gray-500 mt-0.5">Vertrag: {b.contract_id.slice(0, 8)}</p>
              </div>
              <Badge color={BILL_BADGE[b.status]}>{BILL_LABEL[b.status]}</Badge>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4 text-sm">
              <div><p className="text-gray-500">Heizung</p><p className="font-medium">{parseFloat(b.heating_cost).toFixed(2)} €</p></div>
              <div><p className="text-gray-500">Wasser</p><p className="font-medium">{parseFloat(b.water_cost).toFixed(2)} €</p></div>
              <div><p className="text-gray-500">Gesamt</p><p className="font-bold text-gray-900">{parseFloat(b.total_cost).toFixed(2)} €</p></div>
              <div>
                <p className="text-gray-500">Saldo</p>
                <p className={`font-bold ${parseFloat(b.balance) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {parseFloat(b.balance) >= 0 ? `+${parseFloat(b.balance).toFixed(2)} €` : `${parseFloat(b.balance).toFixed(2)} €`}
                </p>
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="secondary" onClick={() => triggerPdf(b.id)} disabled={working === b.id}>
                <Download className="h-3 w-3 mr-1" /> PDF generieren
              </Button>
              {b.status === 'REVIEW_REQUIRED' && (
                <Button size="sm" onClick={() => sendToTenant(b.id)} disabled={working === b.id}>
                  <Send className="h-3 w-3 mr-1" /> An Mieter senden
                </Button>
              )}
              {b.status === 'SENT_TO_TENANT' && (
                <Button size="sm" variant="success" onClick={() => markPaid(b.id)} disabled={working === b.id}>
                  Als bezahlt markieren
                </Button>
              )}
            </div>
          </Card>
        ))}

        {bills.length === 0 && (
          <div className="text-center py-12 text-gray-400">Noch keine Abrechnungen vorhanden.</div>
        )}
      </div>
    </div>
  )
}
