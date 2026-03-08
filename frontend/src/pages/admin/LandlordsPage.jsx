import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCopy,
  Download,
  FileText,
  File,
  Globe,
  MapPin,
  Paperclip,
  Pencil,
  Phone,
  Plus,
  Receipt,
  Search,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Upload,
  User,
  Building2,
  CreditCard,
  X,
  Check,
} from 'lucide-react'
import {
  getLandlords,
  createLandlord,
  updateLandlord,
  upsertLandlordProfile,
  listDocuments,
  uploadDocument,
  updateDocument,
  deleteDocument,
  downloadDocumentUrl,
  searchTags,
} from '../../api/client'
import { userManager } from '../../api/client'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function Badge({ active }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
      }`}
    >
      {active ? 'Aktiv' : 'Inaktiv'}
    </span>
  )
}

function Field({ label, icon: Icon, children }) {
  return (
    <div>
      <label className="flex items-center gap-1 text-xs font-medium text-gray-500 mb-1">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {label}
      </label>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Create Modal
// ---------------------------------------------------------------------------

function CreateModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ email: '', full_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (result?.temp_password) {
      navigator.clipboard.writeText(result.temp_password)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.email || !form.full_name) {
      setError('Alle Felder sind erforderlich.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await createLandlord(form)
      onCreated(res.data)
      setResult({
        landlord: res.data,
        keycloak_created: res.data.keycloak_created,
        temp_password: res.data.temp_password,
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Fehler beim Anlegen.')
    } finally {
      setLoading(false)
    }
  }

  if (result) {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
            <h2 className="text-lg font-semibold text-gray-900">Vermieter angelegt</h2>
          </div>
          {result.keycloak_created ? (
            <>
              <p className="text-sm text-gray-600">
                Keycloak-Konto wurde automatisch erstellt. Der Vermieter muss beim ersten Login ein neues Passwort setzen.
              </p>
              {result.temp_password && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <p className="text-xs font-medium text-gray-500 mb-2">Temporäres Einmal-Passwort</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-sm font-mono text-gray-900 select-all break-all">
                      {result.temp_password}
                    </code>
                    <button
                      onClick={handleCopy}
                      className="p-1.5 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                      title="Passwort kopieren"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-green-500" />
                      ) : (
                        <ClipboardCopy className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    Dieses Passwort wird nur einmal angezeigt und nicht gespeichert.
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 flex gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                Datenbankeintrag wurde erstellt, aber das Keycloak-Konto konnte nicht automatisch provisioniert werden.
              </span>
            </div>
          )}
          <div className="flex justify-end pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700"
            >
              Schließen
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-gray-900">Neuen Vermieter anlegen</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              placeholder="Max Mustermann GmbH"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">E-Mail</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="vermieter@beispiel.de"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <p className="text-xs text-gray-400">
            Ein Keycloak-Konto wird automatisch erstellt und ein temporäres Passwort generiert.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Wird angelegt…' : 'Anlegen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Document list subcomponent
// ---------------------------------------------------------------------------

// Tag-Badge (einzelner Tag als Chip)
function TagBadge({ name, onRemove }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
      {name}
      {onRemove && (
        <button onClick={onRemove} className="ml-0.5 hover:text-red-500 leading-none">&times;</button>
      )}
    </span>
  )
}

// Tag-Eingabefeld mit Autocomplete
function TagInput({ value, onChange }) {
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSugg, setShowSugg] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    if (!input.trim()) { setSuggestions([]); return }
    const timer = setTimeout(() => {
      searchTags(input.trim())
        .then((r) => setSuggestions((r.data || []).map((t) => t.name).filter((n) => !value.includes(n))))
        .catch(() => {})
    }, 150)
    return () => clearTimeout(timer)
  }, [input, value])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setShowSugg(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const addTag = (tag) => {
    const t = tag.trim()
    if (t && !value.includes(t)) onChange([...value, t])
    setInput('')
    setSuggestions([])
    setShowSugg(false)
  }

  const removeTag = (tag) => onChange(value.filter((t) => t !== tag))

  return (
    <div ref={wrapRef} className="relative flex-1 min-w-0">
      <div className="flex flex-wrap gap-1 items-center border border-gray-300 rounded-md px-2 py-1.5 min-h-[34px] focus-within:ring-2 focus-within:ring-blue-500 bg-white">
        {value.map((tag) => (
          <TagBadge key={tag} name={tag} onRemove={() => removeTag(tag)} />
        ))}
        <input
          value={input}
          onChange={(e) => { setInput(e.target.value); setShowSugg(true) }}
          onKeyDown={(e) => {
            if ((e.key === 'Enter' || e.key === ',') && input.trim()) { e.preventDefault(); addTag(input) }
            if (e.key === 'Backspace' && !input && value.length) removeTag(value[value.length - 1])
          }}
          onFocus={() => input.trim() && setShowSugg(true)}
          placeholder={value.length === 0 ? 'Tags eingeben und Enter drücken…' : ''}
          className="flex-1 min-w-20 outline-none text-sm bg-transparent"
        />
      </div>
      {showSugg && suggestions.length > 0 && (
        <ul className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
          {suggestions.map((s) => (
            <li
              key={s}
              onMouseDown={(e) => { e.preventDefault(); addTag(s) }}
              className="px-3 py-1.5 text-sm hover:bg-blue-50 cursor-pointer"
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// DocumentsTab
// ---------------------------------------------------------------------------

function DocumentsTab({ landlordId }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [description, setDescription] = useState('')
  const [newTags, setNewTags] = useState([])
  const [filterTag, setFilterTag] = useState('')
  const [error, setError] = useState('')
  // editId: which doc is being edited; editTags/editDesc: current edit state
  const [editId, setEditId] = useState(null)
  const [editTags, setEditTags] = useState([])
  const [editDesc, setEditDesc] = useState('')
  const [saving, setSaving] = useState(false)
  const fileRef = useRef(null)

  const refresh = () => {
    setLoading(true)
    listDocuments(landlordId)
      .then((r) => setDocs(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [landlordId]) // eslint-disable-line react-hooks/exhaustive-deps

  const startEdit = (doc) => {
    setEditId(doc.id)
    setEditTags((doc.tags || []).map((t) => t.name))
    setEditDesc(doc.description || '')
  }

  const cancelEdit = () => { setEditId(null); setEditTags([]); setEditDesc('') }

  const saveEdit = async (docId) => {
    setSaving(true)
    try {
      const res = await updateDocument(landlordId, docId, { tags: editTags, description: editDesc || null })
      setDocs((prev) => prev.map((d) => d.id === docId ? res.data : d))
      cancelEdit()
    } catch {
      setError('Speichern fehlgeschlagen.')
    } finally {
      setSaving(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      await uploadDocument(landlordId, file, description || undefined, newTags)
      setDescription('')
      setNewTags([])
      refresh()
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload fehlgeschlagen.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (docId) => {
    if (!window.confirm('Dokument wirklich löschen?')) return
    try {
      await deleteDocument(landlordId, docId)
      setDocs((prev) => prev.filter((d) => d.id !== docId))
    } catch {
      setError('Löschen fehlgeschlagen.')
    }
  }

  const handleDownload = async (doc) => {
    const user = await userManager.getUser()
    const url = downloadDocumentUrl(landlordId, doc.id)
    const res = await fetch(url, { headers: { Authorization: `Bearer ${user?.access_token}` } })
    if (!res.ok) { setError('Download fehlgeschlagen.'); return }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = doc.filename
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const fmt = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  // All unique tags across all documents
  const allTags = [...new Set(docs.flatMap((d) => (d.tags || []).map((t) => t.name)))].sort()
  const visible = filterTag ? docs.filter((d) => (d.tags || []).some((t) => t.name === filterTag)) : docs

  return (
    <div className="p-5 space-y-4">
      {/* Upload row */}
      <div className="flex flex-wrap items-end gap-2">
        <TagInput value={newTags} onChange={setNewTags} />
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Beschreibung (optional)"
          className="border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
        />
        <input ref={fileRef} type="file" className="hidden" onChange={handleUpload} />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 shrink-0"
        >
          <Upload className="h-3.5 w-3.5" />
          {uploading ? 'Wird hochgeladen…' : 'Hochladen'}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Tag filter chips */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setFilterTag('')}
            className={`text-xs px-2.5 py-0.5 rounded-full border transition-colors ${filterTag === '' ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-500 hover:border-blue-400'}`}
          >
            Alle ({docs.length})
          </button>
          {allTags.map((tag) => {
            const count = docs.filter((d) => (d.tags || []).some((t) => t.name === tag)).length
            return (
              <button
                key={tag}
                onClick={() => setFilterTag(filterTag === tag ? '' : tag)}
                className={`text-xs px-2.5 py-0.5 rounded-full border transition-colors ${filterTag === tag ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-500 hover:border-blue-400'}`}
              >
                {tag} ({count})
              </button>
            )
          })}
        </div>
      )}

      {/* Document list */}
      {loading ? (
        <p className="text-sm text-gray-400">Wird geladen…</p>
      ) : docs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-gray-400 gap-2">
          <Paperclip className="h-8 w-8 opacity-30" />
          <p className="text-sm">Noch keine Dokumente vorhanden.</p>
        </div>
      ) : (
        <ul className="divide-y divide-gray-100">
          {visible.map((doc) => (
            <li key={doc.id} className="py-2.5 space-y-1.5">
              {/* Row 1: icon + filename + actions */}
              <div className="flex items-start gap-3">
                <File className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{doc.filename}</p>
                  <p className="text-xs text-gray-400">
                    {fmt(doc.size_bytes)} · {new Date(doc.uploaded_at).toLocaleString('de-DE')}
                    {doc.description && editId !== doc.id && ` · ${doc.description}`}
                  </p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {editId === doc.id ? (
                    <>
                      <button
                        onClick={() => saveEdit(doc.id)}
                        disabled={saving}
                        className="p-1.5 text-gray-400 hover:text-green-600 rounded disabled:opacity-50"
                        title="Speichern"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="p-1.5 text-gray-400 hover:text-gray-700 rounded"
                        title="Abbrechen"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => startEdit(doc)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 rounded"
                      title="Tags bearbeiten"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={() => handleDownload(doc)}
                    className="p-1.5 text-gray-400 hover:text-blue-600 rounded"
                    title="Herunterladen"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1.5 text-gray-400 hover:text-red-600 rounded"
                    title="Löschen"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Row 2: edit mode OR tag badges */}
              {editId === doc.id ? (
                <div className="ml-8 flex flex-wrap items-center gap-2">
                  <TagInput value={editTags} onChange={setEditTags} />
                  <input
                    type="text"
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    placeholder="Beschreibung"
                    className="border border-gray-300 rounded-md px-2.5 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-44"
                  />
                </div>
              ) : (doc.tags || []).length > 0 && (
                <div className="ml-8 flex flex-wrap gap-1">
                  {doc.tags.map((t) => <TagBadge key={t.id} name={t.name} />)}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Detail Panel
// ---------------------------------------------------------------------------

const EMPTY_PROFILE = {
  phone: '',
  website: '',
  company_name: '',
  address_street: '',
  address_city: '',
  address_zip: '',
  address_country: 'Deutschland',
  tax_id: '',
  vat_id: '',
  iban: '',
  notes: '',
}

function ProfilePanel({ landlord, onProfileSaved, onClose }) {
  const existingProfile = landlord.profile ?? {}
  const [tab, setTab] = useState('profile') // 'profile' | 'documents'
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ ...EMPTY_PROFILE, ...existingProfile })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Sync when switching landlords
  useEffect(() => {
    setForm({ ...EMPTY_PROFILE, ...(landlord.profile ?? {}) })
    setEditing(false)
    setError('')
    setTab('profile')
  }, [landlord.id])

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      const payload = {}
      for (const [k, v] of Object.entries(form)) {
        payload[k] = v === '' ? null : v
      }
      const res = await upsertLandlordProfile(landlord.id, payload)
      onProfileSaved(landlord.id, res.data)
      setEditing(false)
    } catch (err) {
      setError(err.response?.data?.detail || 'Fehler beim Speichern.')
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    'w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const readClass = 'text-sm text-gray-800 py-1'

  const renderField = (key, placeholder = '') => {
    const val = form[key]
    if (editing) {
      return (
        <input
          value={val ?? ''}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          placeholder={placeholder}
          className={key === 'iban' ? `${inputClass} font-mono tracking-wider` : inputClass}
        />
      )
    }
    return <p className={readClass}>{val || <span className="text-gray-400 italic">—</span>}</p>
  }

  const renderTextarea = (key, placeholder = '') => {
    if (editing) {
      return (
        <textarea
          value={form[key] ?? ''}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          placeholder={placeholder}
          rows={3}
          className="w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      )
    }
    return (
      <p className={`${readClass} whitespace-pre-wrap`}>
        {form[key] || <span className="text-gray-400 italic">—</span>}
      </p>
    )
  }

  const toggleActive = async () => {
    await updateLandlord(landlord.id, { is_active: !landlord.is_active })
    onProfileSaved(landlord.id, landlord.profile, { is_active: !landlord.is_active })
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
            <User className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-sm leading-tight">{landlord.full_name}</p>
            <p className="text-xs text-gray-500">{landlord.email}</p>
          </div>
          <Badge active={landlord.is_active} />
        </div>
        <div className="flex items-center gap-2">
          {tab === 'profile' && (
            editing ? (
              <>
                <button
                  onClick={() => { setForm({ ...EMPTY_PROFILE, ...(landlord.profile ?? {}) }); setEditing(false) }}
                  className="text-xs px-3 py-1.5 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100"
                >
                  Abbrechen
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="text-xs px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Speichern…' : 'Speichern'}
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100"
              >
                <Pencil className="h-3.5 w-3.5" />
                Bearbeiten
              </button>
            )
          )}
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 ml-1"
            title="Panel schließen"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 bg-white">
        {[
          { id: 'profile', label: 'Stammdaten', icon: User },
          { id: 'documents', label: 'Dokumente', icon: Paperclip },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="px-5 py-2 bg-red-50 border-b border-red-100 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Tab Content */}
      {tab === 'documents' ? (
        <DocumentsTab landlordId={landlord.id} />
      ) : (
        <>
      <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-4">
        {/* Firma */}
        <Field label="Firmenname" icon={Building2}>
          {renderField('company_name', 'Mustermann Immobilien GmbH')}
        </Field>

        {/* Kontakt */}
        <Field label="Telefon" icon={Phone}>
          {renderField('phone', '+49 89 12345678')}
        </Field>
        <Field label="Website" icon={Globe}>
          {renderField('website', 'https://example.de')}
        </Field>

        {/* Adresse */}
        <Field label="Straße & Hausnr." icon={MapPin}>
          {renderField('address_street', 'Musterstraße 1')}
        </Field>
        <Field label="PLZ / Ort">
          {editing ? (
            <div className="flex gap-2">
              <input
                value={form.address_zip ?? ''}
                onChange={(e) => setForm({ ...form, address_zip: e.target.value })}
                placeholder="80331"
                className="w-24 border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                value={form.address_city ?? ''}
                onChange={(e) => setForm({ ...form, address_city: e.target.value })}
                placeholder="München"
                className="flex-1 border border-gray-300 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ) : (
            <p className="text-sm text-gray-800 py-1">
              {form.address_zip || form.address_city
                ? `${form.address_zip ?? ''} ${form.address_city ?? ''}`.trim()
                : <span className="text-gray-400 italic">—</span>}
            </p>
          )}
        </Field>
        <Field label="Land">
          {renderField('address_country', 'Deutschland')}
        </Field>

        {/* Steuer / Recht */}
        <Field label="Steuernummer" icon={Receipt}>
          {renderField('tax_id', '123/456/78901')}
        </Field>
        <Field label="USt-IdNr." icon={Receipt}>
          {renderField('vat_id', 'DE123456789')}
        </Field>
        <Field label="IBAN" icon={CreditCard}>
          {renderField('iban', 'DE89 3704 0044 0532 0130 00')}
        </Field>

        {/* Notizen (volle Breite) */}
        <div className="col-span-full">
          <Field label="Interne Notizen (nur für Admins)" icon={FileText}>
            {renderTextarea('notes', 'Freitext für interne Notizen…')}
          </Field>
        </div>
      </div>

      <div className="px-5 pb-3 text-xs text-gray-400 flex gap-4">
        {landlord.profile?.updated_at && (
          <span>
            Profil zuletzt geändert:{' '}
            {new Date(landlord.profile.updated_at).toLocaleString('de-DE')}
          </span>
        )}
        <button
          onClick={toggleActive}
          className={`flex items-center gap-1 ${
            landlord.is_active
              ? 'text-orange-500 hover:text-orange-700'
              : 'text-green-600 hover:text-green-700'
          }`}
        >
          {landlord.is_active ? (
            <><ToggleRight className="h-4 w-4" /> Deaktivieren</>
          ) : (
            <><ToggleLeft className="h-4 w-4" /> Aktivieren</>
          )}
        </button>
      </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function LandlordsPage() {
  const [landlords, setLandlords] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null) // landlord id
  const searchRef = useRef(null)

  useEffect(() => {
    getLandlords()
      .then((r) => setLandlords(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleCreated = (newLandlord) => {
    setLandlords((prev) => [...prev, newLandlord])
    setSelected(newLandlord.id)
  }

  // Update landlord user and/or profile data in local state
  const handleProfileSaved = (id, profile, userPatch = {}) => {
    setLandlords((prev) =>
      prev.map((l) =>
        l.id === id ? { ...l, ...userPatch, profile } : l
      )
    )
  }

  const filtered = landlords.filter((l) => {
    const q = search.toLowerCase()
    return (
      l.full_name.toLowerCase().includes(q) ||
      l.email.toLowerCase().includes(q) ||
      (l.profile?.company_name ?? '').toLowerCase().includes(q)
    )
  })

  const selectedLandlord = landlords.find((l) => l.id === selected) ?? null

  return (
    <div className="space-y-4">
      {/* ── Page header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Vermieter (Mandanten)</h1>
          <p className="text-sm text-gray-500 mt-1">Alle registrierten Vermieter auf der Plattform</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Vermieter anlegen
        </button>
      </div>

      {/* ── Search ──────────────────────────────────────────────────────────── */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
        <input
          ref={searchRef}
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Suche nach Name, E-Mail oder Firma…"
          className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* ── List ────────────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-400">Wird geladen…</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">
            {search
              ? 'Keine Ergebnisse für diese Suche.'
              : 'Noch keine Vermieter vorhanden. Lege den ersten Mandanten an.'}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Name</th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide hidden sm:table-cell">E-Mail</th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide hidden md:table-cell">Firma</th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide hidden lg:table-cell">Angelegt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((l) => (
                <tr
                  key={l.id}
                  onClick={() => setSelected(l.id === selected ? null : l.id)}
                  className={`cursor-pointer transition-colors ${
                    l.id === selected
                      ? 'bg-blue-50 hover:bg-blue-50'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{l.full_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 hidden sm:table-cell">{l.email}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 hidden md:table-cell">
                    {l.profile?.company_name || <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <Badge active={l.is_active} />
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400 hidden lg:table-cell">
                    {new Date(l.created_at).toLocaleDateString('de-DE')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Detail Panel ────────────────────────────────────────────────────── */}
      {selectedLandlord && (
        <ProfilePanel
          landlord={selectedLandlord}
          onProfileSaved={handleProfileSaved}
          onClose={() => setSelected(null)}
        />
      )}

      {/* ── Modals ──────────────────────────────────────────────────────────── */}
      {showCreate && (
        <CreateModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
    </div>
  )
}

