import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Gift, Loader2, Printer, CalendarHeart, Users } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { FamilyAccessTable } from "@/components/FamilyAccessTable";
import { GIFTS, fmt } from "@/config/pricing";
import { api, formatError } from "@/lib/api";
import { useGiftOffers } from "@/lib/gifts";

const HERO_IMG = "https://images.unsplash.com/photo-1758612897055-3d17a4a1e8fb?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200";
const input = "w-full rounded-xl border-2 border-cream-dark bg-white px-4 py-3 text-navy text-base focus:border-navy outline-none";

function Hero({ promo, famille }) {
  const noel = promo?.active;
  return (
    <section className={noel ? "bg-navy-dark text-cream" : "bg-cream/60 text-navy"} data-testid="offrir-hero">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 lg:py-20 grid lg:grid-cols-[1.1fr_1fr] gap-10 items-center">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <span className={`inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] mb-5 ${noel ? "text-mustard" : "text-terracotta"}`}>
            <Gift className="w-4 h-4" /> {noel ? promo.title : "Offrir GénéraQuiz"}
          </span>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.05] mb-5">
            Offrez une année de <span className={noel ? "text-mustard italic" : "text-terracotta italic"}>moments à partager</span>
          </h1>
          <p className={`text-base md:text-lg mb-6 max-w-xl ${noel ? "text-cream/80" : "text-navy/75"}`}>
            Offre Famille — 1 bénéficiaire + 4 proches pour partager une année de jeux. Une carte à imprimer, un code à glisser sous le sapin.
          </p>
          {famille && (
            <div className="flex items-baseline gap-3" data-testid="offrir-hero-price">
              {famille.regular_price && <span className="text-2xl line-through opacity-60">{fmt(famille.regular_price, { integer: true })}</span>}
              <span className={`font-display text-5xl font-extrabold ${noel ? "text-mustard" : "text-bordeaux"}`}>{fmt(famille.price, { integer: true })}</span>
              <span className="opacity-80">pour 1 an</span>
            </div>
          )}
          {noel && <p className="text-sm text-cream/70 mt-2" data-testid="offrir-promo-end">Prix de Noël jusqu&apos;au {new Date(promo.ends_on).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}</p>}
        </motion.div>
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6, delay: 0.1 }}
          className={`rounded-[28px] overflow-hidden border-4 ${noel ? "border-mustard/70" : "border-white"} shadow-warm aspect-[4/3]`}>
          <img src={HERO_IMG} alt="Un grand-père et son petit-fils jouent ensemble sur une tablette" className="w-full h-full object-cover" />
        </motion.div>
      </div>
    </section>
  );
}

function OfferPicker({ offers, value, onChange }) {
  return (
    <div className="grid sm:grid-cols-2 gap-4" role="radiogroup">
      {GIFTS.map((g) => {
        const o = offers?.find((x) => x.id === g.id);
        const active = value === g.id;
        return (
          <button key={g.id} type="button" role="radio" aria-checked={active} onClick={() => onChange(g.id)} data-testid={`offrir-offer-${g.id}`}
            className={`text-left rounded-2xl p-5 border-2 transition-colors ${active ? "border-terracotta bg-white ring-4 ring-terracotta/15" : "border-cream-dark bg-white/70 hover:border-navy/40"}`}>
            <div className="flex items-center gap-2 mb-1">
              {g.id === "famille" ? <Users className="w-5 h-5 text-terracotta" /> : <Gift className="w-5 h-5 text-terracotta" />}
              <span className="font-display text-xl font-extrabold text-navy">{g.nom}</span>
            </div>
            <div className="flex items-baseline gap-2 mb-1">
              {o?.regular_price && <span className="line-through text-navy/50">{fmt(o.regular_price, { integer: true })}</span>}
              <span className="font-display text-2xl font-extrabold text-bordeaux">{o ? fmt(o.price, { integer: true }) : "…"}</span>
              <span className="text-sm text-navy/60">pour 1 an</span>
            </div>
            <p className="text-sm text-navy/70">{g.description}</p>
          </button>
        );
      })}
    </div>
  );
}

function GiftForm({ offer }) {
  const [f, setF] = useState({ recipient_name: "", buyer_name: "", buyer_email: "", message: "" });
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/gifts/checkout", { ...f, offer, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
      setLoading(false);
    }
  }
  return (
    <form onSubmit={submit} className="grid gap-4" data-testid="offrir-form">
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="font-semibold text-navy">Pour qui ?
          <input required maxLength={40} value={f.recipient_name} onChange={set("recipient_name")} placeholder="Ex. Mamie Jeanne" className={`${input} mt-1`} data-testid="offrir-recipient" />
        </label>
        <label className="font-semibold text-navy">De la part de
          <input required maxLength={40} value={f.buyer_name} onChange={set("buyer_name")} placeholder="Ex. Léa et Tom" className={`${input} mt-1`} data-testid="offrir-buyer-name" />
        </label>
      </div>
      <label className="font-semibold text-navy">Votre e-mail <span className="font-normal text-navy/60 text-sm">(pour le reçu)</span>
        <input required type="email" value={f.buyer_email} onChange={set("buyer_email")} placeholder="vous@exemple.fr" className={`${input} mt-1`} data-testid="offrir-buyer-email" />
      </label>
      <label className="font-semibold text-navy">Petit mot imprimé sur la carte <span className="font-normal text-navy/60 text-sm">(facultatif)</span>
        <textarea maxLength={240} rows={3} value={f.message} onChange={set("message")} placeholder="Pour jouer ensemble toute l'année…" className={`${input} mt-1`} data-testid="offrir-message" />
      </label>
      <button type="submit" disabled={loading} data-testid="offrir-submit"
        className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full shadow-warm transition-colors disabled:opacity-70 min-h-[56px]">
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Gift className="w-5 h-5" />}
        {loading ? "Redirection vers le paiement…" : "Payer et recevoir la carte"}
      </button>
      <ul className="grid sm:grid-cols-2 gap-2 text-sm text-navy/70">
        <li className="flex items-center gap-2"><Printer className="w-4 h-4 text-terracotta" /> Carte PDF à imprimer juste après le paiement</li>
        <li className="flex items-center gap-2"><CalendarHeart className="w-4 h-4 text-terracotta" /> L&apos;année commence le jour de l&apos;activation</li>
      </ul>
    </form>
  );
}

export default function Offrir() {
  const [params] = useSearchParams();
  const data = useGiftOffers();
  const [offer, setOffer] = useState(params.get("offre") === "solo" ? "solo" : "famille");
  const famille = data?.offers.find((o) => o.id === "famille");
  return (
    <div className="min-h-screen bg-bgmain">
      <Navbar />
      <Hero promo={data?.promo} famille={famille} />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-14 grid gap-10 [&>*]:min-w-0" data-testid="offrir-page">
        <section>
          <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-5">1. Choisissez le cadeau</h2>
          <OfferPicker offers={data?.offers} value={offer} onChange={setOffer} />
        </section>
        {offer === "famille" && (
          <section>
            <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-2">Qui a accès à quoi ?</h2>
            <p className="text-navy/70 mb-4">1 abonnement complet pour le bénéficiaire + 4 accès aux jeux en famille inclus pendant un an.</p>
            <FamilyAccessTable />
          </section>
        )}
        <section className="bg-white rounded-3xl border-2 border-cream-dark p-6 sm:p-8 shadow-warm">
          <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-5">2. Personnalisez la carte</h2>
          <GiftForm offer={offer} />
        </section>
      </main>
      <Footer />
    </div>
  );
}
