import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { apiClient } from '@/utils/api';
import { Plus, Target, Play, Sparkles, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

const Campaigns = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [generatedCampaigns, setGeneratedCampaigns] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [campaignsRes, productsRes] = await Promise.all([
        apiClient.get('/campaigns'),
        apiClient.get('/products')
      ]);
      setCampaigns(campaignsRes.data.campaigns);
      setProducts(productsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCampaigns = async () => {
    if (!selectedProduct) {
      toast.error('Please select a product');
      return;
    }

    try {
      const product = products.find(p => p.id === selectedProduct);
      const response = await apiClient.post('/campaigns/create', {
        product_id: product.id,
        product_name: product.name,
        auto_generate: true
      });
      setGeneratedCampaigns(response.data.campaigns);
      toast.success('Campaigns generated successfully!');
    } catch (error) {
      toast.error('Failed to generate campaigns');
    }
  };

  const handleLaunchCampaigns = () => {
    toast.success('Campaigns launched successfully! (Demo)');
    setShowCreateDialog(false);
    setGeneratedCampaigns(null);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>Campaign Management</h2>
          <p className="text-slate-600 text-sm mt-1">Create, optimize, and manage your advertising campaigns</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button
              data-testid="create-campaign-button"
              className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
            >
              <Plus size={16} className="mr-2" />
              Create Campaign
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles size={20} className="text-indigo-700" />
                Auto-Generate Campaign
              </DialogTitle>
              <DialogDescription>
                Select a product and we'll automatically generate optimized campaign structures for you
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 mt-4">
              {!generatedCampaigns ? (
                <>
                  <div>
                    <Label htmlFor="product-select">Select Product</Label>
                    <Select onValueChange={setSelectedProduct}>
                      <SelectTrigger id="product-select" data-testid="product-select">
                        <SelectValue placeholder="Choose a product" />
                      </SelectTrigger>
                      <SelectContent>
                        {products.map((product) => (
                          <SelectItem key={product.id} value={product.id}>
                            {product.name} - ${product.price}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="bg-indigo-50 border border-indigo-200 rounded-sm p-4">
                    <h4 className="font-semibold text-indigo-900 mb-2">What we'll generate:</h4>
                    <ul className="space-y-2 text-sm text-indigo-700">
                      <li className="flex items-center gap-2">
                        <ChevronRight size={16} />
                        Auto Campaign for broad discovery
                      </li>
                      <li className="flex items-center gap-2">
                        <ChevronRight size={16} />
                        Manual Keyword Campaign with optimized keywords
                      </li>
                      <li className="flex items-center gap-2">
                        <ChevronRight size={16} />
                        Product Targeting Campaign for competitor targeting
                      </li>
                    </ul>
                  </div>

                  <Button
                    onClick={handleGenerateCampaigns}
                    data-testid="generate-campaigns-button"
                    className="w-full bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
                  >
                    <Sparkles size={16} className="mr-2" />
                    Generate Campaigns
                  </Button>
                </>
              ) : (
                <>
                  <div className="space-y-4">
                    {generatedCampaigns.map((campaign, idx) => (
                      <Card key={idx} className="border border-slate-200 rounded-sm">
                        <CardHeader>
                          <div className="flex items-start justify-between">
                            <div>
                              <CardTitle className="text-base">{campaign.campaign_name}</CardTitle>
                              <CardDescription className="capitalize">{campaign.campaign_type.replace('_', ' ')}</CardDescription>
                            </div>
                            <Badge className="bg-amber-50 text-amber-600 border-amber-200 rounded-sm">Draft</Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-slate-600">Budget:</span>
                              <span className="font-mono font-medium">${campaign.budget}</span>
                            </div>
                            {campaign.keywords && (
                              <div>
                                <p className="text-slate-600 mb-1">Keywords ({campaign.keywords.length}):</p>
                                <div className="flex flex-wrap gap-2">
                                  {campaign.keywords.map((kw, i) => (
                                    <Badge key={i} variant="outline" className="text-xs">
                                      {kw.keyword} ({kw.match_type})
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  <Button
                    onClick={handleLaunchCampaigns}
                    data-testid="launch-campaigns-button"
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
                  >
                    <Play size={16} className="mr-2" />
                    Launch All Campaigns
                  </Button>
                </>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Campaigns List */}
      <div className="grid grid-cols-1 gap-6">
        {campaigns.map((campaign) => (
          <Card key={campaign.id} className="bg-white border border-slate-200 shadow-sm rounded-sm hover:border-indigo-300 transition-colors" data-testid={`campaign-card-${campaign.id}`}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>{campaign.campaign_name}</h3>
                    <Badge className={`${
                      campaign.status === 'active' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-slate-50 text-slate-600 border-slate-200'
                    } rounded-sm text-xs uppercase tracking-wider font-bold`}>
                      {campaign.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-slate-600 capitalize">{campaign.campaign_type.replace('_', ' ')}</p>
                </div>
                <Button
                  variant="ghost"
                  data-testid={`view-campaign-${campaign.id}`}
                  className="text-indigo-700 hover:bg-indigo-50 rounded-sm"
                >
                  View Details
                </Button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Budget</p>
                  <p className="text-sm font-mono font-semibold text-slate-900">${campaign.budget.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Ad Spend</p>
                  <p className="text-sm font-mono font-semibold text-rose-600">${campaign.ad_spend.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Ad Sales</p>
                  <p className="text-sm font-mono font-semibold text-emerald-600">${campaign.ad_sales.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">ROAS</p>
                  <p className="text-sm font-mono font-semibold text-indigo-600">{campaign.roas.toFixed(2)}x</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">ACOS</p>
                  <p className="text-sm font-mono font-semibold text-slate-900">{campaign.acos.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Orders</p>
                  <p className="text-sm font-mono font-semibold text-slate-900">{campaign.orders}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Campaigns;
