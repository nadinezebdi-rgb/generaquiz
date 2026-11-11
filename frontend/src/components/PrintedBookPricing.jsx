import { motion } from "framer-motion";
import { BookOpen, Check } from "lucide-react";
import { PRINTED_BOOK, fmt } from "@/config/pricing";

/** PrintedBookPricing — option séparée : 1 exemplaire imprimé, commandé quand le Livre de Vie est prêt. */
export default function PrintedBookPricing() {
  return (
    <section className="mt-16" data-testid="printed-book-pricing">
      <motion.div
        initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
        className="max-w-4xl mx-auto bg-white rounded-3xl border-2 border-cream-dark p-6 sm:p-8 grid md:grid-cols-[1.3fr_1fr] gap-6 items-center"
      >
        <div>
          <span className="inline-flex items-center gap-1 bg-mustard text-navy font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
            <BookOpen className="w-3.5 h-3.5" /> Option livre imprimé
          </span>
          <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3" data-testid="printed-book-title">
            Votre Livre de Vie, <span className="text-terracotta italic">en vrai</span>
          </h2>
          <p className="text-navy/70 mb-4">
            Le PDF est inclus dans Solo et Famille. Quand votre Livre de Vie est prêt, vous pouvez commander un exemplaire imprimé, envoyé chez vous.
          </p>
          <ul className="grid sm:grid-cols-2 gap-2">
            {PRINTED_BOOK.features.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm text-navy/80">
                <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} /> {f}
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-cream/70 rounded-2xl p-6 text-center">
          <div className="font-display text-4xl font-extrabold text-bordeaux" data-testid="printed-book-price">{fmt(PRINTED_BOOK.prix)}</div>
          <p className="text-sm text-navy/60 mb-4">l&apos;exemplaire, TTC</p>
          <a
            href={`mailto:contact@generaquiz.fr?subject=${encodeURIComponent("Commande Livre de Vie imprimé")}`}
            data-testid="printed-book-cta"
            className="inline-flex items-center justify-center gap-2 bg-navy text-cream font-bold px-6 py-3 rounded-full hover:bg-terracotta transition-colors min-h-[52px]"
          >
            <BookOpen className="w-4 h-4" /> Commander mon livre
          </a>
        </div>
      </motion.div>
    </section>
  );
}
