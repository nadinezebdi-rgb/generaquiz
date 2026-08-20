import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Search, Loader2, ShieldCheck, ShieldOff, Users as UsersIcon, Crown } from "lucide-react";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

/**
 * AdminUsers — liste des utilisateurs + gestion des rôles.
 *
 * - Visible pour tout admin (et superadmin) pour la CONSULTATION.
 * - Le bouton "Promouvoir/Rétrograder" n'est actif que pour un SUPERADMIN.
 * - Impossible via l'UI de modifier son propre rôle ou celui d'un superadmin.
 */
export default function AdminUsers() {
  const { user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";

  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [pendingId, setPendingId] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (q) params.set("q", q);
      if (roleFilter) params.set("role", roleFilter);
      const { data } = await api.get(`/admin/users?${params.toString()}`);
      setUsers(data.users || []);
      setTotal(data.total || 0);
    } catch (e) {
      toast.error(formatError(e?.response?.data?.detail) || "Impossible de charger les utilisateurs");
    } finally {
      setLoading(false);
    }
  }, [q, roleFilter]);

  useEffect(() => { refresh(); }, [refresh]);

  async function changeRole(u, newRole) {
    if (!isSuperadmin) return;
    const label = newRole === "admin" ? `Promouvoir ${u.email} en administrateur ?` : `Rétrograder ${u.email} en simple utilisateur ?`;
    if (!window.confirm(label)) return;
    setPendingId(u.id);
    try {
      await api.post(`/admin/users/${u.id}/role`, { role: newRole });
      toast.success(newRole === "admin" ? "Utilisateur promu admin ✅" : "Utilisateur rétrogradé user");
      await refresh();
    } catch (e) {
      toast.error(formatError(e?.response?.data?.detail) || "Action refusée");
    } finally {
      setPendingId(null);
    }
  }

  const counts = useMemo(() => {
    const c = { superadmin: 0, admin: 0, user: 0, other: 0 };
    for (const u of users) {
      if (c[u.role] != null) c[u.role]++;
      else c.other++;
    }
    return c;
  }, [users]);

  return (
    <div className="min-h-screen bg-cream text-navy">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="admin-users-page">
        <header className="mb-6">
          <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
            <UsersIcon className="w-3.5 h-3.5" /> Administration · Utilisateurs
          </span>
          <h1 className="font-display text-4xl font-extrabold">Utilisateurs & rôles</h1>
          <p className="text-navy/70 mt-2">
            {total} utilisateur{total > 1 ? "s" : ""} · {counts.admin} admin{counts.admin > 1 ? "s" : ""} · {counts.superadmin} super-admin
            {isSuperadmin
              ? <span className="ml-2 text-terracotta font-bold">Vous êtes super-administrateur</span>
              : <span className="ml-2 text-navy/50">(consultation seule — seul un super-administrateur peut changer un rôle)</span>}
          </p>
        </header>

        <div className="bg-white border-2 border-cream-dark rounded-2xl p-4 mb-4 flex flex-wrap items-center gap-3" data-testid="admin-users-filters">
          <div className="flex items-center gap-2 flex-1 min-w-[220px] border-2 border-cream-dark rounded-full px-3">
            <Search className="w-4 h-4 text-navy/40" />
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Rechercher email ou nom"
              className="flex-1 py-2 outline-none bg-transparent"
              data-testid="admin-users-search"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            data-testid="admin-users-role-filter"
            className="border-2 border-cream-dark rounded-full px-4 py-2 bg-white outline-none"
          >
            <option value="">Tous les rôles</option>
            <option value="superadmin">superadmin</option>
            <option value="admin">admin</option>
            <option value="user">user</option>
          </select>
        </div>

        {loading ? (
          <div className="text-center py-10 text-navy/60 inline-flex items-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin" /> Chargement…
          </div>
        ) : (
          <div className="bg-white border-2 border-cream-dark rounded-2xl overflow-hidden" data-testid="admin-users-list">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-cream border-b-2 border-cream-dark">
                  <tr>
                    <th className="text-left px-4 py-3 font-bold">Utilisateur</th>
                    <th className="text-left px-4 py-3 font-bold">Rôle</th>
                    <th className="text-left px-4 py-3 font-bold">Plan</th>
                    <th className="text-left px-4 py-3 font-bold">Inscrit le</th>
                    <th className="text-right px-4 py-3 font-bold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isSelf = u.id === user?.id;
                    const isSuperTarget = u.role === "superadmin";
                    const busy = pendingId === u.id;
                    const canChange = isSuperadmin && !isSelf && !isSuperTarget;
                    return (
                      <tr key={u.id} data-testid={`admin-user-row-${u.id}`} className="border-b border-cream-dark last:border-0 hover:bg-cream/40">
                        <td className="px-4 py-3">
                          <div className="font-bold">{u.name || <span className="italic text-navy/50">Sans nom</span>}</div>
                          <div className="text-xs text-navy/60">{u.email}</div>
                        </td>
                        <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
                        <td className="px-4 py-3">
                          <span className="text-xs">{u.plan_tier || u.plan || "—"}</span>
                          {u.plan_period && <span className="text-xs text-navy/50"> · {u.plan_period}</span>}
                        </td>
                        <td className="px-4 py-3 text-xs text-navy/60">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString("fr-FR") : "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {canChange && u.role !== "admin" && (
                            <button
                              type="button"
                              onClick={() => changeRole(u, "admin")}
                              disabled={busy}
                              data-testid={`admin-user-promote-${u.id}`}
                              className="inline-flex items-center gap-1 bg-terracotta text-white text-xs font-bold px-3 py-1.5 rounded-full hover:bg-terracotta-dark disabled:opacity-50 transition"
                            >
                              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                              Promouvoir admin
                            </button>
                          )}
                          {canChange && u.role === "admin" && (
                            <button
                              type="button"
                              onClick={() => changeRole(u, "user")}
                              disabled={busy}
                              data-testid={`admin-user-demote-${u.id}`}
                              className="inline-flex items-center gap-1 bg-navy text-cream text-xs font-bold px-3 py-1.5 rounded-full hover:bg-navy-dark disabled:opacity-50 transition"
                            >
                              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldOff className="w-3.5 h-3.5" />}
                              Rétrograder
                            </button>
                          )}
                          {isSelf && <span className="text-xs text-navy/40 italic">Vous-même</span>}
                          {isSuperTarget && !isSelf && <span className="text-xs text-navy/40 italic">Verrouillé (super)</span>}
                          {!isSuperadmin && !isSelf && !isSuperTarget && <span className="text-xs text-navy/30">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                  {users.length === 0 && (
                    <tr><td colSpan={5} className="text-center py-10 text-navy/50">Aucun utilisateur trouvé.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}

function RoleBadge({ role }) {
  const styles = {
    superadmin: { bg: "bg-terracotta text-white", icon: Crown, label: "Super-admin" },
    admin:      { bg: "bg-bordeaux text-white",   icon: ShieldCheck, label: "Admin" },
    user:       { bg: "bg-cream border-2 border-cream-dark text-navy/70", icon: null, label: "User" },
  };
  const s = styles[role] || styles.user;
  const Icon = s.icon;
  return (
    <span data-testid={`role-badge-${role}`} className={`inline-flex items-center gap-1 font-bold text-[11px] uppercase tracking-widest px-2 py-1 rounded-full ${s.bg}`}>
      {Icon && <Icon className="w-3 h-3" />} {s.label}
    </span>
  );
}
