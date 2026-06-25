import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Coins, Tv, Play, Check, ArrowRight, Crown, AlertTriangle, Loader2 } from "lucide-react";

const ADSENSE_CLIENT = process.env.REACT_APP_ADSENSE_CLIENT || "";
const ADSENSE_SLOT = process.env.REACT_APP_ADSENSE_SLOT || "";
const WATCH_SECONDS = 15;

/**
 * EarnCredits — "Regardez une pub, recevez 1 crédit".
 * Limit: AD_REWARD_DAILY_CAP (5) ads per day, enforced server-side.
 *
 * AdSense behaviour:
 *   - If REACT_APP_ADSENSE_CLIENT + SLOT are configured, we render an
 *     <ins class="adsbygoogle"> unit and trigger adsbygoogle.push().
 *   - Otherwise we render a house ad (promo for Premium) so the flow is
 *     still testable end-to-end without AdSense approval.
 *
 * Credit is granted only when the user has spent WATCH_SECONDS on the page
 * with the ad rendered. Server-side anti-abuse caps at 5 / day per user.
 */
export default function EarnCredits() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [secondsLeft, setSecondsLeft] = useState(WATCH_SECONDS);
  const [watching, setWatching] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const [msg, setMsg] = useState(null); // {type: success|error, text}
  const [remainingToday, setRemainingToday] = useState(null);
  const timerRef = useRef(null);
  const insRef = useRef(null);

  // Load AdSense script (once)
  useEffect(() => {
    if (!ADSENSE_CLIENT) return;
    if (document.querySelector("script[data-adsense-loaded]")) return;
    const s = document.createElement("script");
    s.async = true;
    s.crossOrigin = "anonymous";
    s.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`;
    s.setAttribute("data-adsense-loaded", "true");
    document.head.appendChild(s);
  }, []);

  const startWatching = () => {
    if (watching) return;
    setMsg(null);
    setWatching(true);
    setSecondsLeft(WATCH_SECONDS);

    // Trigger AdSense ad fill
    if (ADSENSE_CLIENT && ADSENSE_SLOT) {
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      } catch (_) {
        // ignore — ad block / network error → we still let timer run
      }
    }

    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current);
          claimReward();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  };

  const claimReward = async () => {
    setClaiming(true);
    try {
      const { data } = await api.post("/gamification/credits/earn-ad", {});
      setRemainingToday(data.remaining_today);
      setMsg({ type: "success", text: `+${data.earned} crédit ajouté ! Solde : ${data.credits}.` });
      await refresh();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setMsg({ type: "error", text: formatError(detail) || "Erreur. Réessayez plus tard." });
    } finally {
      setClaiming(false);
      setWatching(false);
    }
  };

  useEffect(() => () => timerRef.current && clearInterval(timerRef.current), []);

  if (!user) return null;
  const credits = user.credits || 0;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2">Gagner des crédits</h1>
            <p className="text-lg text-navy/70">Regardez une courte publicité, recevez 1 crédit.</p>
          </div>
          <div className="bg-mustard border-2 border-mustard-dark rounded-2xl px-5 py-3 flex items-center gap-2" data-testid="earn-credits-balance">
            <Coins className="w-6 h-6 text-bordeaux" strokeWidth={2.5} />
            <span className="font-display text-3xl font-extrabold text-navy">{credits}</span>
            <span className="text-navy/70 font-bold">crédits</span>
          </div>
        </div>

        {/* AdSense / house-ad slot */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8 mb-6">
          <div className="bg-cream border-2 border-cream-dark rounded-2xl p-4 min-h-[260px] flex items-center justify-center relative overflow-hidden">
            {ADSENSE_CLIENT && ADSENSE_SLOT ? (
              <ins
                ref={insRef}
                className="adsbygoogle"
                style={{ display: "block", width: "100%", height: "260px" }}
                data-ad-client={ADSENSE_CLIENT}
                data-ad-slot={ADSENSE_SLOT}
                data-ad-format="auto"
                data-full-width-responsive="true"
                data-testid="earn-credits-adsense-slot"
              />
            ) : (
              <HouseAd />
            )}
            {!watching && (
              <div className="absolute inset-0 bg-navy/85 backdrop-blur-sm flex items-center justify-center" data-testid="earn-credits-overlay">
                <button
                  onClick={startWatching}
                  data-testid="earn-credits-start"
                  className="inline-flex items-center gap-3 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full shadow-warm transition"
                >
                  <Play className="w-5 h-5" fill="currentColor" />
                  Regarder la pub ({WATCH_SECONDS} s)
                </button>
              </div>
            )}
          </div>

          {watching && (
            <div className="mt-5" data-testid="earn-credits-progress">
              <div className="flex items-center justify-between text-sm font-bold text-navy mb-2">
                <span className="inline-flex items-center gap-2"><Tv className="w-4 h-4" /> Lecture en cours…</span>
                <span>{secondsLeft} s restantes</span>
              </div>
              <div className="h-2 bg-cream rounded-full overflow-hidden">
                <div
                  className="h-full bg-terracotta transition-all"
                  style={{ width: `${((WATCH_SECONDS - secondsLeft) / WATCH_SECONDS) * 100}%` }}
                />
              </div>
            </div>
          )}

          {claiming && (
            <div className="mt-4 text-sm text-navy/70 inline-flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Crédit en cours d&apos;ajout…
            </div>
          )}

          {msg && (
            <div
              data-testid={`earn-credits-msg-${msg.type}`}
              className={`mt-5 rounded-2xl p-4 border-2 font-medium ${
                msg.type === "success"
                  ? "bg-[#3D9970]/10 border-[#3D9970]/40 text-navy"
                  : "bg-[#D9534F]/10 border-[#D9534F]/40 text-bordeaux"
              }`}
            >
              {msg.type === "success" ? (
                <span className="inline-flex items-center gap-2"><Check className="w-4 h-4" strokeWidth={3} /> {msg.text}</span>
              ) : (
                <span className="inline-flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {msg.text}</span>
              )}
            </div>
          )}

          {remainingToday != null && (
            <p className="mt-3 text-sm text-navy/60" data-testid="earn-credits-remaining">
              Il vous reste <strong>{remainingToday}</strong> visionnages aujourd&apos;hui (max 5/jour).
            </p>
          )}
        </div>

        {/* Educational footer */}
        <div className="bg-cream border-2 border-cream-dark rounded-2xl p-5 text-navy/80 text-sm">
          <p className="mb-2">💡 <strong>Comment ça marche ?</strong></p>
          <ul className="space-y-1 list-disc list-inside">
            <li>1 crédit toutes les <strong>15 secondes</strong> de visionnage.</li>
            <li>Plafond : <strong>5 crédits par jour</strong> via la publicité.</li>
            <li>Les crédits servent à débloquer des indices, sauver une série ou des questions bonus.</li>
            <li>Pas envie de pubs ?{" "}
              <Link to="/app/pricing" className="text-terracotta font-bold hover:underline inline-flex items-center gap-1">
                <Crown className="w-3.5 h-3.5" /> Passer Premium <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </li>
          </ul>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function HouseAd() {
  return (
    <div className="text-center px-6">
      <div className="inline-block bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs mb-3 uppercase tracking-wider">
        Pub maison
      </div>
      <h3 className="font-display text-2xl font-extrabold text-navy mb-2">
        Tirez le meilleur de <span className="text-terracotta">GénéraQuiz</span>
      </h3>
      <p className="text-navy/70 mb-4 max-w-md mx-auto">
        Passez Premium pour des quiz illimités, accès aux 8 catégories et défis famille sans pub.
      </p>
      <Link
        to="/app/pricing"
        className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full shadow-warm"
      >
        <Crown className="w-4 h-4" /> Découvrir Premium
      </Link>
    </div>
  );
}
