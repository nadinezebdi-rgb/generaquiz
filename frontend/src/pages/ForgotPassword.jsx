import { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatError } from "@/lib/api";
import { Sparkles, Mail, Loader2, ArrowLeft, Copy, Check, Info } from "lucide-react";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // {ok, message, reset_link?}
  const [copied, setCopied] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setResult(data);
    } catch (e2) {
      setErr(formatError(e2.response?.data?.detail) || e2.message);
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result?.reset_link || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/login" className="inline-flex items-center gap-2 text-navy hover:text-terracotta font-bold mb-6" data-testid="forgot-back">
          <ArrowLeft className="w-5 h-5" /> Retour à la connexion
        </Link>

        <div className="bg-white border-2 border-cream-dark rounded-3xl p-8 shadow-soft">
          <div className="flex items-center justify-center gap-3 mb-5">
            <span className="w-12 h-12 rounded-full bg-terracotta flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" strokeWidth={2.5} />
            </span>
            <span className="font-display text-2xl font-bold text-navy">Quiz d'Antan</span>
          </div>
          <h1 className="font-display text-3xl font-extrabold text-navy text-center mb-2">Mot de passe oublié ?</h1>
          <p className="text-navy/70 text-center mb-7">
            Saisissez votre email pour recevoir un lien de réinitialisation.
          </p>

          {!result ? (
            <form onSubmit={submit} className="space-y-5">
              <div>
                <label className="block text-sm font-bold text-navy mb-2">Email</label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/40" />
                  <input
                    data-testid="forgot-email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="vous@exemple.fr"
                    className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                  />
                </div>
              </div>

              {err && (
                <div data-testid="forgot-error" className="bg-[#D9534F]/10 border-2 border-[#D9534F]/40 rounded-xl p-4 text-navy font-medium">
                  {err}
                </div>
              )}

              <button
                data-testid="forgot-submit"
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-6 py-4 rounded-full shadow-warm min-h-[60px] disabled:opacity-60 transition"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Mail className="w-5 h-5" />}
                {loading ? "Envoi..." : "Envoyer le lien"}
              </button>
            </form>
          ) : (
            <div className="space-y-4" data-testid="forgot-result">
              <div className="bg-[#3D9970]/10 border-2 border-[#3D9970]/40 rounded-2xl p-5">
                <p className="text-navy font-medium">✅ {result.message}</p>
              </div>

              {result.reset_link && (
                <div className="bg-mustard/20 border-2 border-mustard-dark rounded-2xl p-5">
                  <div className="flex items-start gap-2 mb-3">
                    <Info className="w-5 h-5 text-bordeaux mt-0.5 shrink-0" />
                    <p className="text-navy text-sm">
                      <strong>Démo : envoi d'email simulé.</strong> En production, ce lien sera envoyé par email automatiquement.
                      Cliquez ou copiez-le pour réinitialiser votre mot de passe maintenant.
                    </p>
                  </div>
                  <div className="bg-white rounded-xl p-3 flex items-center gap-2 mb-3">
                    <code className="flex-1 text-xs text-navy/70 font-mono break-all" data-testid="forgot-reset-link">{result.reset_link}</code>
                    <button
                      onClick={copy}
                      data-testid="forgot-copy"
                      className="inline-flex items-center gap-1 bg-navy text-white text-sm font-bold px-3 py-1.5 rounded-lg shrink-0"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      {copied ? "Copié" : "Copier"}
                    </button>
                  </div>
                  <a
                    href={`/reset-password?token=${result.reset_token}`}
                    data-testid="forgot-use-link"
                    className="block w-full text-center bg-terracotta hover:bg-terracotta-dark text-white font-bold py-3 rounded-full shadow-warm"
                  >
                    Réinitialiser mon mot de passe →
                  </a>
                </div>
              )}

              <Link to="/login" className="block text-center text-navy/70 hover:text-terracotta font-medium">
                Retour à la connexion
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
