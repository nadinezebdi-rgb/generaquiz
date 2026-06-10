import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { api, formatError } from "@/lib/api";
import { Sparkles, Lock, Loader2, ArrowLeft, Check } from "lucide-react";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (pw1.length < 6) { setErr("Le mot de passe doit contenir au moins 6 caractères."); return; }
    if (pw1 !== pw2) { setErr("Les deux mots de passe ne correspondent pas."); return; }
    if (!token) { setErr("Lien invalide : token manquant."); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw1 });
      setDone(true);
      setTimeout(() => navigate("/login"), 2500);
    } catch (e2) {
      setErr(formatError(e2.response?.data?.detail) || e2.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/login" className="inline-flex items-center gap-2 text-navy hover:text-terracotta font-bold mb-6" data-testid="reset-back">
          <ArrowLeft className="w-5 h-5" /> Retour à la connexion
        </Link>

        <div className="bg-white border-2 border-cream-dark rounded-3xl p-8 shadow-soft">
          <div className="flex items-center justify-center gap-3 mb-5">
            <span className="w-12 h-12 rounded-full bg-terracotta flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" strokeWidth={2.5} />
            </span>
            <span className="font-display text-2xl font-bold text-navy">GénéraQuiz</span>
          </div>
          <h1 className="font-display text-3xl font-extrabold text-navy text-center mb-2">Nouveau mot de passe</h1>
          <p className="text-navy/70 text-center mb-7">Choisissez un mot de passe d'au moins 6 caractères.</p>

          {done ? (
            <div className="bg-[#3D9970]/10 border-2 border-[#3D9970]/40 rounded-2xl p-6 text-center" data-testid="reset-success">
              <Check className="w-12 h-12 text-[#3D9970] mx-auto mb-3" strokeWidth={3} />
              <h2 className="font-display text-2xl font-bold text-navy mb-2">Mot de passe mis à jour !</h2>
              <p className="text-navy/80">Redirection vers la connexion...</p>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-5">
              <div>
                <label className="block text-sm font-bold text-navy mb-2">Nouveau mot de passe</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/40" />
                  <input
                    data-testid="reset-pw1"
                    type="password"
                    required
                    minLength={6}
                    value={pw1}
                    onChange={(e) => setPw1(e.target.value)}
                    placeholder="6 caractères minimum"
                    className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-navy mb-2">Confirmer le mot de passe</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/40" />
                  <input
                    data-testid="reset-pw2"
                    type="password"
                    required
                    minLength={6}
                    value={pw2}
                    onChange={(e) => setPw2(e.target.value)}
                    placeholder="Retapez votre mot de passe"
                    className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                  />
                </div>
              </div>

              {err && (
                <div data-testid="reset-error" className="bg-[#D9534F]/10 border-2 border-[#D9534F]/40 rounded-xl p-4 text-navy font-medium">
                  {err}
                </div>
              )}

              <button
                data-testid="reset-submit"
                type="submit"
                disabled={loading || !token}
                className="w-full inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-6 py-4 rounded-full shadow-warm min-h-[60px] disabled:opacity-60 transition"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Lock className="w-5 h-5" />}
                {loading ? "Mise à jour..." : "Réinitialiser le mot de passe"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
