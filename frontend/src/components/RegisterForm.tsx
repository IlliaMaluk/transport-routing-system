// frontend/src/components/RegisterForm.tsx
import React, { FormEvent, useState } from "react";
import { useAuth } from "../context/AuthContext";

interface RegisterFormProps {
  onSuccess?: () => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess }) => {
  const { register } = useAuth();
  const [email, setEmail] = useState<string>("");
  const [fullName, setFullName] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(email, password, fullName);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.message || "Помилка реєстрації");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-sm w-full bg-white shadow-md rounded-xl p-4 border border-gray-200"
    >
      <h2 className="text-lg font-semibold mb-3 text-gray-800">Реєстрація</h2>

      <label className="block mb-2 text-sm font-medium text-gray-700">
        Email
        <input
          type="email"
          className="mt-1 block w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </label>

      <label className="block mb-2 text-sm font-medium text-gray-700">
        Ім'я / ПІБ (необов'язково)
        <input
          type="text"
          className="mt-1 block w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Іван Іваненко"
        />
      </label>

      <label className="block mb-3 text-sm font-medium text-gray-700">
        Пароль
        <input
          type="password"
          className="mt-1 block w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={4}
        />
      </label>

      {error && (
        <div className="mb-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2 rounded-lg text-sm font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-60"
      >
        {loading ? "Реєстрація..." : "Зареєструватися"}
      </button>
    </form>
  );
};

export default RegisterForm;
