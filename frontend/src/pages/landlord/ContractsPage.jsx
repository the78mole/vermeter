import { useEffect, useState } from 'react'
import { getContracts, updateContractStatus } from '../../api/client'
import { Card, Button, Badge, Spinner } from '../../components/ui'
import { ContractTimeline } from '../../components/charts/ContractTimeline'

const STATUS_BADGE = {
  DRAFT: 'gray',
  PENDING_SIGNATURE: 'yellow',
  ACTIVE: 'green',
  TERMINATED: 'red',
  ARCHIVED: 'gray',
}

const NEXT_STATUS = {
  DRAFT: 'PENDING_SIGNATURE',
  PENDING_SIGNATURE: 'ACTIVE',
  ACTIVE: 'TERMINATED',
  TERMINATED: 'ARCHIVED',
}

const NEXT_LABEL = {
  DRAFT: 'Zur Unterschrift',
  PENDING_SIGNATURE: 'Aktivieren',
  ACTIVE: 'Kündigen',
  TERMINATED: 'Archivieren',
}

export default function ContractsPage() {
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(null)

  const load = () => getContracts().then((r) => setContracts(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const advance = async (id, next) => {
    setUpdating(id)
    try {
      await updateContractStatus(id, next)
      load()
    } finally {
      setUpdating(null)
    }
  }

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mietverträge</h1>
        <p className="text-gray-500 mt-1">Verwalten Sie den Status Ihrer Mietverträge.</p>
      </div>

      <div className="space-y-4">
        {contracts.map((c) => (
          <Card key={c.id} className="space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-gray-900">Vertrag #{c.id.slice(0, 8)}</p>
                <p className="text-sm text-gray-500 mt-0.5">
                  {c.start_date} {c.end_date ? `– ${c.end_date}` : '(unbefristet)'}
                  {' · '}
                  {parseFloat(c.monthly_rent).toFixed(2)} € / Monat
                </p>
              </div>
              <Badge color={STATUS_BADGE[c.status]}>{c.status}</Badge>
            </div>

            <ContractTimeline status={c.status} />

            {NEXT_STATUS[c.status] && (
              <div className="flex justify-end">
                <Button
                  size="sm"
                  variant={c.status === 'ACTIVE' ? 'danger' : 'primary'}
                  disabled={updating === c.id}
                  onClick={() => advance(c.id, NEXT_STATUS[c.status])}
                >
                  {updating === c.id ? '…' : NEXT_LABEL[c.status]}
                </Button>
              </div>
            )}
          </Card>
        ))}

        {contracts.length === 0 && (
          <div className="text-center py-12 text-gray-400">Noch keine Mietverträge vorhanden.</div>
        )}
      </div>
    </div>
  )
}
