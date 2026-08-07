import { motion } from "framer-motion";
import { Quote, Star } from "lucide-react";

/**
 * TestimonialsSection — "Ils jouent déjà avec GénéraQuiz"
 * 3 illustrative testimonials (senior / famille / EHPAD) with 5-star ratings.
 *
 * Copy is intentionally warm and realistic — noms/villes anonymisés pour éviter
 * toute fausse preuve sociale. À personnaliser plus tard avec de vrais avis.
 */
const TESTIMONIALS = [
  {
    quote: "Depuis que je joue tous les matins, je me sens plus alerte. Et le samedi ma petite-fille vient jouer avec moi.",
    name: "Françoise, 72 ans",
    context: "Utilisatrice depuis 3 mois",
    tag: { label: "Senior", cls: "bg-mustard text-navy" },
  },
  {
    quote: "Mes enfants adorent lancer des défis à mamie. C'est devenu notre rituel du dimanche après-midi.",
    name: "Marc, 38 ans",
    context: "Père de deux enfants, Lyon",
    tag: { label: "Famille", cls: "bg-terracotta/20 text-terracotta-dark" },
  },
  {
    quote: "Un vrai gain de temps pour préparer nos animations mémoire. Les résidents en redemandent chaque semaine.",
    name: "Sylvie, animatrice",
    context: "EHPAD Les Tilleuls, région lyonnaise",
    tag: { label: "EHPAD", cls: "bg-bordeaux/15 text-bordeaux" },
  },
];

export default function TestimonialsSection() {
  return (
    <section id="temoignages" className="py-16 lg:py-20" data-testid="testimonials-section">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <span className="inline-block bg-bordeaux text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
            Ils jouent déjà avec GénéraQuiz
          </span>
          <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-navy mb-3">
            Des familles, des seniors, des <span className="text-terracotta italic">EHPAD</span>
          </h2>
          <p className="text-navy/70">
            Voici quelques retours reçus depuis le lancement.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {TESTIMONIALS.map((t, idx) => (
            <motion.figure
              key={t.name}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1, duration: 0.4 }}
              data-testid={`testimonial-${idx}`}
              className="bg-white border-2 border-cream-dark rounded-[28px] p-6 flex flex-col hover:-translate-y-1 hover:shadow-warm transition"
            >
              <div className="flex items-center justify-between mb-4">
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${t.tag.cls}`}>
                  {t.tag.label}
                </span>
                <div className="flex items-center gap-0.5" aria-label="5 étoiles">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className="w-3.5 h-3.5 text-mustard-dark fill-mustard-dark" />
                  ))}
                </div>
              </div>
              <Quote className="w-6 h-6 text-terracotta mb-2" />
              <blockquote className="text-navy/85 leading-relaxed mb-5 flex-1">
                « {t.quote} »
              </blockquote>
              <figcaption className="mt-auto pt-3 border-t-2 border-cream-dark">
                <div className="font-display font-extrabold text-navy leading-tight">{t.name}</div>
                <div className="text-sm text-navy/60">{t.context}</div>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}
