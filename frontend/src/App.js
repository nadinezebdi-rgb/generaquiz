import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
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
 *  est redirigé vers son tableau de bord. Ne remplace PAS la protection
 *  serveur : tous les endpoints /api/admin/* exigent aussi role=admin. */
function AdminRoute({ children }) {
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
  if (user.role !== "admin") {
    return <Navigate to="/app/dashboard" replace />;
  }
  return children;
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
