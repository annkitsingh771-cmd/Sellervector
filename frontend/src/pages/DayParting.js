import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Clock, TrendingUp, Sun, Moon, Zap, Calendar, BarChart3 } from 'lucide-react';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';

const DayParting = () => {
  const [loading, setLoading] = useState(true);
  const [hourlyData, setHourlyData] = useState([]);
  const [dailyData, setDailyData] = useState([]);
  const [peakHours, setPeakHours] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [schedule, setSchedule] = useState([]);

  useEffect(() => {
    fetchDayPartingData();
    fetchSchedule();
  }, []);

  const fetchDayPartingData = async () => {
    try {
      const response = await apiClient.get('/dayparting/analysis');
      setHourlyData(response.data.hourly_data);
      setDailyData(response.data.daily_data);
      setPeakHours(response.data.peak_hours);
      setRecommendations(response.data.recommendations);
    } catch (error) {
      console.error('Error fetching day parting data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSchedule = async () => {
    try {
      const response = await apiClient.get('/dayparting/schedule');
      setSchedule(response.data.schedule);
    } catch (error) {
      console.error('Error fetching schedule:', error);
    }
  };

  const updateSchedule = async (hour, bidAdjustment) => {
    const newSchedule = schedule.map(s => 
      s.hour === hour ? { ...s, bid_adjustment: bidAdjustment } : s
    );
    setSchedule(newSchedule);
    try {
      await apiClient.post('/dayparting/schedule', { schedule: newSchedule });
      toast.success('Schedule updated');
    } catch (error) {
      toast.error('Error updating schedule');
    }
  };

  const toggleScheduleHour = async (hour) => {
    const newSchedule = schedule.map(s => 
      s.hour === hour ? { ...s, enabled: !s.enabled } : s
    );
    setSchedule(newSchedule);
  };

  const getHourColor = (sales) => {
    const maxSales = Math.max(...hourlyData.map(h => h.sales));
    const intensity = sales / maxSales;
    if (intensity > 0.7) return 'bg-emerald-500';
    if (intensity > 0.4) return 'bg-emerald-300';
    if (intensity > 0.2) return 'bg-emerald-100';
    return 'bg-slate-100';
  };

  const applyRecommendedSchedule = async () => {
    const recommendedSchedule = schedule.map(s => ({
      ...s,
      bid_adjustment: peakHours.includes(s.hour) ? 20 : (s.hour < 6 ? -30 : 0),
      enabled: true
    }));
    setSchedule(recommendedSchedule);
    try {
      await apiClient.post('/dayparting/schedule', { schedule: recommendedSchedule });
      toast.success('Applied recommended schedule');
    } catch (error) {
      toast.error('Error applying schedule');
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
    <div className="space-y-6" data-testid="day-parting-page">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Peak Hours</p>
                <p className="text-2xl font-bold text-slate-900">{peakHours.length}</p>
              </div>
              <div className="p-3 bg-amber-100 rounded-lg">
                <Sun className="text-amber-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Best Hour</p>
                <p className="text-2xl font-bold text-slate-900">
                  {hourlyData.length > 0 ? `${hourlyData.reduce((a, b) => a.sales > b.sales ? a : b).hour}:00` : '-'}
                </p>
              </div>
              <div className="p-3 bg-emerald-100 rounded-lg">
                <TrendingUp className="text-emerald-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Low Traffic Hours</p>
                <p className="text-2xl font-bold text-slate-900">6</p>
                <p className="text-xs text-slate-400">12 AM - 6 AM</p>
              </div>
              <div className="p-3 bg-slate-100 rounded-lg">
                <Moon className="text-slate-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Best Day</p>
                <p className="text-2xl font-bold text-slate-900">
                  {dailyData.length > 0 ? dailyData.reduce((a, b) => a.sales > b.sales ? a : b).day : '-'}
                </p>
              </div>
              <div className="p-3 bg-indigo-100 rounded-lg">
                <Calendar className="text-indigo-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="heatmap" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="heatmap">
            <BarChart3 size={16} className="mr-2" />
            Hourly Heatmap
          </TabsTrigger>
          <TabsTrigger value="schedule">
            <Clock size={16} className="mr-2" />
            Bid Schedule
          </TabsTrigger>
          <TabsTrigger value="weekly">
            <Calendar size={16} className="mr-2" />
            Weekly Performance
          </TabsTrigger>
        </TabsList>

        {/* Hourly Heatmap */}
        <TabsContent value="heatmap">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="text-indigo-600" size={20} />
                Hourly Performance Heatmap
              </CardTitle>
              <CardDescription>
                Sales performance by hour of day. Darker colors indicate higher sales.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-12 gap-2 mb-6">
                {hourlyData.slice(0, 24).map((hour) => (
                  <div
                    key={hour.hour}
                    className={`relative p-3 rounded-lg text-center cursor-pointer transition-all hover:scale-105 ${getHourColor(hour.sales)}`}
                    data-testid={`hour-${hour.hour}`}
                  >
                    <p className="text-xs font-medium text-slate-700">{hour.hour_label}</p>
                    <p className="text-sm font-bold mt-1">${hour.sales.toFixed(0)}</p>
                    {hour.is_peak && (
                      <Badge className="absolute -top-2 -right-2 bg-amber-500 text-white text-xs px-1">
                        <Zap size={10} />
                      </Badge>
                    )}
                  </div>
                ))}
              </div>

              {/* Legend */}
              <div className="flex items-center gap-4 justify-center text-sm text-slate-500">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-slate-100 rounded"></div>
                  <span>Low</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-emerald-100 rounded"></div>
                  <span>Medium</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-emerald-300 rounded"></div>
                  <span>High</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-emerald-500 rounded"></div>
                  <span>Peak</span>
                </div>
              </div>

              {/* Detailed Table */}
              <div className="mt-6 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-2 px-3">Hour</th>
                      <th className="text-right py-2 px-3">Sales</th>
                      <th className="text-right py-2 px-3">Orders</th>
                      <th className="text-right py-2 px-3">Clicks</th>
                      <th className="text-right py-2 px-3">Spend</th>
                      <th className="text-right py-2 px-3">ACOS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hourlyData.map((hour) => (
                      <tr key={hour.hour} className={`border-b border-slate-100 ${hour.is_peak ? 'bg-amber-50' : ''}`}>
                        <td className="py-2 px-3 font-medium">
                          {hour.hour_label}
                          {hour.is_peak && <Badge className="ml-2 bg-amber-500 text-xs">Peak</Badge>}
                        </td>
                        <td className="py-2 px-3 text-right">${hour.sales.toFixed(2)}</td>
                        <td className="py-2 px-3 text-right">{hour.orders}</td>
                        <td className="py-2 px-3 text-right">{hour.clicks}</td>
                        <td className="py-2 px-3 text-right">${hour.spend.toFixed(2)}</td>
                        <td className="py-2 px-3 text-right">{hour.acos}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Bid Schedule */}
        <TabsContent value="schedule">
          <Card className="border-slate-200">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="text-indigo-600" size={20} />
                    Day Parting Bid Schedule
                  </CardTitle>
                  <CardDescription>
                    Adjust bid multipliers for each hour
                  </CardDescription>
                </div>
                <Button onClick={applyRecommendedSchedule} className="bg-indigo-600 hover:bg-indigo-700">
                  Apply Recommended
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {schedule.map((slot) => (
                  <div
                    key={slot.hour}
                    className={`p-3 rounded-lg border ${slot.enabled ? 'border-slate-200 bg-white' : 'border-slate-100 bg-slate-50'}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">{slot.hour_label}</span>
                      <Switch
                        checked={slot.enabled}
                        onCheckedChange={() => toggleScheduleHour(slot.hour)}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">Bid Adj:</span>
                      <select
                        value={slot.bid_adjustment}
                        onChange={(e) => updateSchedule(slot.hour, parseInt(e.target.value))}
                        disabled={!slot.enabled}
                        className="flex-1 text-sm border rounded px-2 py-1"
                      >
                        <option value={-50}>-50%</option>
                        <option value={-30}>-30%</option>
                        <option value={-20}>-20%</option>
                        <option value={0}>0%</option>
                        <option value={20}>+20%</option>
                        <option value={30}>+30%</option>
                        <option value={50}>+50%</option>
                      </select>
                    </div>
                  </div>
                ))}
              </div>

              {/* Recommendations */}
              <div className="mt-6 p-4 bg-amber-50 rounded-lg">
                <h4 className="font-semibold text-amber-800 mb-2">AI Recommendations</h4>
                <ul className="space-y-2">
                  {recommendations.map((rec, idx) => (
                    <li key={idx} className="text-sm text-amber-700 flex items-start gap-2">
                      <Zap size={14} className="mt-0.5 flex-shrink-0" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Weekly Performance */}
        <TabsContent value="weekly">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="text-indigo-600" size={20} />
                Weekly Performance by Day
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-7 gap-4">
                {dailyData.map((day) => (
                  <div
                    key={day.day}
                    className={`p-4 rounded-lg text-center ${day.is_high_performance ? 'bg-emerald-50 border border-emerald-200' : 'bg-slate-50'}`}
                  >
                    <p className="font-semibold text-slate-700">{day.day.slice(0, 3)}</p>
                    <p className="text-xl font-bold mt-2 text-slate-900">${day.sales.toFixed(0)}</p>
                    <p className="text-xs text-slate-500 mt-1">{day.orders} orders</p>
                    <p className={`text-xs mt-2 ${day.acos > 30 ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {day.acos}% ACOS
                    </p>
                    {day.is_high_performance && (
                      <Badge className="mt-2 bg-emerald-500 text-xs">High Perf</Badge>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DayParting;
