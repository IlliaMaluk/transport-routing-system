// frontend/src/pages/AuthPage.tsx
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import LoginForm from "../components/LoginForm";
import RegisterForm from "../components/RegisterForm";
import { useAuth } from "../context/AuthContext";

const AuthPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleSuccess = () => {
    navigate("/");
  };

  return (
    <div className="app-root" style={{ minHeight: "100vh" }}>
      <header className="app-header">
        <div className="flex justify-between items-center w-full">
          <div>
            <h1>Авторизація та реєстрація</h1>
            <p className="subtitle">
              Створіть акаунт оператора або увійдіть зі своїми даними
            </p>
          </div>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 border border-gray-300 text-sm font-medium hover:bg-gray-200"
          >
            ⬅ Назад до головної
          </Link>
        </div>
      </header>

      <main className="app-main" style={{ paddingTop: "1rem" }}>
        {user ? (
          <div className="w-full bg-green-50 border border-green-200 text-green-800 rounded-xl p-4">
            Ви вже увійшли як <strong>{user.full_name || user.email}</strong>.
            <br />
            Можете повернутися на головну, щоб працювати з маршрутами.
          </div>
        ) : (
          <div className="flex flex-col md:flex-row gap-4 w-full">
            <div className="flex-1">
              <LoginForm onSuccess={handleSuccess} />
            </div>
            <div className="flex-1">
              <RegisterForm onSuccess={handleSuccess} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default AuthPage;
