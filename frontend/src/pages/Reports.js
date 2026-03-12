import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/utils/api';
import { FileText, Download } from 'lucide-react';
import { toast } from 'sonner';

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await apiClient.get('/reports');
      setReports(response.data.reports);
    } catch (error) {
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (reportId) => {
    toast.success('Report download started (Demo)');
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>Business Reports</h2>
          <p className="text-slate-600 text-sm mt-1">Download and analyze your business performance reports</p>
        </div>
        <Button
          data-testid="generate-report-button"
          className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
        >
          <FileText size={16} className="mr-2" />
          Generate New Report
        </Button>
      </div>

      {/* Reports List */}
      <div className="grid grid-cols-1 gap-4">
        {reports.map((report) => (
          <Card key={report.id} className="bg-white border border-slate-200 shadow-sm rounded-sm hover:border-indigo-300 transition-colors" data-testid={`report-card-${report.id}`}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-indigo-50 rounded-sm flex items-center justify-center">
                    <FileText size={24} className="text-indigo-700" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-slate-900 mb-1" style={{ fontFamily: 'Chivo, sans-serif' }}>{report.report_name}</h3>
                    <div className="flex items-center gap-3 text-sm text-slate-600">
                      <span className="capitalize">{report.report_type} Report</span>
                      <span>•</span>
                      <span>{report.date_range}</span>
                      <span>•</span>
                      <span>{new Date(report.generated_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge className="bg-emerald-50 text-emerald-600 border-emerald-200 rounded-sm text-xs uppercase tracking-wider font-bold">
                    {report.status}
                  </Badge>
                  <Button
                    onClick={() => handleDownload(report.id)}
                    data-testid={`download-report-${report.id}`}
                    className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-sm font-medium"
                  >
                    <Download size={16} className="mr-2" />
                    Download
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Info */}
      <Card className="bg-indigo-50 border border-indigo-200 shadow-sm rounded-sm">
        <CardContent className="p-5">
          <div className="flex items-start gap-3">
            <FileText size={20} className="text-indigo-700 mt-0.5" />
            <div>
              <h4 className="font-semibold text-indigo-900 mb-1">Report Formats</h4>
              <p className="text-sm text-indigo-700">
                All reports are available in CSV, Excel, and PDF formats for easy analysis and sharing.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Reports;
