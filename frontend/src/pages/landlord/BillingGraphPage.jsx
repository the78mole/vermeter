/**
 * BillingGraphPage – Visual Node-Based Billing Editor powered by React Flow.
 *
 * Node types:
 *   SourceNode   – reads consumption from a meter over a period
 *   MathNode     – applies a formula (inputA + inputB) * factor
 *   SplitterNode – splits one value into two outputs by ratio (e.g. 30/70 split)
 *   SinkNode     – the final cost bucket (e.g. "Tenant A – Heizkosten")
 *
 * The graph JSON is sent to /api/v1/billing/calculate-graph.
 * In "Preview" mode it runs with sample data and shows results live.
 */
import { useCallback, useState } from 'react'
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
} from 'reactflow'
import { calculateGraph } from '../../api/client'
import { Button, Card } from '../../components/ui'
import { Play, Plus, Zap } from 'lucide-react'

// ---------------------------------------------------------------------------
// Custom node components
// ---------------------------------------------------------------------------

function NodeShell({ color, title, children }) {
  return (
    <div className={`rounded-xl border-2 ${color} bg-white shadow-md min-w-[180px] text-xs`}>
      <div className={`px-3 py-1.5 rounded-t-xl font-semibold text-white text-[11px] ${color.replace('border-', 'bg-')}`}>
        {title}
      </div>
      <div className="px-3 py-2 space-y-1">{children}</div>
    </div>
  )
}

function SourceNode({ data }) {
  return (
    <NodeShell color="border-blue-500" title="📡 Zähler-Quelle">
      <p className="text-gray-700 font-medium truncate">{data.label || 'Zähler'}</p>
      <p className="text-gray-400">{data.period_start} → {data.period_end}</p>
      <Handle type="source" position={Position.Right} id="output" className="!bg-blue-500" />
    </NodeShell>
  )
}

function MathNode({ data }) {
  return (
    <NodeShell color="border-violet-500" title="🧮 Formel">
      <Handle type="target" position={Position.Left} id="inputA" style={{ top: '35%' }} className="!bg-violet-500" />
      <Handle type="target" position={Position.Left} id="inputB" style={{ top: '65%' }} className="!bg-violet-500" />
      <p className="font-mono text-gray-700">{data.formula || 'inputA + inputB'}</p>
      <p className="text-gray-400">× {data.factor ?? 1}</p>
      <Handle type="source" position={Position.Right} id="output" className="!bg-violet-500" />
    </NodeShell>
  )
}

function SplitterNode({ data }) {
  const pct = Math.round((data.ratio ?? 0.3) * 100)
  return (
    <NodeShell color="border-orange-500" title="✂️ Aufteilung">
      <Handle type="target" position={Position.Left} id="input" className="!bg-orange-500" />
      <p className="text-gray-700">{pct}% / {100 - pct}%</p>
      <p className="text-gray-400 text-[10px]">Grundkosten / Verbrauch</p>
      <Handle type="source" position={Position.Right} id="output_a" style={{ top: '35%' }} className="!bg-orange-400" />
      <Handle type="source" position={Position.Right} id="output_b" style={{ top: '65%' }} className="!bg-orange-600" />
    </NodeShell>
  )
}

function SinkNode({ data }) {
  return (
    <NodeShell color="border-green-500" title="💰 Ziel">
      <Handle type="target" position={Position.Left} id="input" className="!bg-green-500" />
      <p className="font-medium text-gray-800 truncate">{data.description || 'Kostenstelle'}</p>
      <p className="text-gray-400">{data.cost_type || 'CUSTOM'}</p>
      {data._result != null && (
        <p className="font-bold text-green-700 mt-1">{Number(data._result).toFixed(2)} €</p>
      )}
    </NodeShell>
  )
}

const nodeTypes = { source: SourceNode, math: MathNode, splitter: SplitterNode, sink: SinkNode }

// ---------------------------------------------------------------------------
// Default demo graph
// ---------------------------------------------------------------------------

const DEMO_NODES = [
  { id: 'n1', type: 'source', position: { x: 50, y: 80 },  data: { label: 'Wärmezähler EG', meter_id: 'demo-meter-1', period_start: '2024-01-01', period_end: '2024-12-31' } },
  { id: 'n2', type: 'source', position: { x: 50, y: 220 }, data: { label: 'Wärmepumpe kWh', meter_id: 'demo-meter-2', period_start: '2024-01-01', period_end: '2024-12-31' } },
  { id: 'n3', type: 'math',   position: { x: 310, y: 140 }, data: { formula: 'inputA + inputB', factor: 1 } },
  { id: 'n4', type: 'splitter', position: { x: 540, y: 140 }, data: { ratio: 0.3 } },
  { id: 'n5', type: 'sink',  position: { x: 780, y: 60 },  data: { description: 'Mieter A – Grundkosten', cost_type: 'HEATING_BASE' } },
  { id: 'n6', type: 'sink',  position: { x: 780, y: 220 }, data: { description: 'Mieter A – Verbrauch', cost_type: 'HEATING_CONSUMPTION' } },
]

