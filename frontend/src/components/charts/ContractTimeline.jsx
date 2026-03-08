import { CheckCircle, Circle, Clock } from 'lucide-react'

const STEPS = [
  { status: 'DRAFT', label: 'Entwurf', de: 'ENTWURF' },
  { status: 'PENDING_SIGNATURE', label: 'Ausstehende Unterschrift', de: 'UNTERSCHRIFT' },
  { status: 'ACTIVE', label: 'Aktiv', de: 'AKTIV' },
  { status: 'TERMINATED', label: 'Gekündigt', de: 'GEKÜNDIGT' },
  { status: 'ARCHIVED', label: 'Archiviert', de: 'ARCHIVIERT' },
]

const STATUS_COLOR = {
  DRAFT: 'text-gray-500',
  PENDING_SIGNATURE: 'text-yellow-600',
  ACTIVE: 'text-green-600',
  TERMINATED: 'text-red-600',
  ARCHIVED: 'text-slate-500',
}

export function ContractTimeline({ status }) {
  const currentIdx = STEPS.findIndex((s) => s.status === status)

  return (
    <div className="flex items-center gap-0 overflow-x-auto">
      {STEPS.map((step, idx) => {
        const done = idx < currentIdx
        const active = idx === currentIdx
        return (
          <div key={step.status} className="flex items-center">
            <div className="flex flex-col items-center gap-1 min-w-[80px]">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors
                  ${done ? 'border-blue-600 bg-blue-600' : active ? 'border-blue-600 bg-white' : 'border-gray-300 bg-white'}`}
              >
                {done ? (
                  <CheckCircle className="h-5 w-5 text-white" />
                ) : active ? (
                  <Clock className={`h-4 w-4 ${STATUS_COLOR[step.status]}`} />
                ) : (
                  <Circle className="h-4 w-4 text-gray-300" />
                )}
              </div>
              <span
                className={`text-xs font-medium text-center leading-tight
                  ${active ? STATUS_COLOR[step.status] : done ? 'text-blue-600' : 'text-gray-400'}`}
              >
                {step.de}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div className={`h-0.5 w-8 mx-0.5 ${idx < currentIdx ? 'bg-blue-600' : 'bg-gray-200'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
