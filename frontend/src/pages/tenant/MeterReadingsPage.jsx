import { useEffect, useState } from 'react'
import { myMeters, myMeterReadings, submitMeterReading } from '../../api/client'
import { Card, Button, Input, Spinner, Badge } from '../../components/ui'
import { Plus, Zap } from 'lucide-react'

const METER_LABEL = { ELECTRICITY: 'Strom', WATER_COLD: 'Kaltwasser', WATER_HOT: 'Warmwasser', HEAT: 'Wärme', GAS: 'Gas', OIL: 'Heizöl' }
const METER_UNIT  = { ELECTRICITY: 'kWh', WATER_COLD: 'm³', WATER_HOT: 'm³', HEAT: 'kWh', GAS: 'm³', OIL: 'L' }

export default function MeterReadingsPage() {
  const [meters, setMeters] = useState([])
  const [readings, setReadings] = useState({})
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState({})
  const [form, setForm] = useState({})
  const [submitting, setSubmitting] = useState(null)

  useEffect(() => {
    myMeters()
      .then(async (res) => {
        setMeters(res.data)
        const rMap = {}
        await Promise.all(
          res.data.map(async (m) => {
            const r = await myMeterReadings(m.id)
            rMap[m.id] = r.data
          })
        )
        setReadings(rMap)
      })
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e, meterId) => {
    e.preventDefault()
    setSubmitting(meterId)
    const f = form[meterId] || {}
    try {
      await submitMeterReading(meterId, {
        reading_date: f.reading_date,
        value: parseFloat(f.value),
        unit_of_measure: METER_UNIT[meters.find((m) => m.id === meterId)?.meter_type] ?? 'kWh',
        notes: f.notes || undefined,
      })
      // Refresh readings
      const r = await myMeterReadings(meterId)
      setReadings((prev) => ({ ...prev, [meterId]: r.data }))
      setShowForm((prev) => ({ ...prev, [meterId]: false }))
    } finally {
      setSubmitting(null)
    }
  }

  const setF = (meterId, field) => (e) =>
    setForm((prev) => ({ ...prev, [meterId]: { ...prev[meterId], [field]: e.target.value } }))

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Zählerstand einreichen</h1>
        <p className="text-gray-500 mt-1">Erfassen Sie Ihre aktuellen Zählerstände (Zählerstand-Foto optional).</p>
      </div>

      {meters.map((m) => (
        <Card key={m.id}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="bg-blue-100 p-2.5 rounded-xl">
                <Zap className="h-5 w-5 text-blue-700" />
              </div>
              <div>
                <p className="font-semibold text-gray-900">{METER_LABEL[m.meter_type] ?? m.meter_type}</p>
                {m.serial_number && <p className="text-xs text-gray-400">Nr. {m.serial_number}</p>}
              </div>
            </div>
            <Button size="sm" onClick={() => setShowForm((p) => ({ ...p, [m.id]: !p[m.id] }))}>
              <Plus className="h-3 w-3 mr-1" /> Ablesung hinzufügen
            </Button>
          </div>

          {showForm[m.id] && (
            <form onSubmit={(e) => handleSubmit(e, m.id)} className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4 p-4 bg-gray-50 rounded-lg">
              <Input label="Datum" type="date" value={form[m.id]?.reading_date || ''} onChange={setF(m.id, 'reading_date')} required />
              <Input label={`Wert (${METER_UNIT[m.meter_type] ?? 'Einheit'})`} type="number" step="0.001" value={form[m.id]?.value || ''} onChange={setF(m.id, 'value')} required />
              <Input label="Notiz (optional)" value={form[m.id]?.notes || ''} onChange={setF(m.id, 'notes')} />
              <div className="sm:col-span-3 flex justify-end gap-2">
                <Button type="button" size="sm" variant="secondary" onClick={() => setShowForm((p) => ({ ...p, [m.id]: false }))}>Abbrechen</Button>
                <Button type="submit" size="sm" disabled={submitting === m.id}>
                  {submitting === m.id ? 'Wird gespeichert…' : 'Speichern'}
                </Button>
              </div>
            </form>
          )}

          <div className="space-y-1 max-h-48 overflow-y-auto">
            {(readings[m.id] || []).slice().reverse().map((r) => (
              <div key={r.id} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50 last:border-0">
                <span className="text-gray-600">{r.reading_date}</span>
                <span className="font-medium text-gray-900">{parseFloat(r.value).toFixed(3)} {r.unit_of_measure}</span>
                {r.is_interpolated && <Badge color="blue">Interpoliert</Badge>}
              </div>
            ))}
            {!(readings[m.id] || []).length && (
              <p className="text-sm text-gray-400 text-center py-2">Noch keine Ablesungen vorhanden.</p>
            )}
          </div>
        </Card>
      ))}

      {meters.length === 0 && (
        <div className="text-center py-12 text-gray-400">Keine Zähler für Ihren Vertrag gefunden.</div>
      )}
    </div>
  )
}
