import { useEffect, useState } from "react";
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

function Hero({ promo, selected }) {
  const noel = promo?.active && selected?.id === "famille";
  const famille = selected;
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
            {selected?.id === "solo"
                ? "Offre Solo — une année complète de quiz et de souvenirs. Une carte à imprimer, un code à glisser sous le sapin."
              : noel
                ? "Offre Noël — possibilité de jouer avec 3 membres au quiz pendant un an. Une carte personnalisée à imprimer."
                : "Offre Famille — 1 bénéficiaire + 4 proches pour partager une année de jeux. Une carte à imprimer, un code à offrir."}
          </p>
          {famille && (
            <div className="flex items-baseline gap-3" data-testid="offrir-hero-price">
              {famille.regular_price && <span className="text-2xl line-through opacity-60">{fmt(famille.regular_price, { integer: true })}</span>}
              <span className={`font-display text-5xl font-extrabold ${noel ? "text-mustard" : "text-bordeaux"}`}>{fmt(famille.price, { integer: true })}</span>
              <span className="opacity-80">pour 1 an</span>
            </div>
          )}
          {noel && <p className="text-sm text-cream/70 mt-2" data-testid="offrir-promo-end">Prix de Noël jusqu&apos;au 24 décembre 2026 inclus</p>}
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
      {(offers || []).map((o) => {
        const preset = GIFTS.find((item) => item.id === o.id);
        const label = o.label || preset?.nom || "Carte cadeau";
        const description = o.id === "noel" ? "1 accès personnel complet pendant un an, à activer quand vous le souhaitez."
          : preset?.description || "Une année de jeux à offrir.";
        const active = value === o.id;
        return (
          <button key={o.id} type="button" role="radio" aria-checked={active} onClick={() => onChange(o.id)} data-testid={`offrir-offer-${o.id}`}
            className={`text-left rounded-2xl p-5 border-2 transition-colors ${active ? "border-terracotta bg-white ring-4 ring-terracotta/15" : "border-cream-dark bg-white/70 hover:border-navy/40"}`}>
            <div className="flex items-center gap-2 mb-1">
              {o.id === "famille" ? <Users className="w-5 h-5 text-terracotta" /> : <Gift className="w-5 h-5 text-terracotta" />}
              <span className="font-display text-xl font-extrabold text-navy">{label}</span>
            </div>
            <div className="flex items-baseline gap-2 mb-1">
              {o?.regular_price && <span className="line-through text-navy/50">{fmt(o.regular_price, { integer: true })}</span>}
              <span className="font-display text-2xl font-extrabold text-bordeaux">{o ? fmt(o.price, { integer: true }) : "…"}</span>
              <span className="text-sm text-navy/60">pour 1 an</span>
            </div>
            <p className="text-sm text-navy/70">{description}</p>
          </button>
        );
      })}
    </div>
  );
}

