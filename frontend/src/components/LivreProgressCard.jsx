import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { BookOpen, Camera, Feather, ArrowRight, Layers } from "lucide-react";

/**
 * LivreProgressCard — widget Dashboard "Votre Livre de Vie prend forme".
 *
 * Ne s'affiche que si l'utilisateur a au moins 1 entrée. Sinon on garde
 * la carte "Souvenir du jour" (déjà présente) comme point d'entrée.
 * Progression : barre + 4 stats + CTA "Feuilleter".
 */
export default function LivreProgressCard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/livre/progression").then((r) => setData(r.data)).catch((err) => {
      console.debug("Livre progression fetch failed:", err);
    });
  }, []);

  // On masque le widget tant qu'aucun souvenir n'a été écrit — le "Souvenir
  // du jour" (déjà présent au-dessus) sert de tremplin initial.
  if (!data || data.total_entries === 0) return null;

  const percent = data.progression_percent || 0;

  return (
    <div
      className="bg-white rounded-[24px] border-2 border-navy/20 p-6 md:p-7 mb-10 shadow-warm"
      data-testid="livre-progress-card"
    >
      <div className="flex flex-col lg:flex-row items-start lg:items-center gap-5">
        <div className="bg-navy text-cream rounded-2xl p-3 shrink-0">
          <BookOpen className="w-8 h-8" />
        </div>
        <div className="flex-1 w-full">
          <span className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-2">
            Votre Livre de Vie prend forme
          </span>
          <h3 className="font-display text-2xl font-extrabold text-navy mb-3">
            {data.total_entries} souvenir{data.total_entries > 1 ? "s" : ""} racontés · ≈ {data.estimated_pages} pages
          </h3>

          {/* Barre de progression */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm font-semibold text-navy/70 mb-1.5">
              <span>{data.chapters_completed}/{data.chapters_total} chapitres complétés</span>
              <span>{percent}%</span>
            </div>
            <div className="w-full h-3 rounded-full bg-cream-dark overflow-hidden" data-testid="livre-progress-bar">
              <div
                className="h-full bg-gradient-to-r from-terracotta to-mustard-dark transition-all"
                style={{ width: `${Math.max(percent, 3)}%` }}
              />
            </div>
          </div>

          {/* Mini stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
            <Stat icon={Feather} value={data.total_entries} label="souvenirs" />
            <Stat icon={Camera} value={data.total_photos} label="photos" />
            <Stat icon={Layers} value={`${data.chapters_started}/${data.chapters_total}`} label="chapitres" />
            <Stat icon={BookOpen} value={`${data.estimated_pages}`} label="pages" />
          </div>
        </div>

        <Link
          to="/app/livre"
          data-testid="livre-progress-cta"
          className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-5 py-3 rounded-full hover:bg-navy-dark transition shrink-0 min-h-[52px]"
        >
          Feuilleter mon livre <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, value, label }) {
  return (
    <div className="bg-cream rounded-xl border border-cream-dark px-3 py-2 flex items-center gap-2">
      <Icon className="w-4 h-4 text-terracotta shrink-0" />
      <div className="min-w-0">
        <div className="font-display font-extrabold text-navy leading-none text-lg">{value}</div>
        <div className="text-xs text-navy/60 truncate">{label}</div>
      </div>
    </div>
  );
}
