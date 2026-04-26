import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';
import { Sparkles, AlertCircle } from 'lucide-react';

const Login = ({ onLogin }) => {
  const navigate = useNavigate();
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState('');
  const [loginData,    setLoginData]    = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({ email: '', password: '', full_name: '' });

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await apiClient.post('/auth/login', loginData);

      // handle both response formats
      const token = res.data.token || res.data.access_token;
      const user  = res.data.user;

      if (!token) {
        setError('Login failed — no token received. Please try again.');
        return;
      }

      onLogin(token, user);
      toast.success('Login successful!');
      // small delay to ensure state is set
      setTimeout(() => navigate('/'), 100);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Login failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    if (registerData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/auth/register', registerData);

      const token = res.data.token || res.data.access_token;
      const user  = res.data.user;

      if (!token) {
        setError('Registration failed — no token received. Please try again.');
        return;
      }

      onLogin(token, user);
      toast.success('Account created! Welcome to SellerVector 🎉');
      setTimeout(() => navigate('/'), 100);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Registration failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="relative inline-block mb-4">
            <div className="absolute inset-0 bg-indigo-500/10 blur-2xl rounded-full scale-150" />
            <img src="/sellervector-login.svg" alt="SellerVector"
                 className="h-20 w-auto mx-auto relative z-10 drop-shadow-2xl"
                 onError={e => { e.target.style.display='none'; }} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">SellerVector</h1>
          <p className="text-sm text-slate-500 mt-1">Optimise · Scale · Dominate</p>
        </div>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
          <CardHeader>
            <CardTitle className="text-xl" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Welcome Back
            </CardTitle>
            <CardDescription>Sign in to your account or create a new one</CardDescription>
          </CardHeader>
          <CardContent>

            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-rose-50 border border-rose-200 rounded-sm mb-4">
                <AlertCircle size={15} className="text-rose-600 flex-shrink-0" />
                <p className="text-sm text-rose-700">{error}</p>
              </div>
            )}

            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login"    data-testid="login-tab">Login</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab">Register</TabsTrigger>
              </TabsList>

              {/* ── Login ── */}
              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      data-testid="login-email-input"
                      type="email"
                      placeholder="seller@example.com"
                      required
                      value={loginData.email}
                      onChange={e => setLoginData({ ...loginData, email: e.target.value })}
                      className="mt-1 border-slate-200 focus:border-indigo-500 rounded-sm"
                    />
                  </div>
                  <div>
                    <Label htmlFor="login-password">Password</Label>
                    <Input
                      id="login-password"
                      data-testid="login-password-input"
                      type="password"
                      placeholder="••••••••"
                      required
                      value={loginData.password}
                      onChange={e => setLoginData({ ...loginData, password: e.target.value })}
                      className="mt-1 border-slate-200 focus:border-indigo-500 rounded-sm"
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="login-submit-button"
                    disabled={loading}
                    className="w-full bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium"
                  >
                    {loading ? (
                      <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />Signing in...</>
                    ) : 'Sign In'}
                  </Button>
                </form>
              </TabsContent>

              {/* ── Register ── */}
              <TabsContent value="register">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div>
                    <Label htmlFor="register-name">Full Name</Label>
                    <Input
                      id="register-name"
                      data-testid="register-name-input"
                      type="text"
                      placeholder="John Doe"
                      required
                      value={registerData.full_name}
                      onChange={e => setRegisterData({ ...registerData, full_name: e.target.value })}
                      className="mt-1 border-slate-200 focus:border-indigo-500 rounded-sm"
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-email">Email</Label>
                    <Input
                      id="register-email"
                      data-testid="register-email-input"
                      type="email"
                      placeholder="seller@example.com"
                      required
                      value={registerData.email}
                      onChange={e => setRegisterData({ ...registerData, email: e.target.value })}
                      className="mt-1 border-slate-200 focus:border-indigo-500 rounded-sm"
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-password">Password</Label>
                    <Input
                      id="register-password"
                      data-testid="register-password-input"
                      type="password"
                      placeholder="Min 6 characters"
                      required
                      value={registerData.password}
                      onChange={e => setRegisterData({ ...registerData, password: e.target.value })}
                      className="mt-1 border-slate-200 focus:border-indigo-500 rounded-sm"
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="register-submit-button"
                    disabled={loading}
                    className="w-full bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium"
                  >
                    {loading ? (
                      <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />Creating account...</>
                    ) : 'Create Account'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>

            {/* Demo account */}
            <div className="mt-5 p-3 bg-indigo-50 border border-indigo-200 rounded-sm">
              <div className="flex items-start gap-2">
                <Sparkles size={16} className="text-indigo-700 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-indigo-900">Demo Account</p>
                  <p className="text-xs text-indigo-700 mt-0.5">
                    Email: <strong>demo@sellervector.com</strong><br />
                    Password: <strong>demo123</strong>
                  </p>
                </div>
              </div>
            </div>

          </CardContent>
        </Card>

        {/* Backend wake-up notice */}
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-sm">
          <p className="text-xs text-amber-700 text-center">
            ⚡ First login may take <strong>30-60 seconds</strong> — free server wakes up on first request
          </p>
        </div>

        <p className="text-center text-xs text-slate-400 mt-4">© 2026 SellerVector. All rights reserved.</p>
      </div>
    </div>
  );
};

export default Login;
