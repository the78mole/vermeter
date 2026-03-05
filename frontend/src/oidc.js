/**
 * OIDC configuration for Keycloak.
 *
 * The authority URL must be reachable from the **browser** (not the backend),
 * so we use the public Keycloak URL defined in VITE_KEYCLOAK_URL.
 *
 * Flow: Authorization Code + PKCE (recommended for SPAs).
 * Social logins (Google, GitHub) are configured as Identity Providers inside
 * Keycloak and appear automatically on the Keycloak login page.
 */

const KEYCLOAK_URL    = import.meta.env.VITE_KEYCLOAK_URL    || 'http://localhost:8081'
const KEYCLOAK_REALM  = import.meta.env.VITE_KEYCLOAK_REALM  || 'rental'
const KEYCLOAK_CLIENT = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'rental-frontend'

export const oidcConfig = {
  authority: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}`,
  client_id: KEYCLOAK_CLIENT,
  redirect_uri: window.location.origin + '/',
  post_logout_redirect_uri: window.location.origin + '/',
  scope: 'openid profile email',
  // PKCE is the default in oidc-client-ts
  // Automatically renew tokens in the background using a hidden iframe / refresh token
  automaticSilentRenew: true,
  loadUserInfo: true,
  // Response type: code (PKCE)
  response_type: 'code',
}
