import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Lightbulb, Play } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ShareTipButton } from "@/components/ShareTipButton";
import { TipQuiz } from "@/components/TipQuiz";
import { fmtTipDate } from "@/components/DailyTipCard";
import { api } from "@/lib/api";
import { mascotSrc } from "@/lib/mascot";

const PLAY_TO = "/register?next=/app/quiz/bien-vieillir";

function useSeo(title, description) {
  useEffect(() => {
    const prev = document.title;
    const meta = document.querySelector('meta[name="description"]');
    const prevDesc = meta?.getAttribute("content");
    document.title = title;
    meta?.setAttribute("content", description);
    return () => {
      document.title = prev;
      if (meta && prevDesc) meta.setAttribute("content", prevDesc);
    };
  }, [title, description]);
}

const TipArticle = ({ tip, featured }) => (
  <motion.article
    initial={{ opacity: 0, y: 12 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ duration: 0.4 }}
    data-testid={`tip-article-${tip.date_key}`}
    className={`rounded-[24px] border-2 p-6 ${featured ? "bg-[#6A994E]/10 border-[#6A994E]/50" : "bg-white border-cream-dark"}`}
  >
    <div className="text-xs text-navy/60 mb-1">
      <time dateTime={tip.date_key}>{fmtTipDate(tip.date_key)}</time> · {tip.theme}
    </div>
    <h2 className={`font-display font-extrabold text-navy mb-2 ${featured ? "text-2xl md:text-3xl" : "text-xl"}`}>
      {featured ? tip.title : <Link to={`/conseils-bien-vieillir/${tip.date_key}`} className="hover:text-[#6A994E] transition-colors">{tip.title}</Link>}
    </h2>
    <p className="text-navy/80 leading-relaxed mb-2">{tip.text}</p>
    <p className="text-sm text-navy mb-4"><b>Le geste du jour :</b> <i>{tip.action}</i></p>
    <ShareTipButton tip={tip} testId={`tip-share-${tip.date_key}`} />
    <TipQuiz tip={tip} />
  </motion.article>
);

const THEME_FILTERS = [
  { key: "alimentation", label: "Alimentation" },
  { key: "activité physique", label: "Activité physique" },
  { key: "sommeil", label: "Sommeil" },
  { key: "mémoire", label: "Mémoire" },
  { key: "lien social", label: "Lien social" },
  { key: "prévention", label: "Prévention" },
  { key: "moral & bien-être", label: "Moral & bien-être" },
];
const slug = (k) => k.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z]+/g, "-");

const ThemeFilters = ({ tips, value, onChange }) => {
  const count = (k) => tips.filter((t) => t.theme === k).length;
  const chip = (active) =>
    `px-4 py-2 rounded-full text-sm font-bold border-2 transition-colors ${active ? "bg-[#6A994E] border-[#6A994E] text-white" : "bg-white border-cream-dark text-navy hover:border-[#6A994E]"}`;
  return (
    <div className="flex flex-wrap gap-2 mb-6" data-testid="conseils-filters" role="group" aria-label="Filtrer par thème">
      <button type="button" onClick={() => onChange(null)} className={chip(!value)} data-testid="conseils-filter-tous" aria-pressed={!value}>
        Tous <span className="opacity-70">({tips.length})</span>
      </button>
      {THEME_FILTERS.map(({ key, label }) => (
        <button key={key} type="button" onClick={() => onChange(key)} className={chip(value === key)} data-testid={`conseils-filter-${slug(key)}`} aria-pressed={value === key}>
          {label} <span className="opacity-70">({count(key)})</span>
        </button>
      ))}
    </div>
  );
};

export default function ConseilsArchive() {
  const { dateKey } = useParams();
  const [tips, setTips] = useState(null);
  const [featured, setFeatured] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [theme, setTheme] = useState(null);

  useEffect(() => {
    let ignore = false;
    api.get("/tips/recent?limit=366").then((r) => { if (!ignore) setTips(r.data); }).catch(() => setTips([]));
    if (dateKey) {
      api.get(`/tips/${dateKey}`)
        .then((r) => { if (!ignore) { setFeatured(r.data); setNotFound(false); } })
        .catch(() => { if (!ignore) setNotFound(true); });
    } else {
      setFeatured(null);
    }
    return () => { ignore = true; };
  }, [dateKey]);

  useSeo(
    featured ? `${featured.title} — le conseil de Lucette | GénéraQuiz` : "Conseils pour bien vieillir : un conseil santé chaque jour | GénéraQuiz",
    featured ? featured.text : "Chaque jour, Lucette partage un conseil simple et vérifié pour bien vieillir : alimentation, sommeil, mémoire, activité physique, lien social.",
  );

  const others = (tips || []).filter((t) => t.date_key !== featured?.date_key);
  const list = others.filter((t) => !theme || t.theme === theme);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="landing" />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10" data-testid="conseils-archive">
        <div className="flex items-center gap-5 mb-8">
          <img src={mascotSrc("/api/static/mascots/bien-vieillir.png", "sm")} alt="Lucette la Pétillante" className="w-20 h-20 rounded-2xl border-2 border-white shadow-soft object-cover bg-cream" />
          <div>
            <span className="inline-flex items-center gap-1 bg-[#6A994E] text-white text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full mb-2">
              <Lightbulb className="w-3 h-3" /> Bien vieillir
            </span>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-navy leading-tight">Les conseils de Lucette</h1>
          </div>
        </div>
        <p className="text-base md:text-lg text-navy/80 mb-6 max-w-2xl">
          Un conseil santé simple chaque matin, écrit puis relu par IA selon les recommandations françaises. Il ne remplace pas l&apos;avis de votre médecin.
        </p>
        <Link to={PLAY_TO} data-testid="conseils-cta-play" className="inline-flex items-center gap-2 bg-[#6A994E] text-white font-bold px-6 py-3 rounded-full hover:bg-[#557d3e] transition-colors shadow-warm mb-10">
          <Play className="w-5 h-5" /> Jouer au quiz Bien vieillir
        </Link>

        {notFound && <p className="text-navy/70 mb-6" data-testid="conseils-not-found">Ce conseil est introuvable. Voici les plus récents.</p>}
        {featured && <div className="mb-10"><TipArticle tip={featured} featured /></div>}
        {tips === null ? (
          <p className="text-navy/60" data-testid="conseils-loading">Chargement…</p>
        ) : others.length === 0 ? (
          !featured && <p className="text-navy/70" data-testid="conseils-filter-empty">Le premier conseil de Lucette arrive très bientôt.</p>
        ) : (
          <>
            {featured && <h2 className="font-display text-2xl font-extrabold text-navy mb-4">Les autres conseils</h2>}
            <ThemeFilters tips={others} value={theme} onChange={setTheme} />
            {list.length === 0 ? (
              <p className="text-navy/70" data-testid="conseils-filter-empty">Pas encore de conseil sur ce thème — Lucette y viendra très bientôt.</p>
            ) : (
              <div className="grid gap-5" data-testid="conseils-list">
                {list.map((t, i) => <TipArticle key={t.date_key} tip={t} featured={!featured && !theme && i === 0} />)}
              </div>
            )}
          </>
        )}
        <div className="mt-12 text-sm">
          <Link to="/bien-vieillir" className="font-bold text-navy underline underline-offset-4 hover:text-[#6A994E]" data-testid="conseils-theme-link">
            Découvrir le thème Bien vieillir
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
