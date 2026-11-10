import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Play, Sparkles, MessageCircle, ArrowRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { api } from "@/lib/api";
import { mascotSrc } from "@/lib/mascot";

export const themePath = (id) =>
  id === "bien-vieillir" ? "/bien-vieillir" : id === "voyages-france" ? "/voyages-france" : `/decouvrir/${id}`;

function SampleCard({ s, i, color }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.button
      type="button"
      onClick={() => setOpen(true)}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.05, duration: 0.4 }}
      viewport={{ once: true }}
      data-testid={`theme-sample-${i}`}
      className="text-left bg-cream rounded-2xl border-2 border-cream-dark p-5 hover:border-terracotta transition-colors"
    >
      <p className="font-bold text-navy mb-2">{s.question}</p>
      {open ? (
        <div data-testid={`theme-sample-answer-${i}`}>
          <p className="text-sm font-mono font-bold mb-1" style={{ color }}>→ {s.answer}</p>
          {s.explanation && <p className="text-xs text-navy/70 leading-relaxed">{s.explanation}</p>}
        </div>
      ) : (
        <p className="text-sm font-mono text-navy/40">Voir la réponse</p>
      )}
    </motion.button>
  );
}

export default function ThemeShowcase() {
  const { categoryId } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let ignore = false;
    setData(null);
    api.get(`/categories/${categoryId}/showcase`)
      .then((r) => { if (!ignore) setData(r.data); })
      .catch(() => { if (!ignore) setErr(true); });
    return () => { ignore = true; };
  }, [categoryId]);

  useEffect(() => {
    if (!data) return undefined;
    const prev = document.title;
    const meta = document.querySelector('meta[name="description"]');
    const prevDesc = meta?.getAttribute("content");
    document.title = `Quiz ${data.category.title} : questions et souvenirs à partager | GénéraQuiz`;
    meta?.setAttribute("content", `Quiz ${data.category.title} — ${data.category.description} Des questions vérifiées à jouer en famille avec ${data.category.mascot_name}.`);
    return () => {
      document.title = prev;
      if (meta && prevDesc) meta.setAttribute("content", prevDesc);
    };
  }, [data]);

  if (err) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="landing" />
        <div className="max-w-3xl mx-auto p-12" data-testid="theme-not-found">
          <p className="text-navy text-xl mb-6">Ce thème n&apos;existe pas.</p>
          <Link to="/" className="text-terracotta font-bold underline">Retour à l&apos;accueil</Link>
        </div>
      </div>
    );
  }
  if (!data) return <div className="min-h-screen paper-bg" data-testid="theme-loading" />;

  const { category: c, samples, others } = data;
  const playTo = `/register?next=/app/quiz/${c.id}`;
  const prompt = samples.find((s) => s.discussion_prompt);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="landing" />
      <main data-testid={`theme-showcase-${c.id}`}>
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-16 grid md:grid-cols-2 gap-10 items-center">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <span className="inline-flex items-center gap-2 text-navy font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-4" style={{ backgroundColor: `${c.color}33` }}>
              <Sparkles className="w-3.5 h-3.5" style={{ color: c.color }} /> Thème du quiz · {c.count} questions vérifiées
            </span>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy leading-[1.05] mb-4" data-testid="theme-title">
              {c.title}
            </h1>
            <p className="text-base md:text-lg text-navy/80 leading-relaxed mb-7">
              {c.description} Un quiz à jouer en famille, avec la complicité de <b>{c.mascot_name}</b>.
            </p>
            <div className="flex gap-3 flex-wrap">
              <Link to={playTo} data-testid="theme-cta-play" className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark transition-colors shadow-warm">
                <Play className="w-5 h-5" /> Jouer gratuitement
              </Link>
              <Link to="/quiz-du-jour" data-testid="theme-cta-daily" className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy font-bold px-6 py-3 rounded-full hover:bg-navy hover:text-white transition-colors">
                Essayer le Quiz du jour
              </Link>
            </div>
          </motion.div>
          <motion.div initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.15 }} className="relative">
            <div className="absolute -inset-4 rounded-full blur-3xl" style={{ backgroundColor: `${c.color}22` }} />
            <img src={mascotSrc(c.mascot_image, "md")} alt={`${c.mascot_name}, mascotte du thème ${c.title}`} data-testid="theme-mascot-image" className="relative w-full max-w-md mx-auto rounded-3xl shadow-2xl" />
            <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 bg-white rounded-full px-5 py-2 shadow-warm border-2 border-cream-dark whitespace-nowrap">
              <span className="font-display font-extrabold text-navy">{c.mascot_name}</span>
            </div>
          </motion.div>
        </section>

        {samples.length > 0 && (
          <section className="bg-white py-16">
            <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
              <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-2">Les questions de la semaine</h2>
              <p className="text-navy/70 mb-8">Touchez une carte pour voir la réponse. Nouvelle sélection chaque lundi.</p>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="theme-samples">
                {samples.map((s, i) => <SampleCard key={s.question} s={s} i={i} color={c.color} />)}
              </div>
            </div>
          </section>
        )}

        {prompt && (
          <section className="py-16" style={{ backgroundColor: `${c.color}14` }}>
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
              <span className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
                <MessageCircle className="w-3.5 h-3.5" /> En famille & en EHPAD
              </span>
              <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-4">Une question, puis on raconte.</h2>
              <div className="bg-white rounded-2xl border-2 border-cream-dark p-6 shadow-warm" data-testid="theme-discussion">
                <p className="text-navy font-bold mb-2">« {prompt.question} »</p>
                <p className="text-sm text-navy/60 mb-3">Puis la relance :</p>
                <p className="font-bold italic" style={{ color: c.color }}>« {prompt.discussion_prompt} »</p>
              </div>
            </div>
          </section>
        )}

        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-6">Les autres thèmes</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3" data-testid="theme-others">
            {others.map((o) => (
              <Link key={o.id} to={themePath(o.id)} data-testid={`theme-other-${o.id}`} className="group bg-white border-2 border-cream-dark rounded-2xl p-3 hover:border-terracotta transition-colors flex items-center gap-3">
                <img src={mascotSrc(o.mascot_image, "sm")} loading="lazy" alt="" className="w-12 h-12 rounded-xl object-cover bg-cream shrink-0" />
                <span className="text-sm font-bold text-navy leading-tight">{o.title}</span>
              </Link>
            ))}
          </div>
          <Link to={playTo} data-testid="theme-cta-play-bottom" className="mt-10 inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark transition-colors shadow-warm">
            Créer mon compte gratuit <ArrowRight className="w-4 h-4" />
          </Link>
        </section>
      </main>
      <Footer />
    </div>
  );
}
