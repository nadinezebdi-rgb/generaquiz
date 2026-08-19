import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { BarChart3, Gift, Flag, ArrowRight, ShieldCheck } from "lucide-react";

/**
 * AdminHome — page d'index de l'espace admin.
 *
 * Tableau de bord central listant les outils admin disponibles :
 *   - Analytics (KPI signups, CA, ateliers, catégories)
 *   - Promo (création/toggle/suppression de codes promo)
 *   - Reports (modération des signalements de questions)
 *
 * Toute la protection est faite par <AdminRoute> côté client + get_admin_user
 * côté serveur — cette page ne fait que du routage.
 */

const TILES = [
  {
    to: "/app/admin/analytics",
    icon: BarChart3,
    label: "Analytics",
    desc: "Signups, chiffre d'affaires, catégories populaires, ateliers.",
    accent: "bg-terracotta/20 text-terracotta",
    testid: "admin-tile-analytics",
  },
  {
    to: "/app/admin/promo",
    icon: Gift,
    label: "Codes promo",
    desc: "Créer, activer/désactiver et supprimer les codes promo.",
    accent: "bg-mustard/25 text-mustard-dark",
    testid: "admin-tile-promo",
  },
  {
    to: "/app/admin/reports",
    icon: Flag,
    label: "Signalements",
    desc: "Modérer les questions signalées par les utilisateurs.",
    accent: "bg-navy/10 text-navy",
    testid: "admin-tile-reports",
  },
];

export default function AdminHome() {
  return (
    <div className="min-h-screen bg-cream text-navy">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-bordeaux text-cream flex items-center justify-center">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <span className="inline-block bg-bordeaux text-cream text-xs font-bold uppercase tracking-wider px-3 py-0.5 rounded-full mb-1">
              Espace administrateur
            </span>
            <h1 className="font-display text-3xl md:text-4xl font-extrabold" data-testid="admin-home-title">
              Tableau de bord
            </h1>
          </div>
        </div>
        <p className="text-navy/70 mb-8">
          Accédez aux outils d&apos;administration de GénéraQuiz. Chaque section est protégée par un contrôle de rôle serveur.
        </p>

        <div className="grid md:grid-cols-3 gap-4">
          {TILES.map((t, i) => {
            const Icon = t.icon;
            return (
              <motion.div
                key={t.to}
                initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
              >
                <Link
                  to={t.to}
                  data-testid={t.testid}
                  className="block bg-white rounded-2xl border-2 border-cream-dark p-5 hover:-translate-y-0.5 hover:border-terracotta hover:shadow-warm transition h-full"
                >
                  <div className={`w-12 h-12 rounded-xl ${t.accent} flex items-center justify-center mb-3`}>
                    <Icon className="w-6 h-6" strokeWidth={2.5} />
                  </div>
                  <h2 className="font-display text-xl font-extrabold mb-1">{t.label}</h2>
                  <p className="text-sm text-navy/70 mb-3">{t.desc}</p>
                  <span className="inline-flex items-center gap-1 text-terracotta font-bold text-sm">
                    Ouvrir <ArrowRight className="w-4 h-4" />
                  </span>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </main>
      <Footer />
    </div>
  );
}
