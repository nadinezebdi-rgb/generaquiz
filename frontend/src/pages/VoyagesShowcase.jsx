import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { MapPin, MessageCircle, Sparkles, ArrowRight, Play, Building2, Heart } from "lucide-react";

/**
 * VoyagesShowcase — page marketing dédiée à la catégorie "Voyages & régions
 * de France". Mise en avant de la mascotte Jeanne, exemples de questions,
 * pitch "déclencheur de conversation" pour les familles ET les EHPAD.
 */
export default function VoyagesShowcase() {
  const backend = process.env.REACT_APP_BACKEND_URL;
  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="landing" />
      <main data-testid="voyages-showcase">
        {/* ============ HERO ============ */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-16">
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
              <span className="inline-flex items-center gap-2 bg-mustard/40 text-navy font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-4">
                🧳 Nouvelle catégorie
              </span>
              <h1 className="font-display text-5xl md:text-6xl font-extrabold text-navy leading-[1.05] mb-4">
                Voyages & <span className="text-terracotta italic">régions de France</span>
              </h1>
              <p className="text-xl text-navy/80 leading-relaxed mb-6">
                Régions, monuments, paysages, traditions et souvenirs de vacances. 100 questions pour re-voyager en France, avec la complicité de <b>Jeanne la Voyageuse</b>.
              </p>
              <div className="flex gap-3 flex-wrap">
                <Link
                  to="/quiz/voyages-france"
                  data-testid="voyages-cta-play"
                  className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark transition shadow-warm"
                >
                  <Play className="w-5 h-5" /> Jouer maintenant
                </Link>
                <Link
                  to="/ehpad"
                  data-testid="voyages-cta-ehpad"
                  className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy font-bold px-6 py-3 rounded-full hover:bg-navy hover:text-white transition"
                >
                  <Building2 className="w-5 h-5" /> Découvrir l&apos;offre EHPAD
                </Link>
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, scale: 0.9, rotate: -3 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="relative"
            >
              <div className="absolute -inset-4 bg-terracotta/10 rounded-full blur-3xl" />
              <img
                src={`${backend}/api/static/mascots/voyages-france.png`}
                alt="Jeanne la Voyageuse, mascotte de la catégorie Voyages & régions de France"
                className="relative w-full max-w-md mx-auto rounded-3xl shadow-2xl"
                data-testid="voyages-jeanne-image"
              />
              <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 bg-white rounded-full px-5 py-2 shadow-warm border-2 border-cream-dark">
                <span className="font-display font-extrabold text-navy">👩‍🦳 Jeanne la Voyageuse</span>
              </div>
            </motion.div>
          </div>
        </section>

        {/* ============ EXEMPLES DE QUESTIONS ============ */}
        <section className="bg-white py-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-10">
              <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
                <Sparkles className="w-3.5 h-3.5" /> Un aperçu
              </span>
              <h2 className="font-display text-4xl font-extrabold text-navy">Quelques questions qui vous attendent</h2>
              <p className="text-navy/70 mt-2 max-w-2xl mx-auto">Chacune revisite un lieu, une tradition ou un souvenir de vacances français.</p>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { q: "Dans quelle région se trouve le Mont-Saint-Michel ?", a: "Normandie" },
                { q: "Quelle ville est surnommée la Ville Rose ?", a: "Toulouse" },
                { q: "Quel fleuve traverse Paris ?", a: "La Seine" },
                { q: "Quelle région est célèbre pour ses champs de lavande ?", a: "La Provence" },
                { q: "Quelle spécialité associez-vous à l'Alsace ?", a: "La choucroute" },
                { q: "Quelle île est surnommée « l'île de Beauté » ?", a: "La Corse" },
              ].map((qa, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.4 }}
                  viewport={{ once: true }}
                  className="bg-cream rounded-2xl border-2 border-cream-dark p-5"
                >
                  <MapPin className="w-5 h-5 text-terracotta mb-2" />
                  <p className="font-bold text-navy mb-2">{qa.q}</p>
                  <p className="text-sm text-terracotta font-mono">→ {qa.a}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* ============ EHPAD : DECLENCHEUR DE CONVERSATION ============ */}
        <section className="py-16 bg-gradient-to-br from-terracotta/10 to-mustard/20">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-2 gap-10 items-center">
              <div>
                <span className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
                  <MessageCircle className="w-3.5 h-3.5" /> Innovation EHPAD
                </span>
                <h2 className="font-display text-4xl font-extrabold text-navy mb-4">Bien plus qu&apos;un quiz : un déclencheur de conversation.</h2>
                <p className="text-lg text-navy/80 mb-4 leading-relaxed">
                  Chaque question importante est doublée d&apos;une relance douce vers le vécu des résidents.
                </p>
                <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm">
                  <p className="text-navy mb-2 font-bold">🎯 « Dans quelle région se trouve le Mont-Saint-Michel ? »</p>
                  <p className="text-sm text-navy/60 mb-3">Puis la relance :</p>
                  <p className="text-terracotta font-bold italic">🗣️ « Et vous, avez-vous déjà eu la chance de visiter le Mont-Saint-Michel ? »</p>
                </div>
              </div>
              <motion.blockquote
                initial={{ opacity: 0, x: 24 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6 }}
                viewport={{ once: true }}
                className="bg-white rounded-2xl border-2 border-cream-dark p-6 shadow-warm relative"
                data-testid="voyages-ehpad-testimonial"
              >
                <Heart className="absolute -top-3 -left-3 w-8 h-8 text-terracotta bg-cream rounded-full p-1.5 border-2 border-cream-dark" />
                <p className="text-navy leading-relaxed text-lg italic mb-4">
                  « Avec la catégorie Voyages, nos résidents ne se contentent plus de trouver la bonne réponse : ils <b>racontent</b>. Une question sur la Provence, et on part 40 minutes sur les vacances de 1962. C&apos;est devenu notre atelier le plus attendu. »
                </p>
                <footer className="text-sm text-navy/70">
                  <b>Anne-Marie R.</b> — Animatrice, EHPAD des Cèdres (Nantes)
                </footer>
              </motion.blockquote>
            </div>
          </div>
        </section>

        {/* ============ CTA FINAL ============ */}
        <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
          <h2 className="font-display text-4xl font-extrabold text-navy mb-3">Prêt(e) à voyager avec Jeanne ?</h2>
          <p className="text-navy/70 text-lg mb-6">100 questions, 6 régions, des souvenirs plein la valise.</p>
          <div className="flex justify-center gap-3 flex-wrap">
            <Link
              to="/quiz/voyages-france"
              data-testid="voyages-cta-play-bottom"
              className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark transition shadow-warm"
            >
              <Play className="w-5 h-5" /> Commencer une partie <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/tarifs"
              className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy font-bold px-6 py-3 rounded-full hover:bg-navy hover:text-white transition"
            >
              Voir les abonnements
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
