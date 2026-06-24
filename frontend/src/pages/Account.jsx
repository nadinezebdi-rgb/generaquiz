import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  User, Mail, Crown, Calendar, Lock, Loader2, Check, LogOut, Trash2, Save, ArrowRight, Bell, Flame,
} from "lucide-react";

export default function Account() {
  const { user, refresh, logout } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState(user?.name || "");
  const [savingName, setSavingName] = useState(false);
  const [nameMsg, setNameMsg] = useState("");

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [newPw2, setNewPw2] = useState("");
  const [savingPw, setSavingPw] = useState(false);
  const [pwMsg, setPwMsg] = useState(null); // {type, text}

  const [emailOptin, setEmailOptin] = useState(user?.daily_email_optin !== false);
  const [savingPref, setSavingPref] = useState(false);
  const [prefMsg, setPrefMsg] = useState("");

  const [deleting, setDeleting] = useState(false);

  if (!user) return null;

  const saveName = async (e) => {
    e.preventDefault();
    setSavingName(true); setNameMsg("");
    try {
      await api.patch("/auth/profile", { name });
      await refresh();
      setNameMsg("Profil mis à jour");
      setTimeout(() => setNameMsg(""), 2500);
    } catch (e2) {
      setNameMsg(formatError(e2.response?.data?.detail) || "Erreur");
    } finally {
      setSavingName(false);
    }
  };

  const savePw = async (e) => {
    e.preventDefault();
    setPwMsg(null);
    if (newPw.length < 6) { setPwMsg({ type: "error", text: "6 caractères minimum." }); return; }
    if (newPw !== newPw2) { setPwMsg({ type: "error", text: "Les mots de passe ne correspondent pas." }); return; }
    setSavingPw(true);
    try {
      await api.post("/auth/change-password", { current_password: currentPw, new_password: newPw });
      setPwMsg({ type: "success", text: "Mot de passe modifié avec succès." });
      setCurrentPw(""); setNewPw(""); setNewPw2("");
    } catch (e2) {
      setPwMsg({ type: "error", text: formatError(e2.response?.data?.detail) || "Erreur" });
    } finally {
      setSavingPw(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const togglePref = async (next) => {
    setSavingPref(true); setPrefMsg("");
    try {
      await api.patch("/auth/preferences/daily-email", { daily_email_optin: next });
      setEmailOptin(next);
      if (refresh) refresh();
      setPrefMsg(next ? "Vous recevrez l'email matinal" : "Notifications email désactivées");
      setTimeout(() => setPrefMsg(""), 2500);
    } catch (e2) {
      setPrefMsg(formatError(e2.response?.data?.detail) || "Erreur");
    } finally {
      setSavingPref(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Supprimer définitivement votre compte ? Cette action est irréversible.")) return;
    setDeleting(true);
    try {
      await api.delete("/auth/account");
      await logout();
      navigate("/");
    } catch (e2) {
      alert(formatError(e2.response?.data?.detail) || "Erreur");
      setDeleting(false);
    }
  };

  const isPremium = user.plan === "premium";
  const expiresDate = user.plan_expires_at ? new Date(user.plan_expires_at) : null;
  const isLifetime = expiresDate && expiresDate.getFullYear() > 2090;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2">Mon compte</h1>
          <p className="text-lg text-navy/70">Gérez vos informations et votre abonnement.</p>
        </div>

        {/* ============ PROFIL CARD ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8 mb-6">
          <h2 className="font-display text-2xl font-bold text-navy mb-5 flex items-center gap-2">
            <User className="w-6 h-6 text-terracotta" /> Mes informations
          </h2>

          <form onSubmit={saveName} className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-navy mb-2">Prénom</label>
              <input
                data-testid="account-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={80}
                className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-navy mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/40" />
                <input
                  type="email"
                  value={user.email}
                  disabled
                  className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-cream-dark bg-cream/50 text-navy/70 min-h-[56px]"
                  data-testid="account-email"
                />
              </div>
              <p className="text-xs text-navy/50 mt-1">L&apos;email ne peut pas être modifié.</p>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="submit"
                data-testid="account-save-name"
                disabled={savingName || name === user.name || !name.trim()}
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full shadow-warm disabled:opacity-50"
              >
                {savingName ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Enregistrer
              </button>
              {nameMsg && <span className="text-[#3D9970] font-medium text-sm" data-testid="account-name-msg">{nameMsg}</span>}
            </div>
          </form>
        </div>

        {/* ============ ABONNEMENT CARD ============ */}
        <div className={`rounded-[28px] p-6 md:p-8 mb-6 border-2 ${isPremium ? "bg-navy text-white border-mustard" : "bg-white border-cream-dark"}`}>
          <h2 className={`font-display text-2xl font-bold mb-5 flex items-center gap-2 ${isPremium ? "text-mustard" : "text-navy"}`}>
            <Crown className="w-6 h-6" /> Mon abonnement
          </h2>
          {isPremium ? (
            <div>
              <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-4 py-2 rounded-full mb-4">
                <Crown className="w-5 h-5" /> Premium actif
              </div>
              <div className="flex items-center gap-2 text-cream/90" data-testid="account-plan-expires">
                <Calendar className="w-5 h-5" />
                {isLifetime ? (
                  <span>Accès <strong className="text-mustard">à vie</strong></span>
                ) : expiresDate ? (
                  <span>Expire le {expiresDate.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}</span>
                ) : (
                  <span>Premium actif</span>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <p className="text-navy/80 text-lg" data-testid="account-plan-free">
                Vous utilisez la formule <strong>Découverte</strong> (gratuite, 5 questions par quiz).
              </p>
              <Link
                to="/app/pricing"
                data-testid="account-upgrade"
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full shadow-warm"
              >
                <Crown className="w-4 h-4" /> Passer Premium <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>

        {/* ============ STREAK & NOTIFICATIONS CARD ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8 mb-6" data-testid="account-streak-card">
          <h2 className="font-display text-2xl font-bold text-navy mb-5 flex items-center gap-2">
            <Flame className="w-6 h-6 text-terracotta" fill="currentColor" /> Ma série & notifications
          </h2>

          <div className="grid sm:grid-cols-2 gap-4 mb-6">
            <div className="bg-gradient-to-br from-terracotta/10 to-mustard/20 border-2 border-terracotta/30 rounded-2xl p-5">
              <div className="text-sm font-bold uppercase tracking-wider text-navy/60 mb-1">Série en cours</div>
              <div className="font-display text-4xl font-extrabold text-bordeaux flex items-center gap-2">
                {user.streak_current || 0}
                <span className="text-base text-navy/60 font-normal">jour{(user.streak_current || 0) > 1 ? "s" : ""}</span>
                {(user.streak_current || 0) >= 2 && <Flame className="w-7 h-7 text-terracotta" fill="currentColor" />}
              </div>
              {user.streak_last_date && (
                <div className="text-xs text-navy/60 mt-1">Dernier quiz le {new Date(user.streak_last_date + "T00:00:00").toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}</div>
              )}
            </div>
            <div className="bg-cream border-2 border-cream-dark rounded-2xl p-5">
              <div className="text-sm font-bold uppercase tracking-wider text-navy/60 mb-1">Meilleure série</div>
              <div className="font-display text-4xl font-extrabold text-navy flex items-center gap-2">
                {user.streak_best || 0}
                <span className="text-base text-navy/60 font-normal">jour{(user.streak_best || 0) > 1 ? "s" : ""}</span>
                {(user.streak_best || 0) >= 7 && <span title="Plus de 7 jours !" className="text-2xl">🏆</span>}
              </div>
              <div className="text-xs text-navy/60 mt-1">Votre record personnel</div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t-2 border-cream-dark pt-5">
            <div className="flex items-start gap-3 flex-1">
              <Bell className="w-6 h-6 text-navy mt-0.5 shrink-0" />
              <div>
                <div className="font-bold text-navy">Rappel matinal du Quiz du Jour</div>
                <p className="text-sm text-navy/60">
                  Recevez un email à 9h chaque matin avec votre lien direct vers le Quiz du Jour.
                </p>
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={emailOptin}
              disabled={savingPref}
              onClick={() => togglePref(!emailOptin)}
              data-testid="account-email-optin-toggle"
              className={`relative inline-flex h-8 w-14 shrink-0 items-center rounded-full transition-colors ${
                emailOptin ? "bg-terracotta" : "bg-cream-dark"
              } ${savingPref ? "opacity-60" : ""}`}
            >
              <span className={`inline-block h-6 w-6 transform rounded-full bg-white shadow transition-transform ${emailOptin ? "translate-x-7" : "translate-x-1"}`} />
            </button>
          </div>
          {prefMsg && <p className="text-sm text-[#3D9970] font-medium mt-3" data-testid="account-pref-msg">{prefMsg}</p>}
        </div>

        {/* ============ MOT DE PASSE CARD ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8 mb-6">
          <h2 className="font-display text-2xl font-bold text-navy mb-5 flex items-center gap-2">
            <Lock className="w-6 h-6 text-terracotta" /> Changer mon mot de passe
          </h2>
          <form onSubmit={savePw} className="space-y-4 max-w-lg">
            <input
              data-testid="account-current-pw"
              type="password"
              placeholder="Mot de passe actuel"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              required
              className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
            />
            <input
              data-testid="account-new-pw"
              type="password"
              placeholder="Nouveau mot de passe (6 car. min)"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              required
              minLength={6}
              className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
            />
            <input
              data-testid="account-new-pw2"
              type="password"
              placeholder="Confirmer le nouveau mot de passe"
              value={newPw2}
              onChange={(e) => setNewPw2(e.target.value)}
              required
              minLength={6}
              className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
            />
            {pwMsg && (
              <div
                data-testid={`account-pw-${pwMsg.type}`}
                className={`rounded-xl p-4 text-navy font-medium border-2 ${
                  pwMsg.type === "success"
                    ? "bg-[#3D9970]/10 border-[#3D9970]/40"
                    : "bg-[#D9534F]/10 border-[#D9534F]/40"
                }`}
              >
                {pwMsg.type === "success" ? "✅ " : "❌ "}{pwMsg.text}
              </div>
            )}
            <button
              data-testid="account-save-pw"
              type="submit"
              disabled={savingPw}
              className="inline-flex items-center gap-2 bg-navy hover:bg-navy-dark text-white font-bold px-5 py-3 rounded-full disabled:opacity-60"
            >
              {savingPw ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Mettre à jour
            </button>
          </form>
        </div>

        {/* ============ DANGER ZONE ============ */}
        <div className="bg-white border-2 border-[#D9534F]/40 rounded-[28px] p-6 md:p-8 mb-6">
          <h2 className="font-display text-2xl font-bold text-bordeaux mb-5">Actions</h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleLogout}
              data-testid="account-logout"
              className="inline-flex items-center justify-center gap-2 bg-cream hover:bg-mustard text-navy font-bold px-5 py-3 rounded-full border-2 border-navy transition"
            >
              <LogOut className="w-4 h-4" /> Se déconnecter
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              data-testid="account-delete"
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-[#D9534F] text-bordeaux hover:text-white font-bold px-5 py-3 rounded-full border-2 border-[#D9534F] transition disabled:opacity-60"
            >
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Supprimer mon compte
            </button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
