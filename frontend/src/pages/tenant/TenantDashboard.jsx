import { useEffect, useState } from 'react'
import { myContracts, myMeters, myInterpolatedReadings, myUtilityBills } from '../../api/client'
import { Card, Spinner, Badge } from '../../components/ui'
import { ConsumptionChart } from '../../components/charts/ConsumptionChart'
import { ContractTimeline } from '../../components/charts/ContractTimeline'
import { Zap, Droplets, Flame, BarChart2 } from 'lucide-react'

const METER_ICON = { ELECTRICITY: Zap, WATER_COLD: Droplets, WATER_HOT: Droplets, HEAT: Flame, GAS: Flame, OIL: Flame }
const METER_LABEL = { ELECTRICITY: 'Strom', WATER_COLD: 'Kaltwasser', WATER_HOT: 'Warmwasser', HEAT: 'Wärme', GAS: 'Gas', OIL: 'Heizöl' }

export default function TenantDashboard() {
  const [contracts, setContracts] = useState([])
  const [meters, setMeters] = useState([])
  const [chartData, setChartData] = useState({})
  const [latestBill, setLatestBill] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([myContracts(), myMeters(), myUtilityBills()])
      .then(async ([cr, mr, br]) => {
        setContracts(cr.data)
        setMeters(mr.data)
        setLatestBill(br.data[0] || null)

        // Load interpolated readings for each meter
        const readings = {}
        await Promise.all(
          mr.data.map(async (m) => {
            try {
              const r = await myInterpolatedReadings(m.id)
              readings[m.id] = { data: r.data, type: m.meter_type }
            } catch {}
          })
        )
        setChartData(readings)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />

  const activeContract = contracts.find((c) => c.status === 'ACTIVE') || contracts[0]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mein Dashboard</h1>
        <p className="text-gray-500 mt-1">Ihre Verbrauchsdaten und Abrechnungen auf einen Blick.</p>
      </div>

      {/* Active contract timeline */}
      {activeContract && (
        <Card>
          <h2 className="font-semibold text-gray-800 mb-4">Mietvertrag-Status</h2>
          <ContractTimeline status={activeContract.status} />
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div><p className="text-gray-500">Beginn</p><p className="font-medium">{activeContract.start_date}</p></div>
            {activeContract.end_date && <div><p className="text-gray-500">Ende</p><p className="font-medium">{activeContract.end_date}</p></div>}
            <div><p className="text-gray-500">Kaltmiete</p><p className="font-medium">{parseFloat(activeContract.monthly_rent).toFixed(2)} €/Monat</p></div>
            <div><p className="text-gray-500">Nebenkostenvorauszahlung</p><p className="font-medium">{parseFloat(activeContract.advance_payment_utilities).toFixed(2)} €/Monat</p></div>
          </div>
        </Card>
      )}

      {/* Latest bill summary */}
      {latestBill && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-800">Letzte Nebenkostenabrechnung</h2>
            <Badge color={{ CALCULATING: 'blue', REVIEW_REQUIRED: 'yellow', SENT_TO_TENANT: 'purple', PAID: 'green', DISPUTED: 'red' }[latestBill.status]}>
              {latestBill.status}
            </Badge>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div><p className="text-gray-500">Abrechnungszeitraum</p><p className="font-medium">{latestBill.billing_period_start} – {latestBill.billing_period_end}</p></div>
            <div><p className="text-gray-500">Heizung</p><p className="font-medium">{parseFloat(latestBill.heating_cost).toFixed(2)} €</p></div>
            <div><p className="text-gray-500">Gesamt</p><p className="font-bold">{parseFloat(latestBill.total_cost).toFixed(2)} €</p></div>
            <div>
              <p className="text-gray-500">Saldo</p>
              <p className={`font-bold ${parseFloat(latestBill.balance) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {parseFloat(latestBill.balance) >= 0 ? `Nachzahlung: ${parseFloat(latestBill.balance).toFixed(2)} €` : `Guthaben: ${Math.abs(parseFloat(latestBill.balance)).toFixed(2)} €`}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Consumption charts */}
      {Object.entries(chartData).map(([meterId, { data, type }]) => {
        if (!data.length) return null
        const Icon = METER_ICON[type] ?? BarChart2
        return (
          <Card key={meterId}>
            <div className="flex items-center gap-2 mb-4">
              <Icon className="h-5 w-5 text-blue-600" />
              <h2 className="font-semibold text-gray-800">{METER_LABEL[type] ?? type} – Verbrauchsverlauf</h2>
            </div>
            <ConsumptionChart data={data} meterType={type} />
          </Card>
        )
      })}

      {meters.length === 0 && contracts.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg font-medium">Willkommen!</p>
          <p className="text-sm mt-1">Sobald Ihr Vermieter Ihnen einen Vertrag zuweist, erscheinen hier Ihre Daten.</p>
        </div>
      )}
    </div>
  )
}
