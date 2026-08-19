import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, Shield, BarChart3, Tag, Flag, LayoutDashboard, ClipboardCheck } from "lucide-react";

/**
 * AdminDropdown — collapsible "Admin" trigger visible only to role=admin users.
 * Bundles Home / Analytics / Promos / Signalements / Qualité IA so the desktop nav stays clean.
 */

const ADMIN_LINKS = [
  { to: "/app/admin",           icon: LayoutDashboard, label: "Administration", desc: "Tableau de bord admin",         testid: "nav-admin-home" },
  { to: "/app/admin/analytics", icon: BarChart3,       label: "Analytics",      desc: "MAU, MRR, top catégories",      testid: "nav-admin-analytics" },
  { to: "/app/admin/promo",     icon: Tag,             label: "Promos",         desc: "Codes promo Stripe",            testid: "nav-admin-promo" },
  { to: "/app/admin/reports",   icon: Flag,            label: "Signalements",   desc: "Questions signalées à modérer", testid: "nav-admin-reports" },
  { to: "/app/admin/qa",        icon: ClipboardCheck,  label: "Qualité IA",     desc: "Questions vérifiées par Opus",  testid: "nav-admin-qa" },
];

export default function AdminDropdown() {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false);
    };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        data-testid="nav-admin-trigger"
        className={`inline-flex items-center gap-1 whitespace-nowrap px-3 py-2 text-base font-semibold transition ${
          open ? "text-bordeaux" : "text-bordeaux/80 hover:text-bordeaux"
        }`}
      >
        <Shield className="w-4 h-4" />
        Admin
        <ChevronDown className={`w-4 h-4 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          role="menu"
          data-testid="nav-admin-menu"
          className="absolute right-0 top-full mt-2 w-72 bg-white border-2 border-cream-dark rounded-2xl shadow-warm p-2 z-50"
        >
          {ADMIN_LINKS.map((it) => {
            const Icon = it.icon;
            return (
              <Link
                key={it.to}
                to={it.to}
                role="menuitem"
                data-testid={it.testid}
                onClick={() => setOpen(false)}
                className="flex items-start gap-3 p-3 rounded-xl hover:bg-cream transition"
              >
                <div className="w-9 h-9 rounded-lg bg-bordeaux/15 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-bordeaux" />
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-navy leading-tight">{it.label}</div>
                  <div className="text-xs text-navy/60">{it.desc}</div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
