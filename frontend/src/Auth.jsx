import { useState, useEffect } from 'react';
import { Eye } from 'lucide-react';
import { auth } from './api';

function Auth({ onLogin, onTryDemo, onViewExample }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [rememberCredentials, setRememberCredentials] = useState(false);

  // Inline validation state
  const [emailTouched, setEmailTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);

  // Validation functions
  const validateEmail = (value) => {
    if (!value) return 'Email обязателен';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Некорректный формат email';
    return null;
  };

  const validatePassword = (value) => {
    if (!value) return 'Пароль обязателен';
    if (value.length < 8) return 'Минимум 8 символов';
    return null;
  };

  const emailError = emailTouched ? validateEmail(email) : null;
  const passwordError = passwordTouched ? validatePassword(password) : null;

  // Инициализируем состояние "запоминания" из пользовательской настройки
  useEffect(() => {
    const remember = localStorage.getItem('remember_credentials') === 'true';
    setRememberCredentials(remember);

    if (remember) {
      const savedEmail = localStorage.getItem('remembered_login') || '';
      const savedPassword = localStorage.getItem('remembered_password') || '';

      if (savedEmail) {
        setEmail(savedEmail);
      }
      if (savedPassword) {
        setPassword(savedPassword);
      }
    }
  }, []);

  // Сохраняем логин и пароль в localStorage (для удобного автозаполнения)
  const saveCredentials = (shouldRemember, currentEmail, currentPassword) => {
    if (shouldRemember) {
      localStorage.setItem('remember_credentials', 'true');
      localStorage.setItem('remembered_login', currentEmail);
      localStorage.setItem('remembered_password', currentPassword);
    } else {
      localStorage.removeItem('remember_credentials');
      localStorage.removeItem('remembered_login');
      localStorage.removeItem('remembered_password');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isLogin) {
        await auth.login(email, password);
      } else {
        await auth.register(email, password, fullName);
        // После регистрации автоматически логинимся
        await auth.login(email, password);
      }
      // Сохраняем или очищаем сохраненные логин и пароль в зависимости от выбора пользователя
      saveCredentials(rememberCredentials, email, password);
      // Сессия устанавливается через httpOnly cookies внутри auth.login
      onLogin();
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка аутентификации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full">
        <h1 className="text-3xl font-bold mb-2 text-gray-800">AI User Story Mapper</h1>
        <p className="text-gray-600 mb-6">
          {isLogin ? 'Войдите в свой аккаунт' : 'Создайте новый аккаунт'}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Имя (опционально)
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="Ваше имя"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => setEmailTouched(true)}
              required
              autoComplete="email"
              className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition ${
                emailError
                  ? 'border-red-400 bg-red-50'
                  : emailTouched && !emailError
                  ? 'border-green-400 bg-green-50'
                  : 'border-gray-300'
              }`}
              placeholder="your@email.com"
            />
            {emailError && (
              <p className="text-xs text-red-600 mt-1">{emailError}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Пароль
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => setPasswordTouched(true)}
              required
              minLength={8}
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition ${
                passwordError
                  ? 'border-red-400 bg-red-50'
                  : passwordTouched && !passwordError
                  ? 'border-green-400 bg-green-50'
                  : 'border-gray-300'
              }`}
              placeholder="Минимум 8 символов"
            />
            {isLogin && passwordError && (
              <p className="text-xs text-red-600 mt-1">{passwordError}</p>
            )}
            {!isLogin && password && (
              <div className="mt-2 text-xs space-y-1">
                <p className={password.length >= 8 ? "text-green-600" : "text-gray-400"}>
                  ✓ Минимум 8 символов
                </p>
                <p className={/[A-Z]/.test(password) ? "text-green-600" : "text-gray-400"}>
                  ✓ Минимум 1 заглавная буква
                </p>
                <p className={/[a-z]/.test(password) ? "text-green-600" : "text-gray-400"}>
                  ✓ Минимум 1 строчная буква
                </p>
                <p className={/\d/.test(password) ? "text-green-600" : "text-gray-400"}>
                  ✓ Минимум 1 цифра
                </p>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center text-sm text-gray-700">
              <input
                type="checkbox"
                checked={rememberCredentials}
                onChange={(e) => setRememberCredentials(e.target.checked)}
                className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Запомнить логин и пароль на этом устройстве
            </label>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Загрузка...' : (isLogin ? 'Войти' : 'Зарегистрироваться')}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className="text-blue-600 hover:underline text-sm"
          >
            {isLogin ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти'}
          </button>
        </div>

        {onTryDemo && onViewExample && (
          <div className="mt-6 pt-6 border-t border-gray-200 space-y-3">
            <button
              onClick={onViewExample}
              className="w-full bg-gradient-to-r from-green-600 to-teal-600 text-white py-3 rounded-lg font-semibold hover:from-green-700 hover:to-teal-700 transition shadow-md flex items-center justify-center gap-2"
            >
              <Eye className="w-5 h-5" />
              Посмотреть пример карты
            </button>
            <button
              onClick={onTryDemo}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition shadow-md"
            >
              ✨ Попробовать без регистрации
            </button>
            <p className="text-xs text-gray-500 text-center">
              Посмотрите готовый пример или сгенерируйте свою карту бесплатно
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Auth;

