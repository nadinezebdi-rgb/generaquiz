import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Gift, Save, Plus, Download, Ban, CalendarRange } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api, BACKEND_URL, formatError } from "@/lib/api";
import { fmt } from "@/config/pricing";

const input = "w-full rounded-xl border-2 border-cream-dark px-3 py-2 text-navy focus:border-navy outline-none";
const err = (e) => toast.error(formatError(e.response?.data?.detail));
const STATUS = { active: "À activer", redeemed: "Activé", cancelled: "Annulé" };

function PromoCard() {
  const [p, setP] = useState(null);
  useEffect(() => { api.get("/admin/site-settings/gift-promo").then((r) => setP(r.data)).catch(err); }, []);
  if (!p) return null;
  const set = (k, num) => (e) => setP({ ...p, [k]: e.target.type === "checkbox" ? e.target.checked : num ? Number(e.target.value) : e.target.value });
  const save = async () => {
    try {
      const { active_now: _a, ...body } = p;
      const { data } = await api.put("/admin/site-settings/gift-promo", body);
      setP(data); toast.success(data.active_now ? "Promo enregistrée — visible maintenant" : "Promo enregistrée — hors période");
    } catch (e) { err(e); }
  };
  return (
    <section className="bg-white rounded-2xl border-2 border-cream-dark p-5" data-testid="admin-gift-promo">
      <h2 className="font-display text-xl font-extrabold text-navy mb-1 flex items-center gap-2"><CalendarRange className="w-5 h-5" /> Promo saisonnière (carte Famille)</h2>
      <p className="text-sm text-navy/70 mb-4">Statut : <strong data-testid="admin-gift-promo-status">{p.active_now ? "visible en ce moment" : "non visible"}</strong>. Hors période, la carte Famille est vendue au prix normal.</p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
        <label className="text-sm font-bold text-navy">Titre<input value={p.title} onChange={set("title")} className={`${input} mt-1`} data-testid="promo-title" /></label>
        <label className="text-sm font-bold text-navy">Début<input type="date" value={p.starts_on} onChange={set("starts_on")} className={`${input} mt-1`} data-testid="promo-start" /></label>
        <label className="text-sm font-bold text-navy">Fin (incluse)<input type="date" value={p.ends_on} onChange={set("ends_on")} className={`${input} mt-1`} data-testid="promo-end" /></label>
        <label className="text-sm font-bold text-navy">Prix normal (€)<input type="number" step="0.01" min="1" value={p.famille_regular_price} onChange={set("famille_regular_price", true)} className={`${input} mt-1`} data-testid="promo-regular" /></label>
        <label className="text-sm font-bold text-navy">Prix promo (€)<input type="number" step="0.01" min="1" value={p.famille_promo_price} onChange={set("famille_promo_price", true)} className={`${input} mt-1`} data-testid="promo-price" /></label>
        <label className="text-sm font-bold text-navy flex items-center gap-2 mt-6"><input type="checkbox" checked={p.enabled} onChange={set("enabled")} className="w-5 h-5" data-testid="promo-enabled" /> Promo activée</label>
      </div>
      <button type="button" onClick={save} data-testid="promo-save" className="inline-flex items-center gap-2 bg-navy text-white font-bold px-5 py-2 rounded-full hover:bg-terracotta transition-colors"><Save className="w-4 h-4" /> Enregistrer</button>
    </section>
  );
}

