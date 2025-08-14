import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from '@mui/material';
import {
  Warning as WarningIcon,
  NewReleases as UrgentIcon,
  Schedule as OverdueIcon,
  CheckCircle as CompletedIcon,
  Visibility as ViewIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Block as BlockIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { dashboardApi, reportsApi, Alert as AlertType } from '../services/api';

interface StatsCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: 'primary' | 'error' | 'warning' | 'success';
  onClick?: () => void;
}

function StatsCard({ title, value, icon, color, onClick }: StatsCardProps) {
  return (
    <Card 
      sx={{ 
        height: '100%', 
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { boxShadow: 4 } : {}
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div" color={`${color}.main`}>
              {value}
            </Typography>
          </Box>
          <Box sx={{ color: `${color}.main` }}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

function PriorityBadge({ priority }: { priority?: string }) {
  const getColor = () => {
    switch (priority) {
      case 'P1-Immediate': return 'error';
      case 'P2-Within 48h': return 'warning';
      case 'P3-Within 1 week': return 'info';
      default: return 'default';
    }
  };

  const getIcon = () => {
    switch (priority) {
      case 'P1-Immediate': return '🔴';
      case 'P2-Within 48h': return '🟠';
      case 'P3-Within 1 week': return '🟡';
      default: return '⚪';
    }
  };

  if (!priority) return null;

  return (
    <Chip
      label={`${getIcon()} ${priority}`}
      color={getColor()}
      size="small"
      sx={{ fontWeight: 'bold' }}
    />
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboardData = async () => {
    try {
      setError(null);
      const data = await dashboardApi.getStats();
      setStats(data);
    } catch (err: any) {
      setError('Failed to load dashboard data');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchDashboardData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  const handleExportExcel = async () => {
    try {
      await reportsApi.exportExcel();
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
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  const urgentAlerts = stats?.recent_alerts?.filter(
    (alert: AlertType) => alert.priority === 'P1-Immediate' || alert.priority === 'P2-Within 48h'
  ) || [];

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        <Box>
          <IconButton onClick={handleRefresh} disabled={refreshing}>
            <RefreshIcon />
          </IconButton>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExportExcel}
            sx={{ ml: 1 }}
          >
            Export Excel
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            title="New Alerts"
            value={stats?.new_alerts || 0}
            icon={<WarningIcon fontSize="large" />}
            color="primary"
            onClick={() => navigate('/alerts?tab=active')}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            title="Urgent Alerts"
            value={stats?.urgent_alerts || 0}
            icon={<UrgentIcon fontSize="large" />}
            color="error"
            onClick={() => navigate('/alerts?priority=urgent')}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            title="Overdue"
            value={stats?.overdue_alerts || 0}
            icon={<OverdueIcon fontSize="large" />}
            color="warning"
            onClick={() => navigate('/alerts?status=overdue')}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            title="Completed"
            value={stats?.completed_alerts || 0}
            icon={<CompletedIcon fontSize="large" />}
            color="success"
            onClick={() => navigate('/alerts?tab=completed')}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <StatsCard
            title="Not Relevant"
            value={stats?.not_relevant_alerts || 0}
            icon={<BlockIcon fontSize="large" />}
            color="default"
            onClick={() => navigate('/alerts?tab=notRelevant')}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Priority Alerts */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Priority Alerts (Auto-refresh: 5 min)
            </Typography>
            {urgentAlerts.length === 0 ? (
              <Typography color="textSecondary">No urgent alerts</Typography>
            ) : (
              <List>
                {urgentAlerts.slice(0, 5).map((alert: AlertType) => (
                  <ListItem
                    key={alert.id}
                    sx={{
                      borderLeft: 4,
                      borderColor: alert.priority === 'P1-Immediate' ? 'error.main' : 'warning.main',
                      mb: 1,
                      bgcolor: 'background.paper',
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <PriorityBadge priority={alert.priority} />
                          <Typography variant="subtitle1">
                            {alert.govuk_reference || alert.alert_id}
                          </Typography>
                          {alert.published_date && (
                            <Typography variant="caption" color="textSecondary">
                              Due: {format(new Date(alert.published_date), 'dd MMM')}
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="textSecondary">
                            {alert.product_name || alert.title}
                          </Typography>
                          {alert.patients_affected_count && (
                            <Typography variant="caption">
                              {alert.patients_affected_count} patients affected
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        aria-label="view"
                        onClick={() => navigate(`/alerts/${alert.id}`)}
                      >
                        <ViewIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Quick Stats & Recent Activity */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Quick Stats
            </Typography>
            <Box>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Total Alerts</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.total_alerts || 0}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">In Progress</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.alerts_by_status?.['In Progress'] || 0}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Under Review</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.alerts_by_status?.['Under Review'] || 0}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2">Action Required</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.alerts_by_status?.['Action Required'] || 0}
                </Typography>
              </Box>
            </Box>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Alert Categories
            </Typography>
            {(() => {
              // Define all 8 alert categories
              const allCategories = [
                { name: 'Medicines Recall', icon: '💊', color: '#ff9800' },
                { name: 'National Patient Safety Alert', icon: '⚠️', color: '#f44336' },
                { name: 'Medical Device Alert', icon: '🔧', color: '#2196f3' },
                { name: 'MHRA Safety Roundup', icon: '📋', color: '#9c27b0' },
                { name: 'Drug Safety Update', icon: '💉', color: '#3f51b5' },
                { name: 'Medicine Supply Alert', icon: '📦', color: '#00bcd4' },
                { name: 'Serious Shortage Protocol', icon: '🚨', color: '#ff5722' },
                { name: 'CAS Distribution', icon: '📢', color: '#607d8b' }
              ];
              
              // Get counts from stats, defaulting to 0
              const typeCounts = stats?.alerts_by_type || {};
              
              return allCategories.map(category => {
                const count = typeCounts[category.name] || 0;
                const handleCategoryClick = () => {
                  if (count > 0) {
                    // Navigate to alerts page with category filter
                    navigate(`/alerts?category=${encodeURIComponent(category.name)}`);
                  }
                };
                
                return (
                  <Box 
                    key={category.name} 
                    display="flex" 
                    justifyContent="space-between" 
                    alignItems="center"
                    mb={1}
                    onClick={handleCategoryClick}
                    sx={{ 
                      opacity: count === 0 ? 0.6 : 1,
                      cursor: count > 0 ? 'pointer' : 'default',
                      '&:hover': count > 0 ? { 
                        bgcolor: 'action.hover',
                        transform: 'translateX(4px)',
                        transition: 'all 0.2s'
                      } : {},
                      p: 1,
                      borderRadius: 1,
                      transition: 'all 0.2s'
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2" fontSize="1.2em">{category.icon}</Typography>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          color: count > 0 ? category.color : 'text.secondary',
                          fontWeight: count > 0 ? 500 : 400
                        }}
                      >
                        {category.name}
                      </Typography>
                    </Box>
                    <Chip 
                      label={count} 
                      size="small" 
                      color={count > 0 ? "primary" : "default"}
                      variant={count > 0 ? "filled" : "outlined"}
                      sx={{ fontWeight: 'bold' }}
                    />
                  </Box>
                );
              });
            })()}
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Click a category to view alerts
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;