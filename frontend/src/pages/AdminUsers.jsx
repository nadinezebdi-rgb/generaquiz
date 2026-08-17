import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import { Users, Copy, Check, Loader2, Shield, Crown } from "lucide-react";

export default function AdminUsers() {
  const { user, loading } = useAuth();
  const [users, setUsers] = useState([]);
  const [count, setCount] = useState(0);
  const [fetching, setFetching] = useState(true);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);

  const fetchUsers = async () => {
    try {
      const { data } = await api.get("/admin/users");
      setUsers(data.users || []);
      setCount(data.count || 0);
    } catch (e) {
      setErr(e.response?.data?.detail || "Erreur");
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (user && user.role === "admin") fetchUsers();
    else if (user) setFetching(false);
  }, [user]);

  const copyEmails = async () => {
    try {
      await navigator.clipboard.writeText(users.map((u) => u.email).join(", "));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  const fmtDate = (iso) => {
    if (!iso) return "—";
    try { return new Date(iso).toLocaleDateString("fr-FR"); } catch { return "—"; }
  };

  if (loading) return <div className="min-h-screen paper-bg flex items-center justify-center text-navy text-xl">Chargement...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <main className="max-w-2xl mx-auto px-4 py-16 text-center">
          <Shield className="w-16 h-16 text-bordeaux mx-auto mb-4" />
          <h1 className="font-display text-3xl font-extrabold text-navy mb-3">Accès refusé</h1>
          <p className="text-navy/70 mb-6">Cette page est réservée aux administrateurs.</p>
          <Link to="/app/dashboard" className="bg-navy text-white font-bold px-6 py-3 rounded-full">Tableau de bord</Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-sm mb-3">
              <Shield className="w-4 h-4" /> Administration
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2">Inscrits</h1>
            <p className="text-lg text-navy/70 max-w-2xl">
              {count} utilisateur{count > 1 ? "s" : ""} inscrit{count > 1 ? "s" : ""} sur GénéraQuiz.
            </p>
          </div>
          <button
            onClick={copyEmails}
            data-testid="admin-copy-emails"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-navy text-white font-bold hover:bg-navy/90 transition"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? "Copié !" : "Copier tous les emails"}
          </button>
        </div>

        {err && <p className="text-bordeaux font-semibold mb-4">{err}</p>}

        {fetching ? (
          <div className="flex items-center gap-2 text-navy/70"><Loader2 className="w-5 h-5 animate-spin" /> Chargement des inscrits...</div>
        ) : users.length === 0 ? (
          <div className="text-center py-16 text-navy/60">
            <Users className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p>Aucun inscrit pour le moment.</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border-2 border-cream bg-white/70">
            <table className="w-full text-left">
              <thead className="bg-cream/60 text-navy">
                <tr>
                  <th className="px-4 py-3 font-bold">Email</th>
                  <th className="px-4 py-3 font-bold">Nom</th>
                  <th className="px-4 py-3 font-bold">Plan</th>
                  <th className="px-4 py-3 font-bold">Inscrit le</th>
                  <th className="px-4 py-3 font-bold">Emails quotidiens</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr key={i} className="border-t border-cream/70 text-navy/90">
                    <td className="px-4 py-3 font-medium">{u.email}</td>
                    <td className="px-4 py-3">{u.name || "—"}</td>
                    <td className="px-4 py-3">
                      {u.plan === "premium" ? (
                        <span className="inline-flex items-center gap-1 text-bordeaux font-semibold"><Crown className="w-4 h-4" /> Premium</span>
                      ) : (
                        <span className="text-navy/60">Gratuit</span>
                      )}
                    </td>
                    <td className="px-4 py-3">{fmtDate(u.created_at)}</td>
                    <td className="px-4 py-3">{u.daily_email_optin ? "Oui" : "Non"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
