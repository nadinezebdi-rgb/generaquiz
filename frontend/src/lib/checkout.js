import { api, formatError } from "@/lib/api";

/**
 * Démarre un checkout Stripe pour un package_id backend.
 *
 * - Si l'utilisateur n'est pas connecté (401), on redirige vers /register en
 *   conservant le package à reprendre après connexion.
 * - Sinon on récupère `url` renvoyé par le backend et on redirige.
 */
export async function startCheckout(packageId, { onError } = {}) {
  if (!packageId) {
    onError?.("Ce forfait n'est pas encore disponible.");
    return;
  }
  try {
    const { data } = await api.post("/checkout/session", {
      package_id: packageId,
      origin_url: window.location.origin,
    });
    if (data?.url) {
      window.location.href = data.url;
      return;
    }
    onError?.("Impossible d'ouvrir le paiement. Veuillez réessayer.");
  } catch (err) {
    const status = err?.response?.status;
    if (status === 401 || status === 403) {
      // Pas connecté : on garde le forfait choisi pour le reprendre.
      try { sessionStorage.setItem("pending_checkout_package", packageId); } catch { /* storage bloqué */ }
      window.location.href = `/register?next=/app/pricing&pkg=${encodeURIComponent(packageId)}`;
      return;
    }
    onError?.(formatError(err?.response?.data?.detail));
  }
}
