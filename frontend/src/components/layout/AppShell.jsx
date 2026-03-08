import { NavLink } from "react-router-dom";
import { useAuth } from "react-oidc-context";
import { useUserStore } from "../../store/authStore";
import {
  Home,
  FileText,
  Zap,
  BarChart2,
  LogOut,
  Building2,
  Users,
  ShieldCheck,
  LayoutDashboard,
  UserCog,
} from "lucide-react";
import { cn } from "../../lib/utils";

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
          isActive
            ? "bg-blue-50 text-blue-700"
            : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
        )
      }
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      {label}
    </NavLink>
  );
}

export function AppShell({ children }) {
  const { profile } = useUserStore();
  const auth = useAuth();

  const handleLogout = () => {
    auth.removeUser();
    auth.signoutRedirect();
  };

  const isLandlord =
    profile?.role === "LANDLORD" || profile?.role === "CARETAKER";
  const isCaretaker = profile?.role === "CARETAKER";
  const isAdmin = profile?.role === "ADMIN";
  const isOperator = isAdmin && profile?.admin_role === "OPERATOR";
  const isAdminManager =
    isAdmin &&
    (profile?.admin_role === "ADMIN" || profile?.admin_role === "SUPER_ADMIN");

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="px-4 py-5 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Building2 className="h-6 w-6 text-blue-600" />
            <span className="font-bold text-gray-900 text-lg">
              RentalManager
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1 truncate">
            {profile?.email}
          </p>
          {isAdmin && (
            <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 text-xs font-medium">
              <ShieldCheck className="h-3 w-3" />
              {profile?.admin_role === "SUPER_ADMIN"
                ? "Super-Admin"
                : profile?.admin_role === "ADMIN"
                  ? "Admin"
                  : "Operator"}
            </span>
          )}
          {isCaretaker && (
            <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">
              <ShieldCheck className="h-3 w-3" />
              Hausverwalter
            </span>
          )}
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {isAdmin ? (
            <>
              {isAdminManager && (
                <NavItem to="/admin" icon={LayoutDashboard} label="Übersicht" />
              )}
              <NavItem
                to="/admin/landlords"
                icon={Building2}
                label="Vermieter (Mandanten)"
              />
              {isAdminManager && (
                <NavItem
                  to="/admin/users"
                  icon={UserCog}
                  label="Admin-Benutzer"
                />
              )}
            </>
          ) : isLandlord ? (
            <>
              <NavItem to="/landlord" icon={Home} label="Übersicht" />
              <NavItem
                to="/landlord/properties"
                icon={Building2}
                label="Immobilien"
              />
              <NavItem
                to="/landlord/contracts"
                icon={FileText}
                label="Mietverträge"
              />
              <NavItem
                to="/landlord/bills"
                icon={BarChart2}
                label="Nebenkostenabrechnungen"
              />
              <NavItem to="/landlord/tenants" icon={Users} label="Mieter" />
              <NavItem
                to="/landlord/billing-graph"
                icon={Zap}
                label="Abrechnungs-Editor"
              />
            </>
          ) : (
            <>
              <NavItem to="/tenant" icon={Home} label="Dashboard" />
              <NavItem
                to="/tenant/contracts"
                icon={FileText}
                label="Mein Mietvertrag"
              />
              <NavItem
                to="/tenant/bills"
                icon={BarChart2}
                label="Nebenkostenabrechnungen"
              />
              <NavItem
                to="/tenant/meter-readings"
                icon={Zap}
                label="Zählerstand einreichen"
              />
            </>
          )}
        </nav>

        <div className="px-3 pb-4">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Abmelden
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">{children}</div>
      </main>
    </div>
  );
}
