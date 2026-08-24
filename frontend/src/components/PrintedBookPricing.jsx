import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BookOpen, Check, Star, Sparkles } from "lucide-react";
import { PRINTED_BOOKS, BOOK_DISCOUNT_BY_TIER, fmt } from "@/config/pricing";
import { api } from "@/lib/api";

/**
 * PrintedBookPricing — 3 offres livre imprimé (1/2/3 livres) + PDF gratuit
 * inclus pour les abonnés. Affiche la remise abonné quand l'utilisateur est
 * connecté (−20 % Solo, −25 % Famille, inclus pour Héritage).
 */
export default function PrintedBookPricing() {
  const [tier, setTier] = useState(null); // 'solo'|'famille'|'heritage'|'decouverte'|null

  useEffect(() => {
    // On tente /auth/me : si connecté on récupère le plan_tier
    api.get("/auth/me").then((r) => {
      setTier(r.data?.plan_tier || r.data?.plan || "decouverte");
    }).catch(() => setTier(null));
  }, []);

  const discount = tier ? BOOK_DISCOUNT_BY_TIER[tier] ?? 0 : 0;
  const hasDiscount = discount > 0 && discount < 1;
  const isIncluded = discount === 1; // Héritage : 1 livre offert/an

  return (
    <div className="mt-16 space-y-4" data-testid="printed-book-pricing">
      <section>
        <div className="text-center max-w-2xl mx-auto mb-8">
          <span className="inline-block bg-mustard text-navy font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
            📖 Livre imprimé
          </span>
          <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3" data-testid="printed-book-title">
            Votre Livre de Vie, <span className="text-terracotta italic">en vrai</span>
          </h2>
          <p className="text-navy/70 leading-relaxed">
            <span className="inline-flex items-center gap-1 bg-[#3D9970]/15 text-[#2A7350] font-bold px-3 py-1 rounded-full text-sm">
              <Check className="w-4 h-4" /> PDF gratuit inclus
            </span>{" "}
            pour tous les abonnés. L&apos;impression est optionnelle : format A5, couverture rigide couleur, envoyé chez vous.
          </p>
          {hasDiscount && (
            <p className="mt-3 text-sm font-bold text-terracotta" data-testid="printed-book-discount-banner">
              🎁 Votre formule vous donne droit à −{Math.round(discount * 100)} % sur ces prix.
            </p>
          )}
          {isIncluded && (
            <p className="mt-3 text-sm font-bold text-[#2A7350]" data-testid="printed-book-included-banner">
              ✨ Un livre imprimé est déjà inclus dans votre formule Héritage chaque année.
            </p>
          )}
        </div>

        <div className="grid md:grid-cols-3 gap-5" data-testid="printed-book-grid">
          {PRINTED_BOOKS.map((o, i) => {
            const finalPrice = hasDiscount ? +(o.prix * (1 - discount)).toFixed(2) : o.prix;
            return (
              <motion.div
                key={o.id}
                initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className={`relative bg-white rounded-3xl p-6 border-2 flex flex-col ${
                  o.highlight ? "border-terracotta shadow-warm scale-[1.02] ring-4 ring-terracotta/15" : "border-cream-dark"
                }`}
                data-testid={`printed-book-card-${o.id}`}
              >
                {o.badge && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full shadow-warm inline-flex items-center gap-1">
                    <Star className="w-3 h-3 fill-current" /> {o.badge}
                  </span>
                )}
                <div className="text-4xl mb-2">{["📕", "📚", "🎁"][i]}</div>
                <h3 className="font-display text-2xl font-extrabold text-navy mb-1">{o.nom}</h3>

                {hasDiscount ? (
                  <div className="mb-1">
                    <div className="text-sm text-navy/40 line-through">{fmt(o.prix)}</div>
                    <span className="font-display text-4xl font-extrabold text-bordeaux">{fmt(finalPrice)}</span>
                  </div>
                ) : (
                  <div className="mb-1">
                    <span className="font-display text-4xl font-extrabold text-bordeaux">{fmt(o.prix)}</span>
                  </div>
                )}
                <p className="text-sm text-navy/60 mb-1">{fmt(o.prixParLivre)} / livre</p>
                {o.economie > 0 && (
                  <p className="text-sm font-bold text-[#2A7350] mb-3">Économie {fmt(o.economie)}</p>
                )}
                <ul className="my-4 space-y-2 flex-1">
                  {o.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-navy/80 text-sm">
                      <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
                      {f}
                    </li>
                  ))}
                </ul>
                <a
                  href={`mailto:contact@generaquiz.fr?subject=${encodeURIComponent("Commande Livre de Vie imprimé - " + o.nom)}`}
                  data-testid={`printed-book-cta-${o.id}`}
                  className={`inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition min-h-[52px] ${
                    o.highlight ? "bg-terracotta text-white hover:bg-terracotta-dark shadow-warm" : "bg-white border-2 border-navy text-navy hover:bg-navy hover:text-cream"
                  }`}
                >
                  <BookOpen className="w-4 h-4" /> Commander
                </a>
              </motion.div>
            );
          })}
        </div>
        <p className="text-center text-xs text-navy/50 mt-4">
          <Sparkles className="w-3 h-3 inline mr-1" />
          Impression à la demande · Livraison France métropolitaine ~10 jours ouvrés · Vous validez la maquette avant impression
        </p>
      </section>
    </div>
  );
}
