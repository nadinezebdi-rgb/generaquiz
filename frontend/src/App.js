import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import "@/App.css";

import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { SeniorModeProvider } from "@/contexts/SeniorModeContext";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import QuizPlayer from "@/pages/QuizPlayer";
import Pricing from "@/pages/Pricing";
import Success from "@/pages/Success";
import Challenges from "@/pages/Challenges";
import ChallengeNew from "@/pages/ChallengeNew";
import ChallengeDetail from "@/pages/ChallengeDetail";
import ChallengePlay from "@/pages/ChallengePlay";
import AdminPromo from "@/pages/AdminPromo";
import Account from "@/pages/Account";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import DailyQuiz from "@/pages/DailyQuiz";
import CGU from "@/pages/legal/CGU";
import CGV from "@/pages/legal/CGV";
import Confidentialite from "@/pages/legal/Confidentialite";
import AdminReports from "@/pages/AdminReports";
import AdminAnalytics from "@/pages/AdminAnalytics";
import AdminHome from "@/pages/AdminHome";
import AdminQA from "@/pages/AdminQA";
import AdminUsers from "@/pages/AdminUsers";
import AdminAudit from "@/pages/AdminAudit";
import Pourquoi from "@/pages/Pourquoi";
import EarnCredits from "@/pages/EarnCredits";
import CoopChallengeCreate from "@/pages/CoopChallengeCreate";
import CoopChallengePlay from "@/pages/CoopChallengePlay";
import Leagues from "@/pages/Leagues";
import Progression from "@/pages/Progression";
import Ehpad from "@/pages/Ehpad";
import Atelier from "@/pages/Atelier";
import AtelierEntries from "@/pages/AtelierEntries";
import MonLivre from "@/pages/MonLivre";
import LivreCoop from "@/pages/LivreCoop";
import VoyagesShowcase from "@/pages/VoyagesShowcase";
import EhpadDashboard from "@/pages/EhpadDashboard";
import { EhpadNewSession, EhpadSessionView } from "@/pages/EhpadSession";
import Charades from "@/pages/Charades";
import MotsMeles from "@/pages/MotsMeles";
import MotsFleches from "@/pages/MotsFleches";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading || user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center paper-bg">
        <div className="text-navy text-xl font-medium">Chargement...</div>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return children;
}

/** AdminRoute — guard rôle "admin". Un utilisateur connecté mais non-admin
 *  voit un écran "Accès refusé" explicite (plus de redirection silencieuse,
 *  pour faciliter le diagnostic). Avec `requireSuperadmin`, seul le rôle
 *  "superadmin" passe. Ne remplace PAS la protection serveur : tous
 *  les endpoints /api/admin/* exigent aussi role=admin (ou superadmin). */
