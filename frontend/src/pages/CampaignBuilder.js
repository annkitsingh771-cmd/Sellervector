import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sparkles, Package, Target, Rocket, ChevronRight, ChevronLeft, Edit2, Check, Loader2 } from 'lucide-react';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';

const CampaignBuilder = () => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [campaignConfig, setCampaignConfig] = useState({
    target_acos: 30,
    target_roas: 3.5,
    daily_budget: 50,
    campaign_types: ['sponsored_products', 'sponsored_brands', 'sponsored_display']
  });
  const [generatedCampaigns, setGeneratedCampaigns] = useState([]);
  const [editingCampaign, setEditingCampaign] = useState(null);
  const [launching, setLaunching] = useState(false);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await apiClient.get('/campaign-builder/products');
      setProducts(response.data.products);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const generateCampaigns = async () => {
    if (!selectedProduct) {
      toast.error('Please select a product');
      return;
    }
    setLoading(true);
    try {
      const response = await apiClient.post('/campaign-builder/generate', {
        product_id: selectedProduct.id,
        product_name: selectedProduct.name,
        ...campaignConfig
      });
      setGeneratedCampaigns(response.data.campaigns);
      setStep(3);
    } catch (error) {
      toast.error('Error generating campaigns');
    } finally {
      setLoading(false);
    }
  };

  const launchCampaigns = async () => {
    setLaunching(true);
    try {
      const response = await apiClient.post('/campaign-builder/launch', {
        campaigns: generatedCampaigns
      });
      toast.success(`Successfully launched ${response.data.launched_campaigns.length} campaigns!`);
      setStep(4);
    } catch (error) {
      toast.error('Error launching campaigns');
    } finally {
      setLaunching(false);
    }
  };

  const updateCampaign = (campaignId, updates) => {
    setGeneratedCampaigns(prev => prev.map(c => 
      c.id === campaignId ? { ...c, ...updates } : c
    ));
  };

  const toggleCampaignType = (type) => {
    setCampaignConfig(prev => ({
      ...prev,
      campaign_types: prev.campaign_types.includes(type)
        ? prev.campaign_types.filter(t => t !== type)
        : [...prev.campaign_types, type]
    }));
  };

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {[1, 2, 3, 4].map((s) => (
        <React.Fragment key={s}>
          <div className={`flex items-center justify-center w-10 h-10 rounded-full font-semibold transition-all ${
            step >= s ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-400'
          }`}>
            {step > s ? <Check size={20} /> : s}
          </div>
          {s < 4 && (
            <div className={`w-16 h-1 mx-2 rounded ${step > s ? 'bg-indigo-600' : 'bg-slate-200'}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );

  const renderStep1 = () => (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Package className="text-indigo-600" size={24} />
          Step 1: Select Product
        </CardTitle>
        <CardDescription>Choose the product you want to advertise</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map((product) => (
            <div
              key={product.id}
              onClick={() => setSelectedProduct(product)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                selectedProduct?.id === product.id
                  ? 'border-indigo-600 bg-indigo-50'
                  : 'border-slate-200 hover:border-indigo-300'
              }`}
              data-testid={`product-${product.id}`}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-slate-900">{product.name}</h3>
                {selectedProduct?.id === product.id && (
                  <Check className="text-indigo-600" size={20} />
                )}
              </div>
              <p className="text-sm text-slate-500">ASIN: {product.asin}</p>
              <p className="text-sm text-slate-500">SKU: {product.sku}</p>
              <p className="text-lg font-bold text-indigo-600 mt-2">${product.price}</p>
            </div>
          ))}
        </div>

        <div className="flex justify-end mt-6">
          <Button 
            onClick={() => setStep(2)} 
            disabled={!selectedProduct}
            className="bg-indigo-600 hover:bg-indigo-700"
            data-testid="next-step-1"
          >
            Next: Configure Campaign
            <ChevronRight size={16} className="ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderStep2 = () => (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="text-indigo-600" size={24} />
          Step 2: Configure Campaign Settings
        </CardTitle>
        <CardDescription>Set your targets and budget</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Selected Product Summary */}
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-500">Selected Product</p>
            <p className="font-semibold text-slate-900">{selectedProduct?.name}</p>
            <p className="text-sm text-slate-500">ASIN: {selectedProduct?.asin}</p>
          </div>

          {/* Campaign Types */}
          <div>
            <Label className="mb-3 block">Campaign Types</Label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { id: 'sponsored_products', label: 'Sponsored Products', desc: 'Product ads in search results' },
                { id: 'sponsored_brands', label: 'Sponsored Brands', desc: 'Brand awareness & video ads' },
                { id: 'sponsored_display', label: 'Sponsored Display', desc: 'Retargeting & audience ads' }
              ].map((type) => (
                <div
                  key={type.id}
                  onClick={() => toggleCampaignType(type.id)}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    campaignConfig.campaign_types.includes(type.id)
                      ? 'border-indigo-600 bg-indigo-50'
                      : 'border-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Checkbox checked={campaignConfig.campaign_types.includes(type.id)} />
                    <span className="font-medium">{type.label}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{type.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Targets */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="target_acos">Target ACOS (%)</Label>
              <Input
                id="target_acos"
                type="number"
                value={campaignConfig.target_acos}
                onChange={(e) => setCampaignConfig(prev => ({ ...prev, target_acos: parseFloat(e.target.value) }))}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="target_roas">Target ROAS (x)</Label>
              <Input
                id="target_roas"
                type="number"
                step="0.1"
                value={campaignConfig.target_roas}
                onChange={(e) => setCampaignConfig(prev => ({ ...prev, target_roas: parseFloat(e.target.value) }))}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="daily_budget">Total Daily Budget ($)</Label>
              <Input
                id="daily_budget"
                type="number"
                value={campaignConfig.daily_budget}
                onChange={(e) => setCampaignConfig(prev => ({ ...prev, daily_budget: parseFloat(e.target.value) }))}
                className="mt-1"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-between mt-6">
          <Button variant="outline" onClick={() => setStep(1)}>
            <ChevronLeft size={16} className="mr-2" />
            Back
          </Button>
          <Button 
            onClick={generateCampaigns} 
            disabled={loading || campaignConfig.campaign_types.length === 0}
            className="bg-indigo-600 hover:bg-indigo-700"
            data-testid="generate-campaigns"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles size={16} className="mr-2" />
                Generate AI Campaigns
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderStep3 = () => (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="text-indigo-600" size={24} />
          Step 3: Review & Edit Campaigns
        </CardTitle>
        <CardDescription>Review AI-generated campaigns and make adjustments</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {generatedCampaigns.map((campaign) => (
            <div key={campaign.id} className="p-4 border border-slate-200 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-900">{campaign.campaign_name}</h3>
                  <Badge variant="outline" className="mt-1">{campaign.campaign_type}</Badge>
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-500">Daily Budget</p>
                  {editingCampaign === campaign.id ? (
                    <Input
                      type="number"
                      value={campaign.daily_budget}
                      onChange={(e) => updateCampaign(campaign.id, { daily_budget: parseFloat(e.target.value) })}
                      className="w-24 h-8 text-right"
                    />
                  ) : (
                    <p className="text-lg font-bold text-indigo-600">${campaign.daily_budget}</p>
                  )}
                </div>
              </div>

              {/* Ad Groups / Keywords */}
              {campaign.ad_groups && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-slate-700 mb-2">Ad Groups</p>
                  <div className="flex flex-wrap gap-2">
                    {campaign.ad_groups.map((ag, idx) => (
                      <Badge key={idx} variant="secondary">
                        {ag.name}: ${ag.bid}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {campaign.keywords && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-slate-700 mb-2">Keywords</p>
                  <div className="flex flex-wrap gap-2">
                    {campaign.keywords.map((kw, idx) => (
                      <Badge key={idx} variant="secondary">
                        {kw.keyword} ({kw.match_type}): ${kw.bid}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {campaign.audiences && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-slate-700 mb-2">Audiences</p>
                  <div className="flex flex-wrap gap-2">
                    {campaign.audiences.map((aud, idx) => (
                      <Badge key={idx} variant="secondary">{aud}</Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-3 flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditingCampaign(editingCampaign === campaign.id ? null : campaign.id)}
                >
                  <Edit2 size={14} className="mr-1" />
                  {editingCampaign === campaign.id ? 'Done' : 'Edit'}
                </Button>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-between mt-6">
          <Button variant="outline" onClick={() => setStep(2)}>
            <ChevronLeft size={16} className="mr-2" />
            Back
          </Button>
          <Button 
            onClick={launchCampaigns} 
            disabled={launching}
            className="bg-emerald-600 hover:bg-emerald-700"
            data-testid="launch-campaigns"
          >
            {launching ? (
              <>
                <Loader2 size={16} className="mr-2 animate-spin" />
                Launching...
              </>
            ) : (
              <>
                <Rocket size={16} className="mr-2" />
                Launch Campaigns
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderStep4 = () => (
    <Card className="border-slate-200">
      <CardContent className="py-12 text-center">
        <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Rocket className="text-emerald-600" size={32} />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Campaigns Launched!</h2>
        <p className="text-slate-500 mb-6">
          {generatedCampaigns.length} campaigns have been created and are now live.
        </p>
        <div className="flex justify-center gap-4">
          <Button variant="outline" onClick={() => {
            setStep(1);
            setSelectedProduct(null);
            setGeneratedCampaigns([]);
          }}>
            Create Another
          </Button>
          <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={() => window.location.href = '/campaigns'}>
            View Campaigns
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6" data-testid="campaign-builder-page">
      {renderStepIndicator()}
      
      {step === 1 && renderStep1()}
      {step === 2 && renderStep2()}
      {step === 3 && renderStep3()}
      {step === 4 && renderStep4()}
    </div>
  );
};

export default CampaignBuilder;
