import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Users, Loader2 } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function FamilleRejoindre() {
  const { token } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const here = `/famille/rejoindre/${token}`;

  useEffect(() => {
    api.get(`/famille/invitation/${token}`).then((r) => setInfo(r.data)).catch((e) => setError(formatError(e.response?.data?.detail)));
  }, [token]);

  const accept = async () => {
    setLoading(true);
    try { await api.post(`/famille/invitation/${token}/accept`); toast.success("Bienvenue dans la famille !"); navigate("/app/famille"); }
    catch (e) { toast.error(formatError(e.response?.data?.detail)); setLoading(false); }
  };

  return (
    <div className="min-h-screen paper-bg">
      <Navbar />
      <main className="max-w-xl mx-auto px-4 py-16" data-testid="famille-join-page">
        {error && <p className="bg-white rounded-3xl border-2 border-cream-dark p-8 text-bordeaux font-semibold text-center" data-testid="famille-join-error">{error}</p>}
        {info && (
          <div className="bg-white rounded-3xl border-4 border-mustard p-8 text-center shadow-warm">
            <Users className="w-14 h-14 text-terracotta mx-auto mb-4" />
            <h1 className="font-display text-3xl font-extrabold text-navy mb-2" data-testid="famille-join-title">{info.owner_name} vous invite à jouer en famille</h1>
            <p className="text-navy/75 mb-6">Quiz et défis du groupe familial, classement partagé : c&apos;est gratuit pour vous toute l&apos;année.</p>
            {user ? (
              <button type="button" onClick={accept} disabled={loading} data-testid="famille-join-accept"
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full transition-colors disabled:opacity-70">
                {loading && <Loader2 className="w-5 h-5 animate-spin" />} Rejoindre la famille
              </button>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                <Link to={`/register?next=${encodeURIComponent(here)}`} data-testid="famille-join-register" className="bg-terracotta text-white font-bold px-6 py-4 rounded-full hover:bg-terracotta-dark transition-colors">Créer mon compte</Link>
                <Link to="/login" state={{ from: here }} data-testid="famille-join-login" className="bg-white border-2 border-navy text-navy font-bold px-6 py-4 rounded-full hover:bg-navy hover:text-cream transition-colors">J&apos;ai déjà un compte</Link>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
