import { useEffect, useState } from 'react'
import { getProperties, getContracts, getUtilityBills, getTenants } from '../../api/client'
import { Card, Spinner } from '../../components/ui'
import { Building2, Users, FileText, BarChart2 } from 'lucide-react'

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <Card className="flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </Card>
  )
}

export default function LandlordDashboard() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    Promise.all([getProperties(), getContracts(), getUtilityBills(), getTenants()])
      .then(([p, c, b, t]) =>
        setStats({
          properties: p.data.length,
          contracts: c.data.length,
          bills: b.data.length,
          tenants: t.data.length,
        })
      )
      .catch(() => setStats({ properties: 0, contracts: 0, bills: 0, tenants: 0 }))
  }, [])

  if (!stats) return <Spinner />

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Übersicht</h1>
        <p className="text-gray-500 mt-1">Willkommen zurück in Ihrem Verwaltungs-Dashboard.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Building2} label="Immobilien" value={stats.properties} color="bg-blue-600" />
        <StatCard icon={FileText} label="Mietverträge" value={stats.contracts} color="bg-green-600" />
        <StatCard icon={BarChart2} label="Abrechnungen" value={stats.bills} color="bg-orange-500" />
        <StatCard icon={Users} label="Mieter" value={stats.tenants} color="bg-purple-600" />
      </div>
    </div>
  )
}
