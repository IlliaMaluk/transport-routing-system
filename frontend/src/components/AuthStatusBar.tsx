// frontend/src/components/AuthStatusBar.tsx
import React from "react";
import { useAuth } from "../context/AuthContext";

const AuthStatusBar: React.FC = () => {
  const { user, logout, loading } = useAuth();

  if (loading) {
    return (
      <div className="w-full bg-gray-100 border-b border-gray-200 px-4 py-2 text-sm text-gray-600">
        Перевірка авторизації...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="w-full bg-yellow-50 border-b border-yellow-200 px-4 py-2 text-sm text-yellow-800 flex justify-between items-center">
        <span>Ви не авторизовані. Деякі функції (імпорт, сценарії) недоступні.</span>
        <span className="text-xs text-yellow-700">
          Увійдіть як admin / operator для керування мережею.
        </span>
      </div>
    );
  }

  return (
    <div className="w-full bg-green-50 border-b border-green-200 px-4 py-2 text-sm text-green-800 flex justify-between items-center">
      <span>
        Увійшли як <strong>{user.full_name || user.email}</strong> (
        <span className="uppercase font-semibold">{user.role}</span>)
      </span>
      <button
        onClick={logout}
        className="text-xs px-3 py-1 border border-green-400 rounded-full hover:bg-green-100"
      >
        Вийти
      </button>
    </div>
  );
};

export default AuthStatusBar;
