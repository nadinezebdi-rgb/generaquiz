import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export const PENDING_GIFT_KEY = "gq_pending_gift_code";

export function useGiftOffers() {
  const [data, setData] = useState(null);
  useEffect(() => {
    api.get("/gifts/offers").then((r) => setData(r.data)).catch(() => setData(null));
  }, []);
  return data;
}

export function formatCodeInput(raw) {
  const s = (raw || "").toUpperCase().replace(/[^A-Z0-9]/g, "").replace(/^GQ/, "").slice(0, 8);
  return s.length > 4 ? `GQ-${s.slice(0, 4)}-${s.slice(4)}` : s ? `GQ-${s}` : "";
}

export const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
