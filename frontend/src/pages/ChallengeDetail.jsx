import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { api, BACKEND_URL } from "@/lib/api";
import Navbar from "@/components/Navbar";
import { ArrowLeft, Copy, Check, MessageCircle, Mail, Share2, Trophy, Users, RefreshCw } from "lucide-react";

export default function ChallengeDetail() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [copied, setCopied] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const lastUpdate = useRef(0);

  const inviteUrl = `${window.location.origin}/defi/${token}`;

  const fetchData = async () => {
    try {
      const { data: d } = await api.get(`/challenges/${token}`);
      setData(d);
      lastUpdate.current = Date.now();
    } catch {}
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 5000); // live leaderboard
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const shareText = `Salut ! Je te défie au quiz "${data?.category_title || ""}" sur Quiz d'Antan. Joue ici : ${inviteUrl}`;
  const waUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
  const mailUrl = `mailto:?subject=${encodeURIComponent("Défi quiz famille !")}&body=${encodeURIComponent(shareText)}`;
  const smsUrl = `sms:?body=${encodeURIComponent(shareText)}`;

  if (!data)
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-3xl mx-auto p-12 text-navy/60 text-xl">Chargement...</div>
      </div>
    );

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <Link to="/app/challenges" className="inline-flex items-center gap-2 text-navy hover:text-terracotta font-bold mb-6">
          <ArrowLeft className="w-5 h-5" /> Mes défis
        </Link>

        {/* Header card */}
        <div className="bg-gradient-to-br from-navy to-navy-dark text-white rounded-[28px] p-8 border-4 border-mustard relative overflow-hidden mb-6">
          <div className="absolute -top-16 -right-16 w-72 h-72 rounded-full bg-mustard/20 blur-3xl pointer-events-none" />
          <div className="relative flex flex-col md:flex-row items-start md:items-center gap-5">
            {data.category_mascot_image && (
              <div className="w-24 h-24 rounded-2xl overflow-hidden bg-cream border-4 border-mustard shrink-0">
                <img src={`${BACKEND_URL}${data.category_mascot_image}`} alt="" className="w-full h-full object-cover" />
              </div>
            )}
            <div className="flex-1">
              <div className="text-mustard font-bold tracking-wide uppercase text-sm mb-1">Défi famille</div>
              <h1 className="font-display text-3xl md:text-4xl font-extrabold">{data.category_title}</h1>
              <p className="text-cream/80 mt-1">
                {data.total} questions · animé par {data.category_mascot_name}
              </p>
            </div>
          </div>
        </div>

        {/* Share section */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8 mb-6">
          <h2 className="font-display text-2xl font-bold text-navy mb-4 flex items-center gap-2">
            <Share2 className="w-6 h-6 text-terracotta" /> Inviter la famille
          </h2>

          <div className="bg-cream rounded-2xl p-4 flex items-center gap-3 mb-5">
            <input
              readOnly
              data-testid="challenge-invite-url"
              value={inviteUrl}
              className="flex-1 bg-transparent text-navy font-mono text-sm outline-none min-w-0"
              onClick={(e) => e.target.select()}
            />
            <button
              onClick={copy}
              data-testid="challenge-copy-btn"
              className="inline-flex items-center gap-2 bg-navy hover:bg-navy-dark text-white font-bold px-4 py-2 rounded-full text-sm shrink-0 transition"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied ? "Copié" : "Copier"}
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <a
              href={waUrl}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="challenge-share-whatsapp"
              className="flex flex-col items-center gap-2 p-4 rounded-2xl border-2 border-cream-dark hover:border-[#25D366] hover:bg-[#25D366]/5 transition"
            >
              <MessageCircle className="w-7 h-7 text-[#25D366]" />
              <span className="font-bold text-navy text-sm">WhatsApp</span>
            </a>
            <a
              href={smsUrl}
              data-testid="challenge-share-sms"
              className="flex flex-col items-center gap-2 p-4 rounded-2xl border-2 border-cream-dark hover:border-terracotta hover:bg-terracotta/5 transition"
            >
              <MessageCircle className="w-7 h-7 text-terracotta" />
              <span className="font-bold text-navy text-sm">SMS</span>
            </a>
            <a
              href={mailUrl}
              data-testid="challenge-share-email"
              className="flex flex-col items-center gap-2 p-4 rounded-2xl border-2 border-cream-dark hover:border-navy hover:bg-navy/5 transition"
            >
              <Mail className="w-7 h-7 text-navy" />
              <span className="font-bold text-navy text-sm">Email</span>
            </a>
          </div>
        </div>

        {/* Leaderboard */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8" data-testid="challenge-leaderboard">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-display text-2xl font-bold text-navy flex items-center gap-2">
              <Trophy className="w-6 h-6 text-mustard-dark" /> Classement
            </h2>
            <button
              onClick={() => { setRefreshing(true); fetchData().finally(() => setTimeout(() => setRefreshing(false), 500)); }}
              data-testid="challenge-refresh"
              className="inline-flex items-center gap-1 text-navy/70 hover:text-terracotta text-sm font-medium"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} /> Actualiser
            </button>
          </div>

          {data.participants.length === 0 ? (
            <div className="text-center py-10">
              <Users className="w-14 h-14 mx-auto text-navy/30 mb-3" />
              <p className="text-navy/60 text-lg">En attente du premier joueur...</p>
              <p className="text-navy/50 text-sm mt-1">Partagez le lien ci-dessus pour démarrer.</p>
            </div>
          ) : (
            <ol className="space-y-3">
              {data.participants.map((p, i) => {
                const pct = p.total ? Math.round((p.score / p.total) * 100) : 0;
                const medal = ["🥇", "🥈", "🥉"][i] || "";
                return (
                  <li
                    key={`${p.name}-${p.completed_at}`}
                    data-testid={`leaderboard-row-${i}`}
                    className={`flex items-center justify-between p-4 rounded-2xl border-2 ${
                      i === 0 ? "bg-mustard/20 border-mustard-dark" : "bg-cream/40 border-cream-dark"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-display text-2xl font-extrabold text-navy w-10 text-center">
                        {medal || `#${i + 1}`}
                      </span>
                      <div>
                        <div className="font-display text-lg font-bold text-navy">{p.name}</div>
                        <div className="text-sm text-navy/60">
                          {new Date(p.completed_at).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                          {p.duration_seconds ? ` · ${p.duration_seconds}s` : ""}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-display text-2xl font-extrabold text-bordeaux">{p.score}/{p.total}</div>
                      <div className="text-sm text-navy/60">{pct}%</div>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </main>
    </div>
  );
}
