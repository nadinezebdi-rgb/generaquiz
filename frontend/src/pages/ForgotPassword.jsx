import { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatError } from "@/lib/api";
import { Sparkles, Mail, Loader2, ArrowLeft, Check, Inbox } from "lucide-react";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
    } catch (e2) {
      setErr(formatError(e2.response?.data?.detail) || e2.message);
    } finally {
      setLoading(false);
    }
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
            <span className="font-display text-2xl font-bold text-navy">GénéraQuiz</span>
          </div>

          {!sent ? (
            <>
              <h1 className="font-display text-3xl font-extrabold text-navy text-center mb-2">Mot de passe oublié ?</h1>
              <p className="text-navy/70 text-center mb-7">
                Saisissez votre email pour recevoir un lien de réinitialisation.
              </p>
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
            </>
          ) : (
            <div className="text-center" data-testid="forgot-sent">
              <div className="w-16 h-16 mx-auto rounded-full bg-[#3D9970]/15 flex items-center justify-center mb-4">
                <Inbox className="w-8 h-8 text-[#3D9970]" strokeWidth={2.5} />
              </div>
              <h1 className="font-display text-2xl font-extrabold text-navy mb-3">Vérifiez votre boîte mail</h1>
              <p className="text-navy/80 text-lg mb-2">
                Si un compte est associé à <strong>{email}</strong>, vous allez recevoir un email avec un lien pour réinitialiser votre mot de passe.
              </p>
              <p className="text-navy/60 text-sm mb-6">
                Le lien est valable 1 heure. Pensez à vérifier vos spams.
              </p>
              <div className="space-y-3">
                <button
                  onClick={() => { setSent(false); setEmail(""); }}
                  data-testid="forgot-retry"
                  className="block w-full text-center bg-cream hover:bg-mustard text-navy font-bold py-3 rounded-full border-2 border-navy transition"
                >
                  Renvoyer avec un autre email
                </button>
                <Link to="/login" className="block text-center text-navy/70 hover:text-terracotta font-medium">
                  Retour à la connexion
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
