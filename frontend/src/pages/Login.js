import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';
import { Sparkles } from 'lucide-react';

const Login = ({ onLogin }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({ email: '', password: '', full_name: '' });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await apiClient.post('/auth/login', loginData);
      onLogin(response.data.token, response.data.user);
      toast.success('Login successful!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await apiClient.post('/auth/register', registerData);
      onLogin(response.data.token, response.data.user);
      toast.success('Account created successfully!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo - Premium Design with Black "Seller" text */}
        <div className="text-center mb-10">
          <div className="mb-5 relative inline-block">
            <div className="absolute inset-0 bg-indigo-500/10 blur-2xl rounded-full scale-150"></div>
            <img 
              src="/sellervector-login.svg" 
              alt="SellerVector" 
              className="h-20 w-auto mx-auto relative z-10 drop-shadow-2xl" 
            />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mb-2 tracking-tight">Welcome to SellerVector</h1>
          <p className="text-indigo-600 text-base font-bold tracking-[0.15em] uppercase">Optimise Scale Dominate</p>
        </div>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
          <CardHeader>
            <CardTitle className="text-2xl" style={{ fontFamily: 'Chivo, sans-serif' }}>Welcome Back</CardTitle>
            <CardDescription>Sign in to your account or create a new one</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login" data-testid="login-tab">Login</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab">Register</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      data-testid="login-email-input"
                      type="email"
                      placeholder="seller@example.com"
                      value={loginData.email}
                      onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                      required
                      className="border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white"
                    />
                  </div>
                  <div>
                    <Label htmlFor="login-password">Password</Label>
                    <Input
                      id="login-password"
                      data-testid="login-password-input"
                      type="password"
                      placeholder="••••••••"
                      value={loginData.password}
                      onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                      required
                      className="border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white"
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="login-submit-button"
                    disabled={loading}
                    className="w-full bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
                  >
                    {loading ? 'Signing in...' : 'Sign In'}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div>
                    <Label htmlFor="register-name">Full Name</Label>
                    <Input
                      id="register-name"
                      data-testid="register-name-input"
                      type="text"
                      placeholder="John Doe"
                      value={registerData.full_name}
                      onChange={(e) => setRegisterData({ ...registerData, full_name: e.target.value })}
                      required
                      className="border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white"
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-email">Email</Label>
                    <Input
                      id="register-email"
                      data-testid="register-email-input"
                      type="email"
                      placeholder="seller@example.com"
                      value={registerData.email}
                      onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                      required
                      className="border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white"
                    />
                  </div>
                  <div>
                    <Label htmlFor="register-password">Password</Label>
                    <Input
                      id="register-password"
                      data-testid="register-password-input"
                      type="password"
                      placeholder="••••••••"
                      value={registerData.password}
                      onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                      required
                      className="border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white"
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="register-submit-button"
                    disabled={loading}
                    className="w-full bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
                  >
                    {loading ? 'Creating account...' : 'Create Account'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>

            <div className="mt-6 p-4 bg-indigo-50 border border-indigo-200 rounded-sm">
              <div className="flex items-start gap-3">
                <Sparkles size={20} className="text-indigo-700 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-indigo-900">Demo Account</p>
                  <p className="text-xs text-indigo-700 mt-1">Email: demo@selleros.com | Password: demo123</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-slate-500 mt-6">
          © 2026 SellerVector. Powered by AI.
        </p>
      </div>
    </div>
  );
};

export default Login;
