import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { api, formatError } from "@/lib/api";
import { Sparkles, UserPlus, Mail, Lock, User, Gift, Check, X } from "lucide-react";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [referralCode, setReferralCode] = useState(searchParams.get("code") || "");
  const [birthYear, setBirthYear] = useState("");
  const [codeStatus, setCodeStatus] = useState(null); // null | 'checking' | {valid, sponsor_name, bonus} | {valid:false}
  const [showReferral, setShowReferral] = useState(!!searchParams.get("code"));
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const debounceRef = useRef(null);

  // Live-validate the referral code after the user stops typing for 400ms
  useEffect(() => {
    if (!referralCode || referralCode.trim().length < 4) {
      setCodeStatus(null);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setCodeStatus("checking");
    debounceRef.current = setTimeout(() => {
      api
        .post("/referral/validate-code", { code: referralCode.trim().toUpperCase() })
        .then((r) => setCodeStatus(r.data))
        .catch(() => setCodeStatus({ valid: false }));
    }, 400);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [referralCode]);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const finalCode = codeStatus && codeStatus.valid ? referralCode.trim().toUpperCase() : null;
      const by = birthYear ? parseInt(birthYear, 10) : null;
      await register(name, email, password, finalCode, by);
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

          {codeStatus && codeStatus.valid && (
            <div
              data-testid="register-referral-banner"
              className="bg-mustard/30 border-2 border-mustard-dark rounded-2xl p-3 mb-5 flex items-center gap-3"
            >
              <div className="w-9 h-9 shrink-0 rounded-full bg-terracotta flex items-center justify-center">
                <Gift className="w-5 h-5 text-white" />
              </div>
              <div className="text-sm">
                <div className="font-bold text-navy">
                  Invité·e par <span className="text-bordeaux">{codeStatus.sponsor_name}</span> 🎁
                </div>
                <div className="text-navy/70">
                  +{codeStatus.bonus} crédits offerts dès votre 1ᵉʳ quiz (et autant pour votre parrain).
                </div>
              </div>
            </div>
          )}

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

            <div>
              <label className="block text-sm font-bold text-navy mb-2">Année de naissance <span className="text-navy/50 font-normal">(facultatif)</span></label>
              <input
                data-testid="register-birth-year"
                type="number"
                value={birthYear}
                onChange={(e) => setBirthYear(e.target.value)}
                placeholder="1955"
                min={1900}
                max={2025}
                className="w-full px-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
              />
              <p className="text-xs text-navy/60 mt-1.5">Sert à proposer des duos « Jeune + Senior » dans le mode coopératif.</p>
            </div>

            {/* ============ Referral code ============ */}
            {showReferral ? (
              <div>
                <label className="block text-sm font-bold text-navy mb-2 flex items-center gap-2">
                  <Gift className="w-4 h-4 text-terracotta" /> Code de parrainage (facultatif)
                </label>
                <div className="relative">
                  <input
                    data-testid="register-referral-code"
                    type="text"
                    value={referralCode}
                    onChange={(e) => setReferralCode(e.target.value.toUpperCase())}
                    placeholder="MARIE-X7K2"
                    maxLength={40}
                    className={`w-full pl-4 pr-12 py-4 text-lg rounded-2xl border-2 bg-white min-h-[56px] uppercase tracking-wider ${
                      codeStatus && codeStatus.valid
                        ? "border-[#3D9970]"
                        : codeStatus && codeStatus.valid === false
                        ? "border-[#D9534F]"
                        : "border-cream-dark focus:border-navy"
                    }`}
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2">
                    {codeStatus === "checking" && <span className="text-navy/40 text-sm">…</span>}
                    {codeStatus && codeStatus.valid && (
                      <Check className="w-5 h-5 text-[#3D9970]" data-testid="register-referral-ok" strokeWidth={3} />
                    )}
                    {codeStatus && codeStatus.valid === false && (
                      <X className="w-5 h-5 text-[#D9534F]" data-testid="register-referral-ko" strokeWidth={3} />
                    )}
                  </div>
                </div>
                {codeStatus && codeStatus.valid === false && (
                  <p className="text-xs text-bordeaux mt-1.5">Code inconnu — vérifiez l&apos;orthographe ou laissez vide.</p>
                )}
              </div>
            ) : (
              <button
                type="button"
                data-testid="register-show-referral"
                onClick={() => setShowReferral(true)}
                className="text-sm text-navy/60 hover:text-terracotta font-medium inline-flex items-center gap-1"
              >
                <Gift className="w-4 h-4" /> J&apos;ai un code de parrainage
              </button>
            )}

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
