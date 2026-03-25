import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Zap, TrendingDown, TrendingUp, Pause, DollarSign, AlertTriangle, CheckCircle, ArrowRight, Sparkles } from 'lucide-react';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';

const Optimization = () => {
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState([]);
  const [summary, setSummary] = useState({});
  const [selectedIds, setSelectedIds] = useState([]);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    fetchSuggestions();
  }, []);

  const fetchSuggestions = async () => {
    try {
      const response = await apiClient.get('/optimization/suggestions');
      setSuggestions(response.data.suggestions);
      setSummary(response.data.summary);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  const applySingleOptimization = async (suggestionId) => {
    try {
      await apiClient.post(`/optimization/apply/${suggestionId}`);
      setSuggestions(prev => prev.map(s => 
        s.id === suggestionId ? { ...s, status: 'applied' } : s
      ));
      toast.success('Optimization applied successfully!');
    } catch (error) {
      toast.error('Error applying optimization');
    }
  };

  const applySelectedOptimizations = async () => {
    if (selectedIds.length === 0) {
      toast.error('Please select optimizations to apply');
      return;
    }
    setApplying(true);
    try {
      await apiClient.post('/optimization/apply-all', { suggestion_ids: selectedIds });
      setSuggestions(prev => prev.map(s => 
        selectedIds.includes(s.id) ? { ...s, status: 'applied' } : s
      ));
      setSelectedIds([]);
      toast.success(`Applied ${selectedIds.length} optimizations!`);
    } catch (error) {
      toast.error('Error applying optimizations');
    } finally {
      setApplying(false);
    }
  };

  const toggleSelection = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const selectAllPending = () => {
    const pendingIds = suggestions.filter(s => s.status === 'pending').map(s => s.id);
    setSelectedIds(pendingIds);
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'bid_decrease': return <TrendingDown className="text-rose-500" size={20} />;
      case 'bid_increase': return <TrendingUp className="text-emerald-500" size={20} />;
      case 'pause_keyword': return <Pause className="text-amber-500" size={20} />;
      case 'budget_increase': return <DollarSign className="text-indigo-500" size={20} />;
      case 'negative_keyword': return <AlertTriangle className="text-orange-500" size={20} />;
      default: return <Zap className="text-indigo-500" size={20} />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'bg-rose-100 text-rose-700';
      case 'medium': return 'bg-amber-100 text-amber-700';
      case 'low': return 'bg-slate-100 text-slate-700';
      default: return 'bg-slate-100 text-slate-700';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="optimization-page">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-slate-200 bg-gradient-to-br from-indigo-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Total Suggestions</p>
                <p className="text-3xl font-bold text-indigo-600">{summary.total_suggestions}</p>
              </div>
              <div className="p-3 bg-indigo-100 rounded-lg">
                <Sparkles className="text-indigo-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-gradient-to-br from-rose-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">High Priority</p>
                <p className="text-3xl font-bold text-rose-600">{summary.high_priority}</p>
              </div>
              <div className="p-3 bg-rose-100 rounded-lg">
                <AlertTriangle className="text-rose-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-gradient-to-br from-emerald-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Potential Savings</p>
                <p className="text-3xl font-bold text-emerald-600">${summary.potential_savings?.toFixed(2)}</p>
              </div>
              <div className="p-3 bg-emerald-100 rounded-lg">
                <TrendingDown className="text-emerald-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-gradient-to-br from-amber-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Revenue Gain</p>
                <p className="text-3xl font-bold text-amber-600">${summary.potential_revenue_gain?.toFixed(2)}</p>
              </div>
              <div className="p-3 bg-amber-100 rounded-lg">
                <TrendingUp className="text-amber-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Bar */}
      <Card className="border-slate-200">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="outline" size="sm" onClick={selectAllPending}>
                Select All Pending
              </Button>
              <span className="text-sm text-slate-500">
                {selectedIds.length} selected
              </span>
            </div>
            <Button 
              onClick={applySelectedOptimizations}
              disabled={applying || selectedIds.length === 0}
              className="bg-indigo-600 hover:bg-indigo-700"
              data-testid="apply-selected-button"
            >
              {applying ? 'Applying...' : `Apply Selected (${selectedIds.length})`}
              <ArrowRight size={16} className="ml-2" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Suggestions List */}
      <div className="space-y-4">
        {suggestions.map((suggestion) => (
          <Card 
            key={suggestion.id} 
            className={`border-slate-200 transition-all ${suggestion.status === 'applied' ? 'opacity-60' : 'hover:shadow-md'}`}
            data-testid={`suggestion-${suggestion.id}`}
          >
            <CardContent className="py-4">
              <div className="flex items-start gap-4">
                {/* Checkbox */}
                <div className="pt-1">
                  <Checkbox
                    checked={selectedIds.includes(suggestion.id)}
                    onCheckedChange={() => toggleSelection(suggestion.id)}
                    disabled={suggestion.status === 'applied'}
                  />
                </div>

                {/* Icon */}
                <div className="p-2 bg-slate-50 rounded-lg">
                  {getTypeIcon(suggestion.type)}
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-slate-900">{suggestion.title}</h3>
                    <Badge className={getPriorityColor(suggestion.priority)}>
                      {suggestion.priority}
                    </Badge>
                    {suggestion.status === 'applied' && (
                      <Badge className="bg-emerald-100 text-emerald-700">
                        <CheckCircle size={12} className="mr-1" />
                        Applied
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 mb-2">{suggestion.description}</p>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-slate-500">Campaign: <span className="text-slate-700">{suggestion.campaign_name}</span></span>
                    {suggestion.keyword && (
                      <span className="text-slate-500">Keyword: <span className="font-mono bg-slate-100 px-1 rounded">{suggestion.keyword}</span></span>
                    )}
                  </div>

                  {/* Metrics */}
                  <div className="flex items-center gap-6 mt-3">
                    {suggestion.current_bid && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-500">Bid:</span>
                        <span className="text-sm line-through text-slate-400">${suggestion.current_bid}</span>
                        <ArrowRight size={14} className="text-slate-400" />
                        <span className="text-sm font-semibold text-indigo-600">${suggestion.suggested_bid}</span>
                      </div>
                    )}
                    {suggestion.current_acos && suggestion.expected_acos && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-500">ACOS:</span>
                        <span className="text-sm line-through text-rose-400">{suggestion.current_acos}%</span>
                        <ArrowRight size={14} className="text-slate-400" />
                        <span className="text-sm font-semibold text-emerald-600">{suggestion.expected_acos}%</span>
                      </div>
                    )}
                    {suggestion.estimated_savings && (
                      <div className="text-sm text-emerald-600 font-medium">
                        Save ${suggestion.estimated_savings.toFixed(2)}
                      </div>
                    )}
                    {suggestion.estimated_revenue_gain && (
                      <div className="text-sm text-amber-600 font-medium">
                        +${suggestion.estimated_revenue_gain.toFixed(2)} revenue
                      </div>
                    )}
                    {suggestion.spend && suggestion.sales === 0 && (
                      <div className="text-sm text-rose-600 font-medium">
                        Wasted: ${suggestion.spend.toFixed(2)}
                      </div>
                    )}
                  </div>
                </div>

                {/* Action Button */}
                <div>
                  <Button
                    onClick={() => applySingleOptimization(suggestion.id)}
                    disabled={suggestion.status === 'applied'}
                    variant={suggestion.status === 'applied' ? 'outline' : 'default'}
                    className={suggestion.status !== 'applied' ? 'bg-indigo-600 hover:bg-indigo-700' : ''}
                    data-testid={`apply-${suggestion.id}`}
                  >
                    {suggestion.status === 'applied' ? (
                      <>
                        <CheckCircle size={16} className="mr-1" />
                        Applied
                      </>
                    ) : (
                      <>
                        <Zap size={16} className="mr-1" />
                        Apply
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {suggestions.length === 0 && (
        <Card className="border-slate-200">
          <CardContent className="py-12 text-center">
            <CheckCircle size={48} className="mx-auto text-emerald-500 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">All Optimized!</h3>
            <p className="text-slate-500">No optimization suggestions at this time. Check back later.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Optimization;
