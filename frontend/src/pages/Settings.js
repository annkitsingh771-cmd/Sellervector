import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { apiClient } from '@/utils/api';
import { Plus, Store, CheckCircle, Trash2, RefreshCw, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const Settings = () => {
  const [stores,             setStores]             = useState([]);
  const [loading,            setLoading]            = useState(true);
  const [showConnectDialog,  setShowConnectDialog]  = useState(false);
  const [delConfirm,         setDelConfirm]         = useState(null);   // store id pending delete
  const [connectData,        setConnectData]        = useState({ marketplace: '', store_name: '', seller_id: '' });

  useEffect(() => { fetchStores(); }, []);

  const fetchStores = async () => {
    try {
      const res = await apiClient.get('/stores');  // ← GET /api/stores (not /stores/connect)
      setStores(res.data || []);
    } catch { toast.error('Failed to load stores'); }
    finally   { setLoading(false); }
  };

  const handleConnectStore = async () => {
    if (!connectData.marketplace || !connectData.store_name || !connectData.seller_id) {
      toast.error('Please fill all fields'); return;
    }
    try {
      await apiClient.post('/stores', connectData);   // ← POST /api/stores
      toast.success('Store connected successfully!');
      setShowConnectDialog(false);
      setConnectData({ marketplace: '', store_name: '', seller_id: '' });
      fetchStores();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to connect store');
    }
  };

  const handleDeleteStore = async (storeId) => {
    try {
      await apiClient.delete(`/stores/${storeId}`);
      setStores(prev => prev.filter(s => s.id !== storeId));
      setDelConfirm(null);
      toast.success('Store disconnected');
    } catch { toast.error('Failed to disconnect store'); }
  };

  const marketplaces = ['Amazon', 'Flipkart', 'Meesho', 'eBay'];

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* ── Connected Stores ─────────────────────────── */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Connected Marketplaces
            </CardTitle>
            <CardDescription>Each account only sees its own stores — separate accounts never share data</CardDescription>
          </div>
          <Dialog open={showConnectDialog} onOpenChange={setShowConnectDialog}>
            <DialogTrigger asChild>
              <Button data-testid="connect-store-button"
                      className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95">
                <Plus size={16} className="mr-2" /> Connect Store
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Connect Marketplace</DialogTitle>
                <DialogDescription>Connect your marketplace account to start syncing data</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label>Marketplace</Label>
                  <Select onValueChange={v => setConnectData({ ...connectData, marketplace: v })}>
                    <SelectTrigger data-testid="marketplace-select">
                      <SelectValue placeholder="Select marketplace" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Amazon">Amazon</SelectItem>
                      <SelectItem value="Flipkart">Flipkart (Coming Soon)</SelectItem>
                      <SelectItem value="Meesho">Meesho (Coming Soon)</SelectItem>
                      <SelectItem value="eBay">eBay (Coming Soon)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="store-name">Store Name</Label>
                  <Input id="store-name" data-testid="store-name-input"
                         placeholder="My Amazon Store" value={connectData.store_name}
                         onChange={e => setConnectData({ ...connectData, store_name: e.target.value })}
                         className="border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white" />
                </div>
                <div>
                  <Label htmlFor="seller-id">Seller ID</Label>
                  <Input id="seller-id" data-testid="seller-id-input"
                         placeholder="Enter your seller ID" value={connectData.seller_id}
                         onChange={e => setConnectData({ ...connectData, seller_id: e.target.value })}
                         className="border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white" />
                </div>
                <div className="bg-amber-50 border border-amber-200 rounded-sm p-3">
                  <p className="text-xs text-amber-700">
                    <strong>Note:</strong> API integration configured with real credentials.
                    Currently in demo mode.
                  </p>
                </div>
                <Button onClick={handleConnectStore} data-testid="connect-store-submit-button"
                        className="w-full bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95">
                  Connect Store
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardHeader>

        <CardContent>
          {stores.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Store size={32} className="text-slate-400" />
              </div>
              <p className="text-slate-600 mb-4">No stores connected yet</p>
              <p className="text-sm text-slate-500">Connect your first marketplace to start tracking your business</p>
            </div>
          ) : (
            <div className="space-y-3">
              {stores.map(store => (
                <div key={store.id}
                     className="flex items-center justify-between p-4 border border-slate-200 rounded-sm hover:border-indigo-300 transition-colors"
                     data-testid={`store-card-${store.id}`}>
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-indigo-50 rounded-sm flex items-center justify-center">
                      <Store size={24} className="text-indigo-700" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-900">{store.store_name}</h4>
                      <p className="text-sm text-slate-600">{store.marketplace} • {store.seller_id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-emerald-50 text-emerald-600 border-emerald-200 rounded-sm text-xs flex items-center gap-1">
                      <CheckCircle size={12} /> Active
                    </Badge>
                    {/* Disconnect (with confirmation) */}
                    {delConfirm === store.id ? (
                      <div className="flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-sm px-3 py-1.5">
                        <AlertTriangle size={13} className="text-rose-600" />
                        <span className="text-xs text-rose-700 font-medium">Disconnect?</span>
                        <button onClick={() => handleDeleteStore(store.id)}
                                className="text-xs text-rose-700 font-bold hover:text-rose-900 underline">Yes</button>
                        <button onClick={() => setDelConfirm(null)}
                                className="text-xs text-slate-500 hover:text-slate-700">Cancel</button>
                      </div>
                    ) : (
                      <Button variant="ghost" size="sm"
                              className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-sm"
                              onClick={() => setDelConfirm(store.id)}>
                        <Trash2 size={14} />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Account Settings ─────────────────────────── */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Account Settings
          </CardTitle>
          <CardDescription>Manage your account preferences</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-600">Account settings and preferences will be available here.</p>
        </CardContent>
      </Card>
    </div>
  );
};

export default Settings;
