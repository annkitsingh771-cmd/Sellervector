import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { apiClient } from '@/utils/api';
import { Store, CheckCircle, Trash2, AlertTriangle, Zap, RefreshCw, Plus, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { useSearchParams } from 'react-router-dom';

const Settings = () => {
  const [stores,          setStores]          = useState([]);
  const [marketplaces,    setMarketplaces]    = useState([]);
  const [loading,         setLoading]         = useState(true);
  const [connecting,      setConnecting]      = useState(false);
  const [delConfirm,      setDelConfirm]      = useState(null);
  const [showModal,       setShowModal]       = useState(false);
  const [selectedMP,      setSelectedMP]      = useState('IN');
  const [storeName,       setStoreName]       = useState('');
  const [searchParams]    = useSearchParams();

  useEffect(() => {
    fetchStores();
    fetchMarketplaces();

    // handle redirect back from Amazon OAuth
    const success = searchParams.get('success');
    const error   = searchParams.get('error');
    if (success === 'store_connected') {
      toast.success('Amazon store connected successfully!');
      fetchStores();
    } else if (success === 'ads_connected') {
      toast.success('Amazon Ads API connected!');
      fetchStores();
    } else if (error) {
      const msgs = {
        amazon_denied:      'You cancelled the Amazon connection',
        invalid_state:      'Connection expired. Please try again.',
        token_exchange_failed: 'Failed to get Amazon token. Try again.',
        ads_denied:         'You cancelled Ads connection',
        ads_token_failed:   'Failed to connect Ads API',
      };
      toast.error(msgs[error] || 'Connection failed. Please try again.');
    }
  }, []);

  const fetchStores = async () => {
    try {
      const res = await apiClient.get('/stores');
      setStores(res.data || []);
    } catch { toast.error('Failed to load stores'); }
    finally   { setLoading(false); }
  };

  const fetchMarketplaces = async () => {
    try {
      const res = await apiClient.get('/amazon/marketplaces');
      setMarketplaces(res.data.marketplaces || []);
    } catch {
      // fallback list
      setMarketplaces([
        { code: 'IN', name: 'Amazon India' },
        { code: 'US', name: 'Amazon US' },
        { code: 'UK', name: 'Amazon UK' },
        { code: 'DE', name: 'Amazon Germany' },
        { code: 'AE', name: 'Amazon UAE' },
      ]);
    }
  };

  const handleConnectAmazon = async () => {
    if (!storeName.trim()) {
      toast.error('Please enter a store name');
      return;
    }
    setConnecting(true);
    try {
      // Get OAuth URL from backend
      const res = await apiClient.get('/amazon/connect/url', {
        params: { marketplace: selectedMP, store_name: storeName.trim() }
      });
      const { url } = res.data;
      // Redirect to Amazon authorization page
      window.location.href = url;
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to get Amazon URL. Check SP_API_CLIENT_ID in Render.');
      setConnecting(false);
    }
  };

  const handleConnectAds = async (storeId) => {
    try {
      const res = await apiClient.get('/amazon/ads/connect/url', {
        params: { store_id: storeId }
      });
      window.location.href = res.data.url;
    } catch (err) {
      toast.error('Failed to connect Ads API');
    }
  };

  const handleSync = async (storeId, storeName) => {
    try {
      toast.info(`Syncing ${storeName}...`);
      const res = await apiClient.post(`/multi-store/sync/${storeId}`);
      const r = res.data;
      toast.success(`${storeName} synced! Orders: ${r.total_orders || 0}, Campaigns: ${r.campaigns || 0}`);
      fetchStores();
    } catch { toast.error('Sync failed'); }
  };

  const handleDelete = async (storeId) => {
    try {
      await apiClient.delete(`/stores/${storeId}`);
      setStores(prev => prev.filter(s => s.id !== storeId));
      setDelConfirm(null);
      toast.success('Store disconnected');
    } catch { toast.error('Failed to disconnect store'); }
  };

  const mpFlag = (code) => ({
    IN: '🇮🇳', US: '🇺🇸', UK: '🇬🇧', DE: '🇩🇪', AE: '🇦🇪'
  }[code] || '🏪');

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
    </div>
  );

  return (
    <div className="space-y-6 fade-in">

      {/* ── Connected Stores ── */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Connected Marketplaces
            </CardTitle>
            <CardDescription>
              Click "Connect Amazon" — you'll be redirected to Amazon to authorize. No manual tokens needed!
            </CardDescription>
          </div>
          <Button
            onClick={() => setShowModal(true)}
            className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium"
            data-testid="connect-store-button"
          >
            <Plus size={16} className="mr-2" />
            Connect Amazon
          </Button>
        </CardHeader>
        <CardContent>
          {stores.length === 0 ? (
            <div className="text-center py-14">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Store size={32} className="text-slate-400" />
              </div>
              <p className="text-slate-600 font-medium mb-2">No stores connected yet</p>
              <p className="text-sm text-slate-500 mb-6">
                Connect your Amazon seller account to start tracking orders, inventory and campaigns
              </p>
              <Button
                onClick={() => setShowModal(true)}
                className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm"
              >
                <Plus size={16} className="mr-2" />
                Connect Your First Store
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {stores.map(store => (
                <div key={store.id}
                     className="p-4 border border-slate-200 rounded-sm hover:border-indigo-300 transition-colors">
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    {/* Store info */}
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-indigo-50 rounded-sm flex items-center justify-center text-2xl">
                        {mpFlag(store.marketplace_id === 'A21TJRUUN4KGV' ? 'IN' :
                                store.marketplace_id === 'ATVPDKIKX0DER' ? 'US' : 'UK')}
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-900">{store.store_name}</h4>
                        <p className="text-sm text-slate-500">{store.marketplace} • {store.seller_id || 'No Seller ID'}</p>
                      </div>
                    </div>

                    {/* Status badges */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 rounded-sm text-xs">
                        <CheckCircle size={11} className="mr-1" /> Connected
                      </Badge>
                      {store.has_sp_api ? (
                        <Badge className="bg-blue-50 text-blue-700 border-blue-200 rounded-sm text-xs">
                          ✓ SP-API
                        </Badge>
                      ) : (
                        <Badge className="bg-amber-50 text-amber-700 border-amber-200 rounded-sm text-xs">
                          ⚠ No SP-API
                        </Badge>
                      )}
                      {store.has_ads_api ? (
                        <Badge className="bg-purple-50 text-purple-700 border-purple-200 rounded-sm text-xs">
                          ✓ Ads API
                        </Badge>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleConnectAds(store.id)}
                          className="text-purple-600 border-purple-200 hover:bg-purple-50 rounded-sm text-xs h-6 px-2"
                        >
                          <Zap size={10} className="mr-1" />
                          Connect Ads
                        </Button>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSync(store.id, store.store_name)}
                        className="text-slate-600 border-slate-200 rounded-sm text-xs"
                      >
                        <RefreshCw size={12} className="mr-1" />
                        Sync Now
                      </Button>
                      {delConfirm === store.id ? (
                        <div className="flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-sm px-2 py-1">
                          <AlertTriangle size={12} className="text-rose-600" />
                          <span className="text-xs text-rose-700 font-medium">Disconnect?</span>
                          <button onClick={() => handleDelete(store.id)} className="text-xs text-rose-700 font-bold hover:text-rose-900 underline">Yes</button>
                          <button onClick={() => setDelConfirm(null)} className="text-xs text-slate-500">No</button>
                        </div>
                      ) : (
                        <Button variant="ghost" size="sm" onClick={() => setDelConfirm(store.id)}
                                className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-sm">
                          <Trash2 size={14} />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Last sync info */}
                  {store.last_sync && (
                    <p className="text-xs text-slate-400 mt-2 ml-15">
                      Last synced: {new Date(store.last_sync).toLocaleString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Connect Modal ── */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="text-2xl">🛒</span>
              Connect Amazon Store
            </DialogTitle>
            <DialogDescription>
              You'll be redirected to Amazon to authorize SellerVector. No passwords or tokens needed!
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-2">
            {/* Store name */}
            <div>
              <Label htmlFor="store-name" className="text-sm font-medium text-slate-700">
                Store Name
              </Label>
              <Input
                id="store-name"
                placeholder="e.g. My Brand India"
                value={storeName}
                onChange={e => setStoreName(e.target.value)}
                className="mt-1 border-slate-200 focus:border-indigo-500 rounded-sm"
              />
              <p className="text-xs text-slate-400 mt-1">Give this store a name so you can identify it</p>
            </div>

            {/* Marketplace */}
            <div>
              <Label className="text-sm font-medium text-slate-700">Marketplace</Label>
              <Select value={selectedMP} onValueChange={setSelectedMP}>
                <SelectTrigger className="mt-1 border-slate-200 rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {marketplaces.map(mp => (
                    <SelectItem key={mp.code} value={mp.code}>
                      {mpFlag(mp.code)} {mp.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* How it works */}
            <div className="bg-indigo-50 border border-indigo-100 rounded-sm p-3">
              <p className="text-xs font-semibold text-indigo-800 mb-1">How it works:</p>
              <ol className="text-xs text-indigo-700 space-y-1 list-decimal list-inside">
                <li>Click "Connect with Amazon" below</li>
                <li>Log into your Amazon Seller Central</li>
                <li>Click "Authorize" to grant access</li>
                <li>You'll be redirected back here automatically</li>
              </ol>
            </div>

            {/* Connect button */}
            <Button
              onClick={handleConnectAmazon}
              disabled={connecting || !storeName.trim()}
              className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-sm font-semibold text-sm py-3"
            >
              {connecting ? (
                <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />Redirecting to Amazon...</>
              ) : (
                <><ExternalLink size={16} className="mr-2" />Connect with Amazon</>
              )}
            </Button>

            <p className="text-xs text-slate-400 text-center">
              You can connect multiple Amazon accounts — each will have its own separate data
            </p>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
};

export default Settings;
