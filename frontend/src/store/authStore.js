/**
 * Minimal Zustand store for the backend user profile.
 *
 * The OIDC token lifecycle (login, logout, refresh) is fully managed by
 * react-oidc-context / oidc-client-ts.  This store only caches the user
 * profile returned by our own backend (/api/v1/auth/me) so we can read the
 * role and name without an extra round-trip on every render.
 */
import { create } from 'zustand'

export const useUserStore = create((set) => ({
  profile: null,           // { id, email, full_name, role, is_active, created_at }
  setProfile: (p) => set({ profile: p }),
  clearProfile: () => set({ profile: null }),
}))
