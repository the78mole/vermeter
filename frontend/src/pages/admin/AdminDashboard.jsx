import { useEffect, useState } from 'react'
import { Building2, Users, FileText, TrendingUp } from 'lucide-react'
import { getAdminStats } from '../../api/client'

function StatCard({ icon: Icon, label, value, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${colors[color]}`}>
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value ?? '–'}</p>
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    getAdminStats().then((r) => setStats(r.data)).catch(() => {})
  }, [])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Plattform-Übersicht</h1>
        <p className="text-sm text-gray-500 mt-1">Statistiken und Status aller Mandanten</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Building2} label="Vermieter gesamt" value={stats?.landlords_total} color="blue" />
        <StatCard icon={TrendingUp} label="Vermieter aktiv" value={stats?.landlords_active} color="green" />
        <StatCard icon={Users} label="Mieter gesamt" value={stats?.tenants_total} color="purple" />
        <StatCard icon={FileText} label="Mietverträge" value={stats?.contracts_total} color="orange" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-2">Schnellaktionen</h2>
        <p className="text-sm text-gray-500">
          Verwalte Vermieter-Konten unter <a href="/admin/landlords" className="text-blue-600 hover:underline">Vermieter</a>.
        </p>
      </div>
    </div>
  )
}
