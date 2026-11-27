import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Lock } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { api, formatError } from "@/lib/api";
import { startCheckout } from "@/lib/checkout";
import { offerPresentation, annualDiscountBadge, fmt } from "@/config/pricing";

export function PeriodToggle({ period, setPeriod, promo, testPrefix = "pricing" }) {
  const btn = (value) => `inline-flex items-center gap-1.5 px-3 sm:px-5 py-2.5 rounded-full font-bold text-sm whitespace-nowrap transition-colors ${
    period === value ? "bg-navy text-cream" : "text-navy hover:bg-cream-dark"}`;
  return (
    <div className="flex justify-center mb-8">
      <div className="inline-flex flex-nowrap justify-center gap-1 bg-white border-2 border-cream-dark rounded-full p-1" role="tablist" data-testid={`${testPrefix}-toggle`}>
        <button type="button" role="tab" aria-selected={period === "monthly"} onClick={() => setPeriod("monthly")}
          className={btn("monthly")} data-testid={`${testPrefix}-toggle-monthly`}>Mensuel</button>
        <button type="button" role="tab" aria-selected={period === "yearly"} onClick={() => setPeriod("yearly")}
          className={btn("yearly")} data-testid={`${testPrefix}-toggle-yearly`}>
          Annuel
          <span className="bg-terracotta text-white text-[10px] uppercase tracking-wide px-1.5 sm:px-2 py-0.5 rounded-full whitespace-nowrap">
            {promo ? "🎄 Super promo Noël" : "2 mois d'économie"}
          </span>
        </button>
      </div>
    </div>
  );
}

export function PromoHeader({ promo, testPrefix = "pricing" }) {
  return (
    <>
      <p className="text-lg text-navy/70">Sans engagement · Résiliable à tout moment · Support en français</p>
      <p className={`mt-3 font-bold ${promo ? "text-bordeaux text-base sm:text-lg" : "text-sm text-terracotta"}`} data-testid={`${testPrefix}-promo-banner`}>
        {annualDiscountBadge(promo)}
      </p>
    </>
  );
}

export function PlanPrice({ plan, period, promo }) {
  const pres = offerPresentation(plan, period, promo);
  return (
    <div className="mb-4 sm:min-h-[118px]" data-testid={`plan-price-block-${plan.id}`}>
      {pres.pill && (
        <span className="inline-block bg-bordeaux text-cream text-xs font-extrabold uppercase tracking-wider px-3 py-1 rounded-full mb-2" data-testid={`plan-pill-${plan.id}`}>
          {pres.pill}
        </span>
      )}
      <p className="font-display text-3xl sm:text-4xl font-extrabold text-bordeaux leading-tight" data-testid={`plan-price-${plan.id}`}>
        {pres.main}{pres.unit && <span className="font-display text-xl font-extrabold">{pres.unit}</span>}
      </p>
      {pres.savings && <p className="text-sm font-bold text-navy mt-1.5" data-testid={`plan-savings-${plan.id}`}>{pres.savings}</p>}
      {pres.renewal && <p className="text-sm text-navy mt-1" data-testid={`plan-renewal-${plan.id}`}>{pres.renewal}</p>}
    </div>
  );
}

export function CheckoutRecap({ packageId, onClose }) {
  const [info, setInfo] = useState(null);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setInfo(null); setAccepted(false);
    if (!packageId) return;
    api.get(`/pricing/summary/${packageId}`).then((r) => setInfo(r.data))
      .catch((e) => { toast.error(formatError(e.response?.data?.detail)); onClose(); });
  }, [packageId, onClose]);

  const pay = async () => {
    setBusy(true);
    await startCheckout(packageId, { acceptTerms: true, onError: (m) => { toast.error(m || "Impossible d'ouvrir le paiement."); setBusy(false); } });
  };

  const amount = info ? fmt(info.amount, { integer: true }) : "";
  return (
    <Dialog open={Boolean(packageId)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg bg-cream border-2 border-cream-dark rounded-3xl" data-testid="checkout-recap">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl font-extrabold text-navy">Récapitulatif avant paiement</DialogTitle>
          <DialogDescription className="sr-only">Vérifiez votre offre avant de saisir votre carte.</DialogDescription>
        </DialogHeader>
        {!info ? <Loader2 className="w-6 h-6 animate-spin text-navy mx-auto my-6" /> : (
          <div className="space-y-5">
            <p className="text-navy text-lg leading-relaxed bg-white border-2 border-cream-dark rounded-2xl p-4" data-testid="checkout-recap-text">{info.summary}</p>
            <label className="flex items-start gap-3 text-navy cursor-pointer" data-testid="checkout-recap-terms">
              <Checkbox checked={accepted} onCheckedChange={(v) => setAccepted(v === true)} className="mt-1 h-5 w-5 border-2 border-navy data-[state=checked]:bg-navy" data-testid="checkout-recap-checkbox" />
              <span>
                J&apos;accepte les <Link to="/cgv" target="_blank" className="underline font-semibold">conditions de vente</Link>
                {info.period === "yearly" ? ` et le renouvellement automatique à ${fmt(info.renew_amount, { integer: true })}/an, résiliable à tout moment.` : " et le prélèvement mensuel, résiliable à tout moment."}
              </span>
            </label>
            <button type="button" disabled={!accepted || busy} onClick={pay}
              className="w-full inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold text-lg px-6 py-3.5 rounded-full hover:bg-terracotta-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[56px]"
              data-testid="checkout-recap-pay-btn">
              {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Lock className="w-5 h-5" />} Payer {amount}
            </button>
            <p className="text-sm text-navy text-center">Paiement sécurisé par Stripe. Aucune option payante n&apos;est ajoutée.</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
