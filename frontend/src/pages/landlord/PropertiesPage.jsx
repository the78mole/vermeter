import { useEffect, useState } from 'react'
import { getProperties, createProperty, getPropertyUnits, createUnit } from '../../api/client'
import { Card, Button, Input, Select, Spinner, Badge } from '../../components/ui'
import { Plus, ChevronDown, ChevronRight } from 'lucide-react'

export default function PropertiesPage() {
  const [properties, setProperties] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', address_street: '', address_city: '', address_zip: '', address_country: 'Germany' })
  const [expanded, setExpanded] = useState({})
  const [units, setUnits] = useState({})
  const [unitForm, setUnitForm] = useState({})
  const [showUnitForm, setShowUnitForm] = useState({})

  const load = () => getProperties().then((r) => setProperties(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    await createProperty(form)
    setForm({ name: '', address_street: '', address_city: '', address_zip: '', address_country: 'Germany' })
    setShowForm(false)
    load()
  }

  const toggleExpand = async (propId) => {
    const isOpen = expanded[propId]
    setExpanded((p) => ({ ...p, [propId]: !isOpen }))
    if (!isOpen && !units[propId]) {
      const res = await getPropertyUnits(propId)
      setUnits((u) => ({ ...u, [propId]: res.data }))
    }
  }

  const handleCreateUnit = async (e, propId) => {
    e.preventDefault()
    const uf = unitForm[propId] || {}
    await createUnit(propId, { ...uf, square_meters: parseFloat(uf.square_meters || 0), rooms: uf.rooms ? parseFloat(uf.rooms) : undefined })
    setShowUnitForm((s) => ({ ...s, [propId]: false }))
    const res = await getPropertyUnits(propId)
    setUnits((u) => ({ ...u, [propId]: res.data }))
  }

  const setUF = (propId, field) => (e) =>
    setUnitForm((prev) => ({ ...prev, [propId]: { ...prev[propId], [field]: e.target.value } }))

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mieteinheiten</h1>
          <p className="text-gray-500 mt-1">Verwalten Sie Ihre Immobilien und Wohneinheiten.</p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>
          <Plus className="h-4 w-4 mr-1" /> Immobilie hinzufügen
        </Button>
      </div>

      {showForm && (
        <Card>
          <h2 className="font-semibold text-gray-800 mb-4">Neue Immobilie</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
            <Input label="Straße" value={form.address_street} onChange={(e) => setForm((f) => ({ ...f, address_street: e.target.value }))} required />
            <Input label="Stadt" value={form.address_city} onChange={(e) => setForm((f) => ({ ...f, address_city: e.target.value }))} required />
            <Input label="PLZ" value={form.address_zip} onChange={(e) => setForm((f) => ({ ...f, address_zip: e.target.value }))} required />
            <div className="sm:col-span-2 flex gap-2 justify-end">
              <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Abbrechen</Button>
              <Button type="submit">Speichern</Button>
            </div>
          </form>
        </Card>
      )}

      <div className="space-y-4">
        {properties.map((prop) => (
          <Card key={prop.id} className="p-0">
            <button
              onClick={() => toggleExpand(prop.id)}
              className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 rounded-xl transition-colors"
            >
              <div>
                <p className="font-semibold text-gray-900">{prop.name}</p>
                <p className="text-sm text-gray-500">{prop.address_street}, {prop.address_zip} {prop.address_city}</p>
              </div>
              {expanded[prop.id] ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
            </button>

            {expanded[prop.id] && (
              <div className="border-t border-gray-100 px-6 pb-4">
                <div className="flex items-center justify-between py-3">
                  <p className="font-medium text-gray-700">Mieteinheiten</p>
                  <Button size="sm" onClick={() => setShowUnitForm((s) => ({ ...s, [prop.id]: !s[prop.id] }))}>
                    <Plus className="h-3 w-3 mr-1" /> Einheit
                  </Button>
                </div>

                {showUnitForm[prop.id] && (
                  <form onSubmit={(e) => handleCreateUnit(e, prop.id)} className="grid grid-cols-2 gap-3 mb-4 p-4 bg-gray-50 rounded-lg">
                    <Input label="Name" value={unitForm[prop.id]?.name || ''} onChange={setUF(prop.id, 'name')} required />
                    <Input label="Fläche (m²)" type="number" step="0.01" value={unitForm[prop.id]?.square_meters || ''} onChange={setUF(prop.id, 'square_meters')} required />
                    <Input label="Zimmer" type="number" step="0.5" value={unitForm[prop.id]?.rooms || ''} onChange={setUF(prop.id, 'rooms')} />
                    <Select label="Heizungstyp" value={unitForm[prop.id]?.heating_type || 'GAS'} onChange={setUF(prop.id, 'heating_type')}>
                      <option value="GAS">Gas</option>
                      <option value="OIL">Öl</option>
                      <option value="HEAT_PUMP">Wärmepumpe</option>
                      <option value="DISTRICT_HEATING">Fernwärme</option>
                      <option value="ELECTRICITY">Strom</option>
                    </Select>
                    <div className="col-span-2 flex gap-2 justify-end">
                      <Button type="button" variant="secondary" size="sm" onClick={() => setShowUnitForm((s) => ({ ...s, [prop.id]: false }))}>Abbrechen</Button>
                      <Button type="submit" size="sm">Speichern</Button>
                    </div>
                  </form>
                )}

                {(units[prop.id] || []).map((unit) => (
                  <div key={unit.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{unit.name}</p>
                      <p className="text-xs text-gray-500">{unit.square_meters} m² · {unit.rooms} Zi. · {unit.heating_type}</p>
                    </div>
                    <Badge color={unit.is_occupied ? 'green' : 'gray'}>
                      {unit.is_occupied ? 'Belegt' : 'Frei'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        ))}

        {properties.length === 0 && (
          <div className="text-center py-12 text-gray-400">Noch keine Immobilien vorhanden.</div>
        )}
      </div>
    </div>
  )
}