function AdminRoute({ children, requireSuperadmin = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading || user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center paper-bg">
        <div className="text-navy text-xl font-medium">Chargement...</div>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  const isSuper = user.role === "superadmin";
  const isAdmin = isSuper || user.role === "admin";
  if (requireSuperadmin ? !isSuper : !isAdmin) {
    return <AdminAccessDenied role={user.role} requireSuperadmin={requireSuperadmin} />;
  }
  return children;
}

function AdminAccessDenied({ role, requireSuperadmin = false }) {
  const requiredLabel = requireSuperadmin ? "super-administrateur" : "administrateur";
  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-4" data-testid="admin-access-denied">
      <div className="max-w-md w-full bg-white border-2 border-cream-dark rounded-3xl p-8 text-center shadow-warm">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-bordeaux/10 text-bordeaux flex items-center justify-center text-3xl">
          🔒
        </div>
        <h1 className="font-display text-2xl font-extrabold text-navy mb-2">
          Accès refusé
        </h1>
        <p className="text-navy/70 mb-1">
          Droits <strong>{requiredLabel}</strong> requis pour accéder à cette page.
        </p>
        <p className="text-xs text-navy/50 mb-6">
          Votre rôle actuel : <code className="bg-cream px-2 py-0.5 rounded font-mono">{role || "user"}</code>
        </p>
        <div className="flex flex-col gap-2">
          <Link
            to="/app/dashboard"
            data-testid="admin-denied-back-dashboard"
            className="inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full hover:bg-terracotta-dark transition"
          >
            Retour au tableau de bord
          </Link>
          <Link
            to="/"
            data-testid="admin-denied-back-home"
            className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy text-navy font-bold px-5 py-3 rounded-full hover:bg-navy hover:text-cream transition"
          >
            Retour à l&apos;accueil
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <SeniorModeProvider>
        <BrowserRouter>
        <Toaster richColors position="top-right" />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/quiz-du-jour" element={<DailyQuiz />} />
          <Route path="/cgu" element={<CGU />} />
          <Route path="/cgv" element={<CGV />} />
          <Route path="/confidentialite" element={<Confidentialite />} />
          <Route path="/ehpad" element={<Ehpad />} />
          <Route path="/voyages-france" element={<VoyagesShowcase />} />
          <Route path="/livre/coop/:code" element={<LivreCoop />} />
          <Route
            path="/app/atelier"
            element={
              <ProtectedRoute>
                <Atelier />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/atelier/mes-souvenirs"
            element={
              <ProtectedRoute>
                <AtelierEntries />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/livre"
            element={
              <ProtectedRoute>
                <MonLivre />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/ehpad"
            element={
              <ProtectedRoute>
                <EhpadDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/ehpad/nouvelle-seance"
            element={
              <ProtectedRoute>
                <EhpadNewSession />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/ehpad/seance/:sessionId"
            element={
              <ProtectedRoute>
                <EhpadSessionView />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/charades"
            element={
              <ProtectedRoute>
                <Charades />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/mots-meles"
            element={
              <ProtectedRoute>
                <MotsMeles />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/mots-fleches"
            element={
              <ProtectedRoute>
                <MotsFleches />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/account"
            element={
              <ProtectedRoute>
                <Account />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/quiz/:categoryId"
            element={
              <ProtectedRoute>
                <QuizPlayer />
              </ProtectedRoute>
            }
          />
          <Route path="/app/pricing" element={<Pricing />} />
          <Route
            path="/app/success"
            element={
              <ProtectedRoute>
                <Success />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/challenges"
            element={
              <ProtectedRoute>
                <Challenges />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/challenges/new"
            element={
              <ProtectedRoute>
                <ChallengeNew />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/challenges/:token"
            element={
              <ProtectedRoute>
                <ChallengeDetail />
              </ProtectedRoute>
            }
          />
          <Route path="/defi/:token" element={<ChallengePlay />} />
          <Route
            path="/app/admin"
            element={
              <AdminRoute>
                <AdminHome />
              </AdminRoute>
            }
          />
          <Route
            path="/app/admin/promo"
            element={
              <AdminRoute>
                <AdminPromo />
              </AdminRoute>
            }
          />
          <Route
            path="/app/admin/reports"
            element={
              <AdminRoute>
                <AdminReports />
              </AdminRoute>
            }
          />
          <Route
            path="/app/admin/analytics"
            element={
              <AdminRoute>
                <AdminAnalytics />
              </AdminRoute>
            }
          />
          <Route
            path="/app/admin/qa"
            element={
              <AdminRoute>
                <AdminQA />
              </AdminRoute>
            }
          />
          <Route
            path="/app/admin/users"
            element={
              <AdminRoute>
                <AdminUsers />
              </AdminRoute>
            }
          />
          <Route
            path="/app/admin/audit"
            element={
              <AdminRoute requireSuperadmin>
                <AdminAudit />
              </AdminRoute>
            }
          />
          <Route path="/pourquoi" element={<Pourquoi />} />
          <Route
            path="/app/earn-credits"
            element={
              <ProtectedRoute>
                <EarnCredits />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/coop/new"
            element={
              <ProtectedRoute>
                <CoopChallengeCreate />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/coop/:token"
            element={
              <ProtectedRoute>
                <CoopChallengePlay />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/leagues"
            element={
              <ProtectedRoute>
                <Leagues />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/progression"
            element={
              <ProtectedRoute>
                <Progression />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      </SeniorModeProvider>
    </AuthProvider>
  );
}
