/**
 * AuthGate – handles OIDC auth state for the whole app.
 *
 * States:
 *   loading      → show a spinner (OIDC is initialising or processing callback)
 *   not authed   → redirect to Keycloak login page
 *   authed       → fetch backend profile (JIT provision), render children
 *
 * The Keycloak login page shows Username/Password + any enabled Social
 * Identity Providers (Google, GitHub) configured in the realm.
 */
import { useEffect } from 'react'
import { useAuth } from 'react-oidc-context'
import { getMe } from '../../api/client'
import { useUserStore } from '../../store/authStore'
import { Building2 } from 'lucide-react'

export function AuthGate({ children }) {
  const auth = useAuth()
  const { profile, setProfile } = useUserStore()

  // Fetch backend profile once we have a valid OIDC session
  useEffect(() => {
    if (auth.isAuthenticated && !profile) {
      getMe()
        .then((res) => setProfile(res.data))
        .catch(() => {/* retry on next render */})
    }
    if (!auth.isAuthenticated) {
      setProfile(null)
    }
  }, [auth.isAuthenticated, profile, setProfile])

  // ── Loading / callback processing ────────────────────────────────────────
  if (auth.isLoading) {
    return <OIDCLoadingScreen message="Authentifizierung wird geprüft…" />
  }

  // ── OIDC error ────────────────────────────────────────────────────────────
  if (auth.error) {
    return (
      <OIDCLoadingScreen
        message={`Anmeldefehler: ${auth.error.message}`}
        action={() => auth.signinRedirect()}
        actionLabel="Erneut anmelden"
      />
    )
  }

  // ── Not authenticated → redirect to Keycloak ────────────────────────────
  if (!auth.isAuthenticated) {
    auth.signinRedirect()
    return <OIDCLoadingScreen message="Weiterleitung zur Anmeldung…" />
  }

  // ── Authenticated but backend profile not loaded yet ────────────────────
  if (!profile) {
    return <OIDCLoadingScreen message="Profil wird geladen…" />
  }

  return children
}

function OIDCLoadingScreen({ message, action, actionLabel }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100 gap-6">
      <div className="bg-blue-600 p-4 rounded-2xl shadow-lg">
        <Building2 className="h-10 w-10 text-white" />
      </div>
      <p className="text-gray-600 text-sm font-medium">{message}</p>
      {!action && (
        <div className="h-6 w-6 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      )}
      {action && (
        <button
          onClick={action}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
