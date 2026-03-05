import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthGate } from './components/layout/AuthGate'
import { AppShell } from './components/layout/AppShell'
import { useUserStore } from './store/authStore'

// Lazy-load pages
import { lazy, Suspense } from 'react'
import { Spinner } from './components/ui'

const LandlordDashboard   = lazy(() => import('./pages/landlord/LandlordDashboard'))
const PropertiesPage      = lazy(() => import('./pages/landlord/PropertiesPage'))
const ContractsPage       = lazy(() => import('./pages/landlord/ContractsPage'))
const BillsPage           = lazy(() => import('./pages/landlord/BillsPage'))
const TenantsPage         = lazy(() => import('./pages/landlord/TenantsPage'))
const BillingGraphPage    = lazy(() => import('./pages/landlord/BillingGraphPage'))
const TenantDashboard     = lazy(() => import('./pages/tenant/TenantDashboard'))
const TenantContractsPage = lazy(() => import('./pages/tenant/TenantContractsPage'))
const TenantBillsPage     = lazy(() => import('./pages/tenant/TenantBillsPage'))
const MeterReadingsPage   = lazy(() => import('./pages/tenant/MeterReadingsPage'))

function RoleRoot() {
  const { profile } = useUserStore()
  if (!profile) return <Spinner />
  const isLandlord = profile.role === 'LANDLORD' || profile.role === 'ADMIN'
  return <Navigate to={isLandlord ? '/landlord' : '/tenant'} replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthGate>
        <AppShell>
          <Suspense fallback={<Spinner />}>
            <Routes>
              <Route path="/" element={<RoleRoot />} />

              {/* Landlord routes */}
              <Route path="/landlord" element={<LandlordDashboard />} />
              <Route path="/landlord/properties" element={<PropertiesPage />} />
              <Route path="/landlord/contracts" element={<ContractsPage />} />
              <Route path="/landlord/bills" element={<BillsPage />} />
              <Route path="/landlord/tenants" element={<TenantsPage />} />
              <Route path="/landlord/billing-graph" element={<BillingGraphPage />} />

              {/* Tenant routes */}
              <Route path="/tenant" element={<TenantDashboard />} />
              <Route path="/tenant/contracts" element={<TenantContractsPage />} />
              <Route path="/tenant/bills" element={<TenantBillsPage />} />
              <Route path="/tenant/meter-readings" element={<MeterReadingsPage />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </AppShell>
      </AuthGate>
    </BrowserRouter>
  )
}