function ManualGift({ onCreated }) {
  const [f, setF] = useState({ offer: "famille", recipient_name: "", buyer_name: "", message: "", theme: "classic" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    try { const { data } = await api.post("/admin/gifts", f); toast.success(`Code ${data.code} créé`); onCreated(); }
    catch (e2) { err(e2); }
  };
  return (
    <form onSubmit={submit} className="bg-white rounded-2xl border-2 border-cream-dark p-5 grid sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end" data-testid="admin-gift-create">
      <label className="text-sm font-bold text-navy">Offre<select value={f.offer} onChange={set("offer")} className={`${input} mt-1`} data-testid="admin-gift-offer"><option value="famille">Famille 1 an</option><option value="solo">Solo 1 an</option></select></label>
      <label className="text-sm font-bold text-navy">Pour<input maxLength={40} value={f.recipient_name} onChange={set("recipient_name")} className={`${input} mt-1`} data-testid="admin-gift-recipient" /></label>
      <label className="text-sm font-bold text-navy">De la part de<input maxLength={40} value={f.buyer_name} onChange={set("buyer_name")} className={`${input} mt-1`} data-testid="admin-gift-buyer" /></label>
      <label className="text-sm font-bold text-navy">Visuel<select value={f.theme} onChange={set("theme")} className={`${input} mt-1`} data-testid="admin-gift-theme"><option value="classic">Classique</option><option value="noel">Noël</option></select></label>
      <button type="submit" data-testid="admin-gift-submit" className="inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-5 py-2.5 rounded-full hover:bg-terracotta-dark transition-colors"><Plus className="w-4 h-4" /> Créer un code offert</button>
    </form>
  );
}

function GiftRow({ g, onCancel }) {
  return (
    <tr className="border-t border-cream-dark" data-testid={`admin-gift-row-${g.code}`}>
      <td className="px-3 py-2 font-mono font-bold text-navy">{g.code}</td>
      <td className="px-3 py-2">{g.offer_label}</td>
      <td className="px-3 py-2">{g.recipient_name || "—"}<div className="text-xs text-navy/60">{g.buyer_email || (g.source === "admin" ? "offert (admin)" : "")}</div></td>
      <td className="px-3 py-2">{g.amount ? fmt(g.amount) : "0 €"}</td>
      <td className="px-3 py-2">{STATUS[g.status]}{g.redeemed_by_email && <div className="text-xs text-navy/60">{g.redeemed_by_email}</div>}</td>
      <td className="px-3 py-2 whitespace-nowrap">
        <a href={`${BACKEND_URL}${g.pdf_url}`} target="_blank" rel="noreferrer" aria-label="Télécharger la carte" className="inline-flex p-2 text-navy hover:text-terracotta" data-testid={`admin-gift-pdf-${g.code}`}><Download className="w-4 h-4" /></a>
        {g.status === "active" && <button type="button" onClick={() => onCancel(g)} aria-label="Annuler le code" className="p-2 text-bordeaux" data-testid={`admin-gift-cancel-${g.code}`}><Ban className="w-4 h-4" /></button>}
      </td>
    </tr>
  );
}

export default function AdminGifts() {
  const [data, setData] = useState(null);
  const load = useCallback(() => api.get("/admin/gifts").then((r) => setData(r.data)).catch(err), []);
  useEffect(() => { load(); }, [load]);
  const cancel = async (g) => {
    if (!window.confirm(`Annuler le code ${g.code} ?`)) return;
    try { await api.patch(`/admin/gifts/${g.code}/cancel`); load(); } catch (e) { err(e); }
  };
  const s = data?.stats;
  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 grid gap-6" data-testid="admin-gifts-page">
        <h1 className="font-display text-3xl font-extrabold text-navy flex items-center gap-2"><Gift className="w-7 h-7 text-terracotta" /> Cartes cadeau</h1>
        {s && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="admin-gift-stats">
            {[["Vendues", s.sold], ["Chiffre d'affaires", fmt(s.revenue)], ["Activées", s.redeemed], ["En attente", s.pending]].map(([l, v]) => (
              <div key={l} className="bg-white rounded-2xl border-2 border-cream-dark p-4"><div className="text-sm text-navy/60">{l}</div><div className="font-display text-2xl font-extrabold text-navy">{v}</div></div>
            ))}
          </div>
        )}
        <PromoCard />
        <ManualGift onCreated={load} />
        <div className="bg-white rounded-2xl border-2 border-cream-dark overflow-x-auto">
          <table className="w-full text-sm text-left min-w-[760px]" data-testid="admin-gift-table">
            <thead className="bg-cream text-navy/70 text-xs uppercase"><tr>{["Code", "Offre", "Destinataire", "Montant", "Statut", ""].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
            <tbody>{data?.gifts.map((g) => <GiftRow key={g.code} g={g} onCancel={cancel} />)}</tbody>
          </table>
          {data && data.gifts.length === 0 && <p className="p-4 text-navy/60">Aucune carte cadeau pour l&apos;instant.</p>}
        </div>
      </main>
    </div>
  );
}
