import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { apiClient } from '@/utils/api';
import { Store, CheckCircle, Trash2, AlertTriangle, RefreshCw, Plus, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';
import { useSearchParams } from 'react-router-dom';

const Settings = () => {
  const [stores,         setStores]         = useState([]);
  const [loading,        setLoading]        = useState(true);
  const [showModal,      setShowModal]       = useState(false);
  const [delConfirm,     setDelConfirm]     = useState(null);
  const [showAdvanced,   setShowAdvanced]   = useState(false);
  const [connectData,    setConnectData]    = useState({
    store_name: '',
    marketplace: 'Amazon India',
    seller_id: '',
    sp_refresh_token: '',
  });
  const [searchParams] = useSearchParams();

  useEffect(() => {
    fetchStores();
    const success = searchParams.get('success');
    const error   = searchParams.get('error');
    if (success === 'store_connected') { toast.success('Store connected!'); fetchStores(); }
    if (error) toast.error('Connection failed. Try manual connection below.');
  }, []);

  const fetchStores = async () => {
    try {
      const res = await apiClient.get('/stores');
      setStores(res.data || []);
    } catch { toast.error('Failed to load stores'); }
    finally   { setLoading(false); }
  };

  const handleConnect = async () => {
    if (!connectData.store_name || !connectData.marketplace) {
      toast.error('Please fill Store Name and Marketplace'); return;
    }
    try {
      await apiClient.post('/stores', {
        store_name:       connectData.store_name,
        marketplace:      connectData.marketplace,
        seller_id:        connectData.seller_id,
        sp_refresh_token: connectData.sp_refresh_token,
      });
      toast.success('Store connected successfully!');
      setShowModal(false);
      setConnectData({ store_name:'', marketplace:'Amazon India', seller_id:'', sp_refresh_token:'' });
      setShowAdvanced(false);
      fetchStores();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to connect store');
    }
  };

  const handleOAuthConnect = async () => {
    if (!connectData.store_name) { toast.error('Enter store name first'); return; }
    try {
      const res = await apiClient.get('/amazon/connect/url', {
        params: { marketplace: 'IN', store_name: connectData.store_name }
      });
      window.location.href = res.data.url;
    } catch { toast.error('OAuth not available yet. Use manual connection below.'); }
  };

  const handleSync = async (storeId, storeName) => {
    try {
      toast.info(`Syncing ${storeName}...`);
      await apiClient.post(`/multi-store/sync/${storeId}`);
      toast.success(`${storeName} synced!`);
      fetchStores();
    } catch { toast.error('Sync failed'); }
  };

  const handleDelete = async (storeId) => {
    try {
      await apiClient.delete(`/stores/${storeId}`);
      setStores(prev => prev.filter(s => s.id !== storeId));
      setDelConfirm(null);
      toast.success('Store disconnected');
    } catch { toast.error('Failed to disconnect'); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
    </div>
  );

  return (
    <div className="space-y-6 fade-in">
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Connected Marketplaces
            </CardTitle>
            <CardDescription>Connect your Amazon store to sync real data</CardDescription>
          </div>
          <Button onClick={() => setShowModal(true)}
                  className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium">
            <Plus size={16} className="mr-2" /> Connect Store
          </Button>
        </CardHeader>
        <CardContent>
          {stores.length === 0 ? (
            <div className="text-center py-12">
              <Store size={40} className="mx-auto text-slate-300 mb-4" />
              <p className="text-slate-600 font-medium mb-2">No stores connected yet</p>
              <Button onClick={() => setShowModal(true)}
                      className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm mt-2">
                <Plus size={16} className="mr-2" /> Connect Your First Store
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {stores.map(store => (
                <div key={store.id}
                     className="flex items-center justify-between p-4 border border-slate-200 rounded-sm hover:border-indigo-300 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-indigo-50 rounded-sm flex items-center justify-center">
                      <Store size={20} className="text-indigo-700" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-900">{store.store_name}</p>
                      <p className="text-xs text-slate-500">{store.marketplace} • {store.seller_id || 'No Seller ID'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 rounded-sm text-xs">
                      <CheckCircle size={11} className="mr-1" /> Connected
                    </Badge>
                    <Button variant="outline" size="sm" onClick={() => handleSync(store.id, store.store_name)}
                            className="text-slate-600 border-slate-200 rounded-sm text-xs">
                      <RefreshCw size={12} className="mr-1" /> Sync
                    </Button>
                    {delConfirm === store.id ? (
                      <div className="flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-sm px-2 py-1">
                        <AlertTriangle size={12} className="text-rose-600" />
                        <span className="text-xs text-rose-700">Disconnect?</span>
                        <button onClick={() => handleDelete(store.id)} className="text-xs text-rose-700 font-bold underline">Yes</button>
                        <button onClick={() => setDelConfirm(null)} className="text-xs text-slate-500">No</button>
                      </div>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={() => setDelConfirm(store.id)}
                              className="text-slate-400 hover:text-rose-600 rounded-sm">
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

      {/* Connect Store Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Connect Amazon Store</DialogTitle>
            <DialogDescription>Connect your store to sync real data</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-2">
            {/* Store Name */}
            <div>
              <Label>Store Name *</Label>
              <Input placeholder="e.g. GLOOYA" value={connectData.store_name}
                     onChange={e => setConnectData({...connectData, store_name: e.target.value})}
                     className="mt-1 border-slate-200 rounded-sm" />
            </div>

            {/* Marketplace */}
            <div>
              <Label>Marketplace *</Label>
              <Select value={connectData.marketplace}
                      onValueChange={v => setConnectData({...connectData, marketplace: v})}>
                <SelectTrigger className="mt-1 border-slate-200 rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Amazon India">🇮🇳 Amazon India</SelectItem>
                  <SelectItem value="Amazon US">🇺🇸 Amazon US</SelectItem>
                  <SelectItem value="Amazon UK">🇬🇧 Amazon UK</SelectItem>
                  <SelectItem value="Amazon Germany">🇩🇪 Amazon Germany</SelectItem>
                  <SelectItem value="Amazon UAE">🇦🇪 Amazon UAE</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Seller ID */}
            <div>
              <Label>Seller ID</Label>
              <Input placeholder="Your Amazon Seller ID" value={connectData.seller_id}
                     onChange={e => setConnectData({...connectData, seller_id: e.target.value})}
                     className="mt-1 border-slate-200 rounded-sm" />
              <p className="text-xs text-slate-400 mt-1">
                Find in Seller Central → Account Info → Merchant Token
              </p>
            </div>

            {/* Advanced — SP API Token */}
            <div>
              <button onClick={() => setShowAdvanced(!showAdvanced)}
                      className="flex items-center gap-2 text-sm text-indigo-600 font-medium">
                {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                Advanced — Add SP-API Token for real data sync
              </button>

              {showAdvanced && (
                <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-sm">
                  <Label>SP-API Refresh Token</Label>
                  <Input
                    placeholder="Atzr|IwEBIK2v..."
                    type="password"
                    value={connectData.sp_refresh_token}
                    onChange={e => setConnectData({...connectData, sp_refresh_token: e.target.value})}
                    className="mt-1 border-slate-200 rounded-sm bg-white font-mono text-xs"
                  />
                  <p className="text-xs text-slate-500 mt-2">
                    Get from: Seller Central → Apps & Services → Manage Apps → Authorize → Copy Refresh Token
                  </p>
                  <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-sm">
                    <p className="text-xs text-amber-700">
                      ⚠️ Keep this token private. It gives access to your Amazon account data.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-2">
              <Button onClick={handleConnect}
                      className="flex-1 bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium">
                Connect Store
              </Button>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-slate-400">or</span>
              </div>
            </div>

            <Button onClick={handleOAuthConnect} variant="outline"
                    className="w-full border-amber-300 text-amber-700 hover:bg-amber-50 rounded-sm font-medium">
              <ExternalLink size={16} className="mr-2" />
              Connect with Amazon (OAuth)
            </Button>
            <p className="text-xs text-slate-400 text-center">
              OAuth available once app is published by Amazon
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Settings;
