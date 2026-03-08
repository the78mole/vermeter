import { useEffect, useState } from "react";
import {
  Check,
  ChevronDown,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
  UserCog,
  X,
} from "lucide-react";
import {
  listAdminUsers,
  createAdminUser,
  updateAdminUser,
  deleteAdminUser,
} from "../../api/client";
import { useUserStore } from "../../store/authStore";

// ---------------------------------------------------------------------------
// Role config
// ---------------------------------------------------------------------------

const ADMIN_ROLES = [
  {
    value: "SUPER_ADMIN",
    label: "Super-Admin",
    color: "bg-purple-100 text-purple-700",
    desc: "Kann alle Admin-Benutzer verwalten",
  },
  {
    value: "ADMIN",
    label: "Admin",
    color: "bg-blue-100 text-blue-700",
    desc: "Kann Admins und Operatoren verwalten",
  },
  {
    value: "OPERATOR",
    label: "Operator",
    color: "bg-green-100 text-green-700",
    desc: "Kann nur Mandanten verwalten",
  },
];

function RoleBadge({ adminRole }) {
  const meta = ADMIN_ROLES.find((r) => r.value === adminRole);
  if (!meta) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${meta.color}`}
    >
      <ShieldCheck className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Create Dialog
// ---------------------------------------------------------------------------

function CreateDialog({ currentAdminRole, onCreated, onClose }) {
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    admin_role: "OPERATOR",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  // ADMIN can create ADMIN + OPERATOR, SUPER_ADMIN can create all
  const allowedRoles =
    currentAdminRole === "SUPER_ADMIN"
      ? ADMIN_ROLES
      : ADMIN_ROLES.filter(
          (r) => r.value === "ADMIN" || r.value === "OPERATOR",
        );

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const res = await createAdminUser(form);
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Fehler beim Anlegen.");
    } finally {
      setSaving(false);
    }
  };

  if (result) {
    return (
      <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
          <div className="flex items-center gap-2 text-green-700">
            <Check className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Benutzer angelegt</h2>
          </div>
          <p className="text-sm text-gray-600">
            <strong>{result.email}</strong> wurde erfolgreich als{" "}
            <RoleBadge adminRole={result.admin_role} /> angelegt.
          </p>
          {result.temp_password && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-xs font-medium text-yellow-800 mb-1">
                Temporäres Passwort (einmalig sichtbar):
              </p>
              <code className="text-sm font-mono text-yellow-900 break-all">
                {result.temp_password}
              </code>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button
              onClick={() => {
                onCreated(result);
                onClose();
              }}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Schließen
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            Admin-Benutzer anlegen
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              E-Mail
            </label>
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              required
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Rolle
            </label>
            <div className="space-y-2">
              {allowedRoles.map((r) => (
                <label
                  key={r.value}
                  className="flex items-start gap-2.5 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="admin_role"
                    value={r.value}
                    checked={form.admin_role === r.value}
                    onChange={() => setForm({ ...form, admin_role: r.value })}
                    className="mt-0.5"
                  />
                  <div>
                    <RoleBadge adminRole={r.value} />
                    <p className="text-xs text-gray-500 mt-0.5">{r.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Wird angelegt…" : "Anlegen"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Row
// ---------------------------------------------------------------------------

function UserRow({ user, currentUser, onUpdated, onDeleted }) {
  const [editing, setEditing] = useState(false);
  const [editRole, setEditRole] = useState(user.admin_role);
  const [editActive, setEditActive] = useState(user.is_active);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState(false);

  const isSelf = user.id === currentUser?.id;
  const canManage =
    currentUser?.admin_role === "SUPER_ADMIN" ||
    (currentUser?.admin_role === "ADMIN" &&
      (user.admin_role === "ADMIN" || user.admin_role === "OPERATOR"));

  const saveEdit = async () => {
    setSaving(true);
    try {
      const res = await updateAdminUser(user.id, {
        admin_role: editRole,
        is_active: editActive,
      });
      onUpdated(res.data);
      setEditing(false);
    } catch {
      // keep editing open
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`${user.full_name} (${user.email}) wirklich löschen?`))
      return;
    try {
      await deleteAdminUser(user.id);
      onDeleted(user.id);
    } catch {
      // ignore
    }
  };

  // Allowed roles for editing (ADMIN can't assign SUPER_ADMIN)
  const editableRoles =
    currentUser?.admin_role === "SUPER_ADMIN"
      ? ADMIN_ROLES
      : ADMIN_ROLES.filter(
          (r) => r.value === "ADMIN" || r.value === "OPERATOR",
        );

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
        <p className="text-xs text-gray-500">{user.email}</p>
        {isSelf && (
          <span className="text-xs text-blue-600 font-medium">Ich</span>
        )}
      </td>
      <td className="px-4 py-3">
        {editing ? (
          <div className={`relative ${open ? "z-40" : ""}`}>
            <button
              type="button"
              onClick={() => setOpen(!open)}
              className="flex items-center gap-1 border border-gray-300 rounded-md px-2 py-1 text-sm bg-white"
            >
              <RoleBadge adminRole={editRole} />
              <ChevronDown className="h-3 w-3 text-gray-400" />
            </button>
            {open && (
              <div className="absolute left-0 z-50 mt-1 min-w-max bg-white border border-gray-200 rounded-md shadow-lg">
                {editableRoles.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    onClick={() => {
                      setEditRole(r.value);
                      setOpen(false);
                    }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-gray-50 text-left"
                  >
                    <RoleBadge adminRole={r.value} />
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <RoleBadge adminRole={user.admin_role} />
        )}
      </td>
      <td className="px-4 py-3">
        {editing ? (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={editActive}
              onChange={(e) => setEditActive(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-gray-600">Aktiv</span>
          </label>
        ) : (
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${user.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
          >
            {user.is_active ? "Aktiv" : "Deaktiviert"}
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-gray-400">
        {new Date(user.created_at).toLocaleDateString("de-DE")}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1">
          {canManage &&
            !isSelf &&
            (editing ? (
              <>
                <button
                  onClick={saveEdit}
                  disabled={saving}
                  className="p-1.5 text-gray-400 hover:text-green-600 rounded disabled:opacity-50"
                  title="Speichern"
                >
                  <Check className="h-4 w-4" />
                </button>
                <button
                  onClick={() => {
                    setEditing(false);
                    setEditRole(user.admin_role);
                    setEditActive(user.is_active);
                  }}
                  className="p-1.5 text-gray-400 hover:text-gray-700 rounded"
                  title="Abbrechen"
                >
                  <X className="h-4 w-4" />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setEditing(true)}
                  className="p-1.5 text-gray-400 hover:text-blue-600 rounded"
                  title="Bearbeiten"
                >
                  <Pencil className="h-4 w-4" />
                </button>
                {currentUser?.admin_role === "SUPER_ADMIN" && (
                  <button
                    onClick={handleDelete}
                    className="p-1.5 text-gray-400 hover:text-red-600 rounded"
                    title="Löschen"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </>
            ))}
        </div>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminUsersPage() {
  const { profile } = useUserStore();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const load = () => {
    setLoading(true);
    listAdminUsers()
      .then((r) => setUsers(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreated = (newUser) => setUsers((prev) => [...prev, newUser]);
  const handleUpdated = (updated) =>
    setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
  const handleDeleted = (id) =>
    setUsers((prev) => prev.filter((u) => u.id !== id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <UserCog className="h-6 w-6 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Admin-Benutzerverwaltung
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Super-Admins, Admins und Operatoren verwalten
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Neuer Benutzer
        </button>
      </div>

      {/* Role info cards */}
      <div className="grid grid-cols-3 gap-4">
        {ADMIN_ROLES.map((r) => {
          const count = users.filter((u) => u.admin_role === r.value).length;
          return (
            <div
              key={r.value}
              className="bg-white rounded-xl border border-gray-200 p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <RoleBadge adminRole={r.value} />
                <span className="text-2xl font-bold text-gray-900">
                  {count}
                </span>
              </div>
              <p className="text-xs text-gray-500">{r.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-visible">
        {loading ? (
          <p className="p-6 text-sm text-gray-400">Wird geladen…</p>
        ) : users.length === 0 ? (
          <p className="p-6 text-sm text-gray-400">
            Keine Admin-Benutzer gefunden.
          </p>
        ) : (
          <table className="w-full text-left">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Name / E-Mail
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Rolle
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Status
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Erstellt
                </th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <UserRow
                  key={u.id}
                  user={u}
                  currentUser={profile}
                  onUpdated={handleUpdated}
                  onDeleted={handleDeleted}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreateDialog
          currentAdminRole={profile?.admin_role}
          onCreated={handleCreated}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}
