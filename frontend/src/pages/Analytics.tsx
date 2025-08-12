import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
} from '@mui/material';
import {
  PieChart,
  Pie,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Download as DownloadIcon } from '@mui/icons-material';
import { dashboardApi, reportsApi } from '../services/api';

const COLORS = {
  Critical: '#D5281B',
  High: '#FA9200',
  Medium: '#FFD700',
  Low: '#768692',
  Completed: '#00703C',
  'In Progress': '#0072CE',
  New: '#D5281B',
  Closed: '#768692',
};

function Analytics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [monthlyData, setMonthlyData] = useState<any>(null);
  const [annualData, setAnnualData] = useState<any>(null);

  useEffect(() => {
    fetchData();
  }, [selectedYear, selectedMonth]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [dashStats, monthly, annual] = await Promise.all([
        dashboardApi.getStats(),
        reportsApi.getMonthlySummary(selectedYear, selectedMonth),
        reportsApi.getAnnualSummary(selectedYear),
      ]);
      
      setStats(dashStats);
      setMonthlyData(monthly);
      setAnnualData(annual);
    } catch (err: any) {
      setError('Failed to load analytics data');
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportReport = async () => {
    try {
      const startDate = `${selectedYear}-${String(selectedMonth).padStart(2, '0')}-01`;
      const endDate = `${selectedYear}-${String(selectedMonth).padStart(2, '0')}-31`;
      await reportsApi.exportExcel(startDate, endDate);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        {error}
      </Alert>
    );
  }

  // Prepare data for charts
  const statusData = Object.entries(stats?.alerts_by_status || {}).map(([status, count]) => ({
    name: status,
    value: count as number,
  }));

  const priorityData = Object.entries(stats?.alerts_by_priority || {}).map(([priority, count]) => ({
    name: priority || 'None',
    value: count as number,
  }));

  const typeData = Object.entries(stats?.alerts_by_type || {}).map(([type, count]) => ({
    name: type || 'Unknown',
    value: count as number,
  })).slice(0, 5); // Top 5 types

  const monthlyTrendData = annualData?.monthly_breakdown?.map((month: any) => ({
    month: `Month ${month.month}`,
    Total: month.total,
    Relevant: month.relevant,
    Completed: month.completed,
  })) || [];

  const complianceScore = monthlyData?.completion_rate || 0;
  const avgResponseTime = monthlyData?.avg_response_time_hours || 0;
  const avgCompletionTime = monthlyData?.avg_completion_time_hours || 0;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Compliance Analytics
        </Typography>
        
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Year</InputLabel>
            <Select
              value={selectedYear}
              label="Year"
              onChange={(e) => setSelectedYear(e.target.value as number)}
            >
              {[2023, 2024, 2025].map(year => (
                <MenuItem key={year} value={year}>{year}</MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Month</InputLabel>
            <Select
              value={selectedMonth}
              label="Month"
              onChange={(e) => setSelectedMonth(e.target.value as number)}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map(month => (
                <MenuItem key={month} value={month}>
                  {new Date(2000, month - 1).toLocaleString('default', { month: 'short' })}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            onClick={handleExportReport}
          >
            Export Report
          </Button>
        </Box>
      </Box>

      {/* CQC Compliance Metrics */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          CQC Compliance Metrics
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Response Time Compliance
                </Typography>
                <Typography variant="h4" color={complianceScore >= 90 ? 'success.main' : 'warning.main'}>
                  {complianceScore.toFixed(1)}%
                </Typography>
                <Typography variant="caption">
                  Target: 95%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Avg Response Time
                </Typography>
                <Typography variant="h4">
                  {avgResponseTime.toFixed(1)}h
                </Typography>
                <Typography variant="caption">
                  Target: &lt;4h
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Avg Completion Time
                </Typography>
                <Typography variant="h4">
                  {avgCompletionTime.toFixed(1)}h
                </Typography>
                <Typography variant="caption">
                  Target: &lt;48h
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Overdue Alerts
                </Typography>
                <Typography variant="h4" color={stats?.overdue_alerts > 0 ? 'error.main' : 'success.main'}>
                  {stats?.overdue_alerts || 0}
                </Typography>
                <Typography variant="caption">
                  Target: 0
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>

      {/* Charts */}
      <Grid container spacing={3}>
        {/* Alerts by Status */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Alerts by Status
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name as keyof typeof COLORS] || '#8884d8'} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Alerts by Priority */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Alerts by Priority
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={priorityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#005EB8" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Monthly Trend */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Monthly Trend - {selectedYear}
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthlyTrendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="Total" stroke="#005EB8" />
                <Line type="monotone" dataKey="Relevant" stroke="#FA9200" />
                <Line type="monotone" dataKey="Completed" stroke="#00703C" />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Alert Types */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Top Alert Types
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={typeData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={150} />
                <Tooltip />
                <Bar dataKey="value" fill="#0072CE" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Summary Statistics */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          {new Date(selectedYear, selectedMonth - 1).toLocaleString('default', { month: 'long', year: 'numeric' })} Summary
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <Typography variant="body2" color="textSecondary">
              Total Alerts
            </Typography>
            <Typography variant="h6">
              {monthlyData?.total_alerts || 0}
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="body2" color="textSecondary">
              Relevant Alerts
            </Typography>
            <Typography variant="h6">
              {monthlyData?.relevant_alerts || 0}
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="body2" color="textSecondary">
              Completed Alerts
            </Typography>
            <Typography variant="h6">
              {monthlyData?.completed_alerts || 0}
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="body2" color="textSecondary">
              Completion Rate
            </Typography>
            <Typography variant="h6">
              {monthlyData?.completion_rate?.toFixed(1) || 0}%
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}

export default Analytics;