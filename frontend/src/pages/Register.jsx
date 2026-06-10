import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { formatError } from "@/lib/api";
import { Sparkles, UserPlus, Mail, Lock, User } from "lucide-react";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await register(name, email, password);
      navigate("/app/dashboard");
    } catch (e2) {
      setErr(formatError(e2.response?.data?.detail) || e2.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center justify-center gap-2 mb-8" data-testid="auth-back-home">
          <span className="w-12 h-12 rounded-full bg-terracotta flex items-center justify-center shadow-warm">
            <Sparkles className="w-6 h-6 text-white" strokeWidth={2.5} />
          </span>
          <span className="font-display text-3xl font-bold text-navy">GénéraQuiz</span>
        </Link>

        <div className="bg-white border-2 border-cream-dark rounded-3xl p-8 shadow-soft">
          <h1 className="font-display text-3xl font-extrabold text-navy mb-2 text-center">Inscription gratuite</h1>
          <p className="text-navy/70 text-center mb-7">Créez votre compte en 30 secondes</p>

          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="block text-sm font-bold text-navy mb-2">Votre prénom</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/40" />
                <input
                  data-testid="register-name"
                  type="text"
                  required
                  minLength={1}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Marie"
                  className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-navy mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/40" />
                <input
                  data-testid="register-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="vous@exemple.fr"
                  className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-navy mb-2">Mot de passe</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/40" />
                <input
                  data-testid="register-password"
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="6 caractères minimum"
                  className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                />
              </div>
            </div>

            {err && (
              <div data-testid="register-error" className="bg-[#D9534F]/10 border-2 border-[#D9534F]/40 rounded-xl p-4 text-navy font-medium">
                {err}
              </div>
            )}

            <button
              data-testid="register-submit"
              type="submit"
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-6 py-4 rounded-full shadow-warm min-h-[60px] disabled:opacity-60 transition"
            >
              <UserPlus className="w-5 h-5" />
              {loading ? "Inscription..." : "Créer mon compte"}
            </button>
          </form>

          <p className="text-center text-navy/70 mt-6">
            Déjà inscrit ?{" "}
            <Link to="/login" data-testid="register-to-login" className="text-terracotta font-bold hover:underline">
              Se connecter
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
