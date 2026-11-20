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
  const up = (raw || "").toUpperCase();
  let s = up.replace(/[^A-Z0-9]/g, "");
  if (s === "G" || s === "GQ") return up.replace(/[^A-Z0-9-]/g, "");
  if (s.startsWith("GQ")) s = s.slice(2);
  s = s.slice(0, 32);
  const groups = s.match(/.{1,8}/g) || [];
  return groups.length ? `GQ-${groups.join("-")}` : "";
}

export const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
