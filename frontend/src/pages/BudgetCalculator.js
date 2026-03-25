import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Calculator, TrendingUp, DollarSign, Target, AlertCircle, CheckCircle, Lightbulb, ArrowRight } from 'lucide-react';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';

const BudgetCalculator = () => {
  const [loading, setLoading] = useState(false);
  const [budgetPlans, setBudgetPlans] = useState([]);
  const [calculatorInputs, setCalculatorInputs] = useState({
    budget: 1000,
    cpc: 0.50,
    cvr: 10,
    avg_order_value: 50,
    target_acos: 30
  });
  const [predictions, setPredictions] = useState(null);
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    fetchBudgetPlans();
  }, []);

  const fetchBudgetPlans = async () => {
    try {
      const response = await apiClient.get('/budget-planner/products');
      setBudgetPlans(response.data.budget_plans);
    } catch (error) {
      console.error('Error fetching budget plans:', error);
    }
  };

  const calculatePredictions = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/budget-calculator', calculatorInputs);
      setPredictions(response.data.predictions);
      setRecommendations(response.data.recommendations);
    } catch (error) {
      toast.error('Error calculating predictions');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setCalculatorInputs(prev => ({ ...prev, [field]: parseFloat(value) || 0 }));
  };

  const updateProductBudget = async (productId, newBudget) => {
    try {
      await apiClient.patch(`/budget-planner/products/${productId}`, { daily_budget: newBudget });
      toast.success('Budget updated successfully');
      fetchBudgetPlans();
    } catch (error) {
      toast.error('Error updating budget');
    }
  };

  return (
    <div className="space-y-6" data-testid="budget-calculator-page">
      <Tabs defaultValue="calculator" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-6">
          <TabsTrigger value="calculator" data-testid="calculator-tab">
            <Calculator size={16} className="mr-2" />
            ROAS Calculator
          </TabsTrigger>
          <TabsTrigger value="planner" data-testid="planner-tab">
            <Target size={16} className="mr-2" />
            ASIN Budget Planner
          </TabsTrigger>
        </TabsList>

        {/* ROAS Calculator Tab */}
        <TabsContent value="calculator">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input Section */}
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calculator className="text-indigo-600" size={20} />
                  Budget & ROAS Predictor
                </CardTitle>
                <CardDescription>
                  Enter your metrics to predict campaign performance
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="budget">Daily Budget ($)</Label>
                    <Input
                      id="budget"
                      data-testid="budget-input"
                      type="number"
                      value={calculatorInputs.budget}
                      onChange={(e) => handleInputChange('budget', e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="cpc">Average CPC ($)</Label>
                    <Input
                      id="cpc"
                      data-testid="cpc-input"
                      type="number"
                      step="0.01"
                      value={calculatorInputs.cpc}
                      onChange={(e) => handleInputChange('cpc', e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="cvr">Conversion Rate (%)</Label>
                    <Input
                      id="cvr"
                      data-testid="cvr-input"
                      type="number"
                      step="0.1"
                      value={calculatorInputs.cvr}
                      onChange={(e) => handleInputChange('cvr', e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="aov">Avg Order Value ($)</Label>
                    <Input
                      id="aov"
                      data-testid="aov-input"
                      type="number"
                      value={calculatorInputs.avg_order_value}
                      onChange={(e) => handleInputChange('avg_order_value', e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="target_acos">Target ACOS (%)</Label>
                  <Input
                    id="target_acos"
                    data-testid="target-acos-input"
                    type="number"
                    value={calculatorInputs.target_acos}
                    onChange={(e) => handleInputChange('target_acos', e.target.value)}
                    className="mt-1"
                  />
                </div>

                <Button 
                  onClick={calculatePredictions} 
                  disabled={loading}
                  data-testid="calculate-button"
                  className="w-full bg-indigo-600 hover:bg-indigo-700"
                >
                  {loading ? 'Calculating...' : 'Calculate Predictions'}
                </Button>
              </CardContent>
            </Card>

            {/* Results Section */}
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="text-emerald-600" size={20} />
                  Predicted Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                {predictions ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-slate-50 rounded-lg">
                        <p className="text-sm text-slate-500">Est. Clicks</p>
                        <p className="text-2xl font-bold text-slate-900">{predictions.estimated_clicks.toLocaleString()}</p>
                      </div>
                      <div className="p-4 bg-slate-50 rounded-lg">
                        <p className="text-sm text-slate-500">Est. Orders</p>
                        <p className="text-2xl font-bold text-slate-900">{predictions.estimated_orders.toLocaleString()}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-emerald-50 rounded-lg">
                        <p className="text-sm text-emerald-600">Est. Sales</p>
                        <p className="text-2xl font-bold text-emerald-700">${predictions.estimated_sales.toLocaleString()}</p>
                      </div>
                      <div className="p-4 bg-indigo-50 rounded-lg">
                        <p className="text-sm text-indigo-600">Est. ROAS</p>
                        <p className="text-2xl font-bold text-indigo-700">{predictions.estimated_roas}x</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className={`p-4 rounded-lg ${predictions.estimated_acos <= calculatorInputs.target_acos ? 'bg-emerald-50' : 'bg-rose-50'}`}>
                        <p className={`text-sm ${predictions.estimated_acos <= calculatorInputs.target_acos ? 'text-emerald-600' : 'text-rose-600'}`}>Est. ACOS</p>
                        <p className={`text-2xl font-bold ${predictions.estimated_acos <= calculatorInputs.target_acos ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {predictions.estimated_acos}%
                        </p>
                      </div>
                      <div className={`p-4 rounded-lg ${predictions.profit_after_ads >= 0 ? 'bg-emerald-50' : 'bg-rose-50'}`}>
                        <p className={`text-sm ${predictions.profit_after_ads >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>Profit After Ads</p>
                        <p className={`text-2xl font-bold ${predictions.profit_after_ads >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                          ${predictions.profit_after_ads.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    {/* Recommendations */}
                    {recommendations.length > 0 && (
                      <div className="mt-6 space-y-2">
                        <h4 className="font-semibold text-slate-700 flex items-center gap-2">
                          <Lightbulb size={16} className="text-amber-500" />
                          Recommendations
                        </h4>
                        {recommendations.map((rec, idx) => (
                          <div key={idx} className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg">
                            <AlertCircle size={16} className="text-amber-600 mt-0.5 flex-shrink-0" />
                            <p className="text-sm text-amber-800">{rec}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 text-slate-400">
                    <Calculator size={48} className="mb-4" />
                    <p>Enter your metrics and click Calculate</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ASIN Budget Planner Tab */}
        <TabsContent value="planner">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="text-indigo-600" size={20} />
                ASIN/SKU Budget Planning
              </CardTitle>
              <CardDescription>
                Manage daily budgets for each product
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full" data-testid="budget-plans-table">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">Product</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-slate-600">ASIN</th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">Daily Budget</th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">Current Spend</th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">Utilization</th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">ACOS</th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">ROAS</th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-slate-600">Recommended</th>
                      <th className="text-center py-3 px-4 text-sm font-semibold text-slate-600">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {budgetPlans.map((plan) => (
                      <tr key={plan.product_id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-4">
                          <p className="font-medium text-slate-900">{plan.product_name}</p>
                          <p className="text-xs text-slate-500">{plan.sku}</p>
                        </td>
                        <td className="py-3 px-4 text-sm text-slate-600">{plan.asin}</td>
                        <td className="py-3 px-4 text-right font-medium">${plan.daily_budget}</td>
                        <td className="py-3 px-4 text-right">${plan.current_daily_spend}</td>
                        <td className="py-3 px-4 text-right">
                          <Badge variant={plan.budget_utilization > 100 ? 'destructive' : plan.budget_utilization > 80 ? 'warning' : 'secondary'}>
                            {plan.budget_utilization}%
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className={plan.acos > 30 ? 'text-rose-600' : 'text-emerald-600'}>
                            {plan.acos}%
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className={plan.roas >= 3 ? 'text-emerald-600' : 'text-amber-600'}>
                            {plan.roas}x
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className={plan.recommended_budget > plan.daily_budget ? 'text-emerald-600' : 'text-rose-600'}>
                            ${plan.recommended_budget}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Button
                            size="sm"
                            variant="outline"
                            data-testid={`apply-budget-${plan.product_id}`}
                            onClick={() => updateProductBudget(plan.product_id, plan.recommended_budget)}
                            className="text-xs"
                          >
                            Apply
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default BudgetCalculator;