function GiftForm({ offer, isChristmas }) {
  const [f, setF] = useState({ buyer_full_name: "", buyer_email: "", recipient_name: "", buyer_name: "", message: "", delivery_method: "self", recipient_email: "", delivery_date: "" });
  const [theme, setTheme] = useState("noel_femme");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/gifts/checkout", {
        ...f, offer, theme: isChristmas ? theme : "classic", origin_url: window.location.origin,
        recipient_email: f.delivery_method === "direct" ? f.recipient_email : null,
        delivery_date: f.delivery_method === "direct" ? f.delivery_date : null,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
      setLoading(false);
    }
  }
  return (
    <form onSubmit={submit} className="grid gap-4" data-testid="offrir-form">
      {isChristmas && (
        <fieldset className="grid gap-2">
          <legend className="font-semibold text-navy">Modèle de carte</legend>
          <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Modèle de carte">
            {[{ id: "noel_femme", label: "Modèle femme" }, { id: "noel_homme", label: "Modèle homme" }].map((model) => (
              <button
                key={model.id}
                type="button"
                role="radio"
                aria-checked={theme === model.id}
                onClick={() => setTheme(model.id)}
                data-testid={`offrir-model-${model.id}`}
                className={`min-h-12 rounded-xl border-2 px-4 py-3 text-left font-semibold transition-colors ${theme === model.id ? "border-bordeaux bg-bordeaux text-white" : "border-cream-dark bg-white text-navy hover:border-bordeaux"}`}
              >
                {model.label}
              </button>
            ))}
          </div>
        </fieldset>
      )}
      <h3 className="font-display text-xl font-bold text-bordeaux">01 · Vos coordonnées</h3>
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="font-semibold text-navy">Votre prénom et votre nom
          <input required maxLength={80} value={f.buyer_full_name} onChange={set("buyer_full_name")} className={`${input} mt-1`} data-testid="offrir-buyer-full-name" />
        </label>
        <label className="font-semibold text-navy">Votre e-mail
          <input required type="email" value={f.buyer_email} onChange={set("buyer_email")} placeholder="vous@exemple.fr" className={`${input} mt-1`} data-testid="offrir-buyer-email" />
        </label>
      </div>
      <h3 className="font-display text-xl font-bold text-bordeaux">02 · Votre carte à offrir</h3>
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="font-semibold text-navy">Pour qui ?
          <input required maxLength={40} value={f.recipient_name} onChange={set("recipient_name")} placeholder="Ex. Mamie Jeanne" className={`${input} mt-1`} data-testid="offrir-recipient" />
        </label>
        <label className="font-semibold text-navy">De la part de
          <input required maxLength={40} value={f.buyer_name} onChange={set("buyer_name")} placeholder="Ex. Léa et Tom" className={`${input} mt-1`} data-testid="offrir-buyer-name" />
        </label>
      </div>
      <label className="font-semibold text-navy">Petit mot imprimé sur la carte <span className="font-normal text-navy/60 text-sm">(facultatif)</span>
        <textarea maxLength={240} rows={3} value={f.message} onChange={set("message")} placeholder="Pour jouer ensemble toute l'année…" className={`${input} mt-1`} data-testid="offrir-message" />
      </label>
      <fieldset className="grid gap-3">
        <legend className="font-display text-xl font-bold text-bordeaux mb-2">03 · La remise du cadeau</legend>
        <p className="text-sm text-navy/60">Choisir un seul mode</p>
        <label className="flex gap-3 items-start rounded-xl border-2 border-cream-dark p-4 cursor-pointer">
          <input type="radio" name="delivery_method" value="self" checked={f.delivery_method === "self"} onChange={set("delivery_method")} className="mt-1 accent-bordeaux" />
          <span><strong>Je reçois la carte pour l’offrir moi-même</strong><span className="block text-sm text-navy/65">Pour l’imprimer ou la transmettre à mon proche.</span></span>
        </label>
        <label className="flex gap-3 items-start rounded-xl border-2 border-cream-dark p-4 cursor-pointer">
          <input type="radio" name="delivery_method" value="direct" checked={f.delivery_method === "direct"} onChange={set("delivery_method")} className="mt-1 accent-bordeaux" />
          <span><strong>Envoi direct par e-mail au bénéficiaire</strong><span className="block text-sm text-navy/65">À la date souhaitée ci-dessous.</span></span>
        </label>
        {f.delivery_method === "direct" && (
          <div className="grid sm:grid-cols-2 gap-4">
            <label className="font-semibold text-navy">E-mail du bénéficiaire
              <input required type="email" maxLength={254} value={f.recipient_email} onChange={set("recipient_email")} className={`${input} mt-1`} data-testid="offrir-recipient-email" />
            </label>
            <label className="font-semibold text-navy">Date d’envoi souhaitée
              <input required type="date" min={new Date().toISOString().slice(0, 10)} value={f.delivery_date} onChange={set("delivery_date")} className={`${input} mt-1`} data-testid="offrir-delivery-date" />
            </label>
          </div>
        )}
      </fieldset>
      <p className="text-sm text-navy/65">Cette demande ne déclenche aucun paiement. Le code cadeau est attribué après validation du paiement. Aucun prix n’apparaît sur la carte remise au bénéficiaire.</p>
      <button type="submit" disabled={loading} data-testid="offrir-submit"
        className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full shadow-warm transition-colors disabled:opacity-70 min-h-[56px]">
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Gift className="w-5 h-5" />}
        {loading ? "Redirection vers le paiement…" : "Continuer vers le paiement"}
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
  const [offer, setOffer] = useState(params.get("offre") || "");
  useEffect(() => {
    if (!data) return;
    if (data.promo.closed) {
      setOffer("noel");
    } else if (!data.offers.some((item) => item.id === offer)) {
      setOffer(data.promo.active ? "noel" : "famille");
    }
  }, [data, offer]);
  const selected = data?.offers.find((o) => o.id === offer);
  const isChristmas = data?.promo?.active && offer === "noel";
  return (
    <div className="min-h-screen bg-bgmain">
      <Navbar />
      <Hero promo={data?.promo} selected={selected} />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-14 grid gap-10 [&>*]:min-w-0" data-testid="offrir-page">
        <section>
          <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-5">1. Choisissez le cadeau</h2>
          <OfferPicker offers={data?.offers} value={offer} onChange={setOffer} />
        </section>
        {data?.promo?.closed && <p className="border-l-4 border-bordeaux bg-white px-5 py-4 font-bold text-bordeaux" role="status">L’offre de Noël est terminée</p>}
        {offer === "noel" && isChristmas && (
          <section>
            <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-2">Une année de jeux. De beaux souvenirs.</h2>
            <p className="text-navy/70 mb-4">Quiz illimités, progression et historique, Livre de Vie en PDF. 1 accès personnel complet, valable un an à partir de l’activation. Livre papier non inclus.</p>
          </section>
        )}
        {offer === "famille" && !isChristmas && (
          <section>
            <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-2">Qui a accès à quoi ?</h2>
            <p className="text-navy/70 mb-4">1 abonnement complet pour le bénéficiaire + 4 accès aux jeux en famille inclus pendant un an.</p>
            <FamilyAccessTable />
          </section>
        )}
        {!(data?.promo?.closed && offer === "noel") && selected && (
          <section className="bg-white rounded-3xl border-2 border-cream-dark p-6 sm:p-8 shadow-warm">
            <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-5">2. Personnalisez la carte</h2>
            <GiftForm offer={offer} isChristmas={isChristmas} />
          </section>
        )}
      </main>
      <Footer />
    </div>
  );
}
