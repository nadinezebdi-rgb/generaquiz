import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Lightbulb, ArrowRight } from "lucide-react";
import { api, BACKEND_URL } from "@/lib/api";
import { ShareTipButton } from "@/components/ShareTipButton";

export const fmtTipDate = (k) => {
  const s = new Date(`${k}T12:00:00`).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
  return s.charAt(0).toUpperCase() + s.slice(1);
};
const fmtDate = fmtTipDate;

export const DailyTipCard = ({ ctaTo = "/app/quiz/bien-vieillir", ctaLabel = "Tester mes connaissances" }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    let ignore = false;
    api.get("/tips/today").then((r) => { if (!ignore) setData(r.data); }).catch(() => {});
    return () => { ignore = true; };
  }, []);

  const tip = data?.tip;
  if (!tip) return null;

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      data-testid="daily-tip-card"
      className="relative overflow-hidden rounded-[28px] border-2 border-[#6A994E]/40 bg-[#6A994E]/10 p-6 md:p-7 mb-10"
    >
      <div className="absolute -right-10 -bottom-10 w-48 h-48 rounded-full bg-[#6A994E]/15 pointer-events-none" />
      <div className="relative flex flex-col sm:flex-row gap-5 items-start">
        <img
          src={`${BACKEND_URL}/api/static/mascots/bien-vieillir.png`}
          alt="Lucette la Pétillante"
          className="w-20 h-20 rounded-2xl border-2 border-white shadow-soft object-cover shrink-0 bg-cream"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="inline-flex items-center gap-1 bg-[#6A994E] text-white text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full">
              <Lightbulb className="w-3 h-3" /> Conseil du jour
            </span>
            <span className="text-xs text-navy/60" data-testid="daily-tip-date">
              {data.is_today ? fmtDate(tip.date_key) : `Conseil du ${fmtDate(tip.date_key).toLowerCase()}`} · {tip.theme}
            </span>
          </div>
          <h3 className="font-display text-xl md:text-2xl font-extrabold text-navy mb-2" data-testid="daily-tip-title">
            {tip.title}
          </h3>
          <p className="text-navy/80 leading-relaxed mb-3" data-testid="daily-tip-text">{tip.text}</p>
          <p className="text-sm text-navy font-bold mb-4" data-testid="daily-tip-action">
            Aujourd&apos;hui : <span className="font-normal italic">{tip.action}</span>
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <Link
              to={ctaTo}
              data-testid="daily-tip-quiz-cta"
              className="inline-flex items-center gap-2 bg-[#6A994E] text-white font-bold px-5 py-2.5 rounded-full hover:bg-[#557d3e] transition-colors shadow-soft"
            >
              {ctaLabel} <ArrowRight className="w-4 h-4" />
            </Link>
            <ShareTipButton tip={tip} testId="daily-tip-share-whatsapp" />
            <Link
              to="/conseils-bien-vieillir"
              data-testid="daily-tip-archive-link"
              className="text-sm font-bold text-navy underline underline-offset-4 hover:text-[#6A994E] transition-colors"
            >
              Tous les conseils
            </Link>
          </div>
          <p className="text-xs text-navy/75 mt-3">Conseil général de Lucette, relu par IA — il ne remplace pas l&apos;avis de votre médecin.</p>
        </div>
      </div>
    </motion.section>
  );
};
