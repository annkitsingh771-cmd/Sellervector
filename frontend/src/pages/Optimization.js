import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Zap, TrendingDown, TrendingUp, Pause, DollarSign,
  AlertTriangle, CheckCircle, ArrowRight, Sparkles, RefreshCw,
} from 'lucide-react';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';

const Optimization = () => {
  const [loading,     setLoading]     = useState(true);
  const [suggestions, setSuggestions] = useState([]);
  const [summary,     setSummary]     = useState({});
  const [selectedIds, setSelectedIds] = useState([]);
  const [applying,    setApplying]    = useState(false);

  useEffect(() => { fetchSuggestions(); }, []);

  const fetchSuggestions = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/optimization/suggestions');
      setSuggestions(res.data.suggestions || []);
      setSummary(res.data.summary || {});
    } catch (err) {
      toast.error('Failed to load optimizations');
    } finally {
      setLoading(false);
    }
  };

  const applySingle = async (id) => {
    try {
      await apiClient.post(`/optimization/apply/${id}`);
      setSuggestions(prev => prev.map(s => s.id === id ? { ...s, status: 'applied' } : s));
      toast.success('Optimization applied!');
    } catch { toast.error('Error applying optimization'); }
  };

  const applySelected = async () => {
    if (selectedIds.length === 0) { toast.error('Select at least one'); return; }
    setApplying(true);
    try {
      await apiClient.post('/optimization/apply-all', { suggestion_ids: selectedIds });
      setSuggestions(prev =>
        prev.map(s => selectedIds.includes(s.id) ? { ...s, status: 'applied' } : s)
      );
      setSelectedIds([]);
      toast.success(`Applied ${selectedIds.length} optimization(s)!`);
    } catch { toast.error('Error applying optimizations'); }
    finally   { setApplying(false); }
  };

  const toggleSelect = (id) =>
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  const selectAllPending = () =>
    setSelectedIds(suggestions.filter(s => s.status === 'pending').map(s => s.id));

  const typeIcon = (type) => {
    const icons = {
      bid_decrease: <TrendingDown className="text-rose-500" size={20} />,
      bid_increase: <TrendingUp className="text-emerald-500" size={20} />,
      pause_keyword: <Pause className="text-amber-500" size={20} />,
      budget_increase: <DollarSign className="text-indigo-500" size={20} />,
      negative_keyword: <AlertTriangle className="text-orange-500" size={20} />,
    };
    return icons[type] || <Zap className="text-indigo-500" size={20} />;
  };

  const priorityColor = (p) => ({
    high: 'bg-rose-100 text-rose-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-slate-100 text-slate-700',
  }[p] || 'bg-slate-100 text-slate-700');

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
    </div>
  );

  return (
    <div className="space-y-6" data-testid="optimization-page">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-slate-200 bg-gradient-to-br from-indigo-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-slate-500">Total Suggestions</p><p className="text-3xl font-bold text-indigo-600">{summary.total_suggestions ?? 0}</p></div>
              <div className="p-3 bg-indigo-100 rounded-lg"><Sparkles className="text-indigo-600" size={24} /></div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-gradient-to-br from-rose-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-slate-500">High Priority</p><p className="text-3xl font-bold text-rose-600">{summary.high_priority ?? 0}</p></div>
              <div className="p-3 bg-rose-100 rounded-lg"><AlertTriangle className="text-rose-600" size={24} /></div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-gradient-to-br from-emerald-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-slate-500">Potential Savings</p><p className="text-3xl font-bold text-emerald-600">${(summary.potential_savings || 0).toFixed(2)}</p></div>
              <div className="p-3 bg-emerald-100 rounded-lg"><TrendingDown className="text-emerald-600" size={24} /></div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-gradient-to-br from-amber-50 to-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-slate-500">Revenue Gain</p><p className="text-3xl font-bold text-amber-600">${(summary.potential_revenue_gain || 0).toFixed(2)}</p></div>
              <div className="p-3 bg-amber-100 rounded-lg"><TrendingUp className="text-amber-600" size={24} /></div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="outline" size="sm" onClick={selectAllPending}>Select All Pending</Button>
              <span className="text-sm text-slate-500">{selectedIds.length} selected</span>
              <Button variant="ghost" size="sm" onClick={fetchSuggestions} className="text-slate-500">
                <RefreshCw size={14} className="mr-1" /> Refresh
              </Button>
            </div>
            <Button onClick={applySelected} disabled={applying || selectedIds.length === 0}
                    className="bg-indigo-600 hover:bg-indigo-700" data-testid="apply-selected-button">
              {applying ? 'Applying...' : `Apply Selected (${selectedIds.length})`}
              <ArrowRight size={16} className="ml-2" />
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {suggestions.map(s => (
          <Card key={s.id}
                className={`border-slate-200 transition-all ${s.status === 'applied' ? 'opacity-60' : 'hover:shadow-md'}`}
                data-testid={`suggestion-${s.id}`}>
            <CardContent className="py-4">
              <div className="flex items-start gap-4">
                <div className="pt-1">
                  <Checkbox checked={selectedIds.includes(s.id)} onCheckedChange={() => toggleSelect(s.id)} disabled={s.status === 'applied'} />
                </div>
                <div className="p-2 bg-slate-50 rounded-lg">{typeIcon(s.type)}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-semibold text-slate-900">{s.title}</h3>
                    <Badge className={priorityColor(s.priority)}>{s.priority}</Badge>
                    {s.status === 'applied' && <Badge className="bg-emerald-100 text-emerald-700"><CheckCircle size={12} className="mr-1" />Applied</Badge>}
                  </div>
                  <p className="text-sm text-slate-600 mb-2">{s.description}</p>
                  <div className="flex items-center gap-4 text-sm flex-wrap">
                    <span className="text-slate-500">Campaign: <span className="text-slate-700">{s.campaign_name}</span></span>
                    {s.keyword && <span className="text-slate-500">Keyword: <span className="font-mono bg-slate-100 px-1 rounded">{s.keyword}</span></span>}
                  </div>
                  <div className="flex items-center gap-6 mt-3 flex-wrap">
                    {s.current_bid && s.suggested_bid && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-500">Bid:</span>
                        <span className="text-sm line-through text-slate-400">${s.current_bid}</span>
                        <ArrowRight size={14} className="text-slate-400" />
                        <span className="text-sm font-semibold text-indigo-600">${s.suggested_bid}</span>
                      </div>
                    )}
                    {s.current_acos && s.expected_acos && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-500">ACoS:</span>
                        <span className="text-sm line-through text-rose-400">{s.current_acos}%</span>
                        <ArrowRight size={14} className="text-slate-400" />
                        <span className="text-sm font-semibold text-emerald-600">{s.expected_acos}%</span>
                      </div>
                    )}
                    {(s.estimated_savings > 0) && <span className="text-sm text-emerald-600 font-medium">Save ${s.estimated_savings.toFixed(2)}</span>}
                    {(s.estimated_revenue_gain > 0) && <span className="text-sm text-amber-600 font-medium">+${s.estimated_revenue_gain.toFixed(2)} revenue</span>}
                    {(s.spend > 0 && s.sales === 0) && <span className="text-sm text-rose-600 font-medium">Wasted: ${s.spend.toFixed(2)}</span>}
                  </div>
                </div>
                <Button onClick={() => applySingle(s.id)} disabled={s.status === 'applied'}
                        variant={s.status === 'applied' ? 'outline' : 'default'}
                        className={s.status !== 'applied' ? 'bg-indigo-600 hover:bg-indigo-700' : ''}
                        data-testid={`apply-${s.id}`}>
                  {s.status === 'applied' ? <><CheckCircle size={16} className="mr-1" />Applied</> : <><Zap size={16} className="mr-1" />Apply</>}
                </Button>
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
            <p className="text-slate-500">No optimization suggestions right now.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Optimization;