const DEMO_EDGES = [
  { id: 'e1', source: 'n1', target: 'n3', sourceHandle: 'output', targetHandle: 'inputA', markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e2', source: 'n2', target: 'n3', sourceHandle: 'output', targetHandle: 'inputB', markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e3', source: 'n3', target: 'n4', sourceHandle: 'output', targetHandle: 'input',  markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e4', source: 'n4', target: 'n5', sourceHandle: 'output_a', targetHandle: 'input', markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e5', source: 'n4', target: 'n6', sourceHandle: 'output_b', targetHandle: 'input', markerEnd: { type: MarkerType.ArrowClosed } },
]

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function BillingGraphPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState(DEMO_NODES)
  const [edges, setEdges, onEdgesChange] = useEdgesState(DEMO_EDGES)
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [errors, setErrors] = useState([])

  const onConnect = useCallback(
    (params) =>
      setEdges((eds) =>
        addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds)
      ),
    [setEdges]
  )

  const addNode = (type) => {
    const templates = {
      source:   { label: 'Neuer Zähler', meter_id: '', period_start: '2024-01-01', period_end: '2024-12-31' },
      math:     { formula: 'inputA + inputB', factor: 1 },
      splitter: { ratio: 0.3 },
      sink:     { description: 'Neue Kostenstelle', cost_type: 'CUSTOM' },
    }
    const id = `n${Date.now()}`
    setNodes((ns) => [
      ...ns,
      { id, type, position: { x: 200 + Math.random() * 100, y: 200 + Math.random() * 100 }, data: templates[type] },
    ])
  }

  const runPreview = async () => {
    setRunning(true)
    setErrors([])
    try {
      const graphPayload = {
        nodes: nodes.map((n) => ({ id: n.id, type: n.type, data: n.data, inputs: [] })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          source_handle: e.sourceHandle,
          target_handle: e.targetHandle,
        })),
        preview_mode: true,
        // Sample data: 1000 kWh per meter for preview
        sample_data: Object.fromEntries(nodes.filter((n) => n.type === 'source').map((n) => [n.data.meter_id || n.id, 1000])),
      }

      const res = await calculateGraph(graphPayload)
      setResult(res.data)

      // Annotate sink nodes with their computed results
      const trace = res.data.calculation_trace?.nodes || {}
      setNodes((ns) =>
        ns.map((n) => {
          if (n.type === 'sink') {
            const nodeTrace = trace[n.id]
            return { ...n, data: { ...n.data, _result: nodeTrace?.outputs?.result ?? null } }
          }
          return n
        })
      )
    } catch (err) {
      const errData = err.response?.data
      setErrors(errData?.detail?.errors || [err.message])
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Abrechnungs-Editor</h1>
          <p className="text-gray-500 mt-1">Visueller Graph-Editor für die Nebenkostenberechnung.</p>
        </div>
        <div className="flex gap-2">
          {['source', 'math', 'splitter', 'sink'].map((t) => (
            <Button key={t} size="sm" variant="secondary" onClick={() => addNode(t)}>
              <Plus className="h-3 w-3 mr-1" />
              {t === 'source' ? 'Quelle' : t === 'math' ? 'Formel' : t === 'splitter' ? 'Aufteilung' : 'Ziel'}
            </Button>
          ))}
          <Button onClick={runPreview} disabled={running}>
            {running ? (
              <span className="flex items-center gap-1"><span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" /> Berechne…</span>
            ) : (
              <span className="flex items-center gap-1"><Play className="h-4 w-4" /> Vorschau</span>
            )}
          </Button>
        </div>
      </div>

      {errors.length > 0 && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 space-y-1">
          {errors.map((e, i) => <p key={i}>{e}</p>)}
        </div>
      )}

      <Card className="p-0 overflow-hidden">
        <div style={{ height: 560 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-right"
          >
            <Background gap={16} size={1} color="#e2e8f0" />
            <Controls />
            <MiniMap nodeColor={(n) => ({ source: '#3b82f6', math: '#8b5cf6', splitter: '#f97316', sink: '#22c55e' }[n.type] ?? '#94a3b8')} />
          </ReactFlow>
        </div>
      </Card>

      {result && (
        <Card>
          <div className="flex items-center gap-2 mb-3">
            <Zap className="h-4 w-4 text-yellow-500" />
            <h2 className="font-semibold text-gray-800">Berechnungsergebnis (Vorschau)</h2>
          </div>
          <pre className="text-xs bg-gray-50 rounded-lg p-4 overflow-auto max-h-48 text-gray-700">
            {JSON.stringify(result.node_results, null, 2)}
          </pre>
        </Card>
      )}

      <Card className="bg-blue-50 border-blue-200">
        <h3 className="font-medium text-blue-900 mb-2 text-sm">Legende</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-blue-500 flex-shrink-0" /><span>Quelle – Zählerstand für Abrechnungszeitraum</span></div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-violet-500 flex-shrink-0" /><span>Formel – mathematische Operation (z.B. Summe)</span></div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-orange-500 flex-shrink-0" /><span>Aufteilung – Grundkosten / Verbrauchskosten</span></div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-green-500 flex-shrink-0" /><span>Ziel – Kostenstelle des Mieters</span></div>
        </div>
      </Card>
    </div>
  )
}
