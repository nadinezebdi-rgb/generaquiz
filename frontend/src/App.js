import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import "@/App.css";

import { AuthProvider, useAuth } from "@/contexts/AuthContext";
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
import AdminUsers from "@/pages/AdminUsers";
import Account from "@/pages/Account";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import DailyQuiz from "@/pages/DailyQuiz";
import CGU from "@/pages/legal/CGU";
import CGV from "@/pages/legal/CGV";
import Confidentialite from "@/pages/legal/Confidentialite";

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

export default function App() {
  return (
    <AuthProvider>
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
          <Route
            path="/app/pricing"
            element={
              <ProtectedRoute>
                <Pricing />
              </ProtectedRoute>
            }
          />
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
            path="/app/admin/promo"
            element={
              <ProtectedRoute>
                <AdminPromo />
              </ProtectedRoute>
            }
          />
        <Route
          path="/app/admin/users"
          element={
            <ProtectedRoute>
              <AdminUsers />
            </ProtectedRoute>
          }
        />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
