import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Chip,
  Typography,
  Button,
  CircularProgress,
  Alert,
  InputAdornment,
  Card,
  CardContent,
  useMediaQuery,
  useTheme,
  Tabs,
  Tab,
  Badge,
} from '@mui/material';
import {
  Search as SearchIcon,
  Visibility as ViewIcon,
  Timer as TimerIcon,
  Note as NoteIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
  NewReleases as NewIcon,
  Assignment as ReviewIcon,
  CheckCircle as CompletedIcon,
  Cancel as NotRelevantIcon,
  Launch as LaunchIcon,
  ThumbDown as ThumbDownIcon,
} from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { format } from 'date-fns';
import { alertsApi, Alert as AlertType } from '../services/api';

function SeverityChip({ severity }: { severity?: string }) {
  const getColor = () => {
    switch (severity) {
      case 'Critical': return 'error';
      case 'High': return 'warning';
      case 'Medium': return 'info';
      default: return 'default';
    }
  };

  if (!severity) return null;

  return <Chip label={severity} color={getColor()} size="small" />;
}

function StatusChip({ status }: { status: string }) {
  const getColor = () => {
    switch (status) {
      case 'New': return 'error';
      case 'Under Review': return 'warning';
      case 'In Progress': return 'info';
      case 'Completed': return 'success';
      case 'Closed': return 'default';
      default: return 'default';
    }
  };

  return <Chip label={status} color={getColor()} size="small" />;
}

function CategoryChip({ category }: { category?: string }) {
  const getIcon = () => {
    if (!category) return null;
    
    switch (category) {
      case 'Medicines Recall': return '💊';
      case 'National Patient Safety Alert': return '⚠️';
      case 'Medical Device Alert': return '🔧';
      case 'MHRA Safety Roundup': return '📋';
      case 'Drug Safety Update': return '💉';
      case 'Medicine Supply Alert': return '📦';
      case 'Serious Shortage Protocol': return '🚨';
      case 'CAS Distribution': return '📢';
      default: return '📄';
    }
  };
  
  const getColor = () => {
    if (!category) return 'default';
    
    switch (category) {
      case 'National Patient Safety Alert': return 'error';
      case 'Medicines Recall': return 'warning';
      case 'Medical Device Alert': return 'info';
      case 'Serious Shortage Protocol': return 'error';
      default: return 'default';
    }
  };
  
  if (!category) return null;
  
  return (
    <Chip 
      label={`${getIcon()} ${category}`} 
      color={getColor() as any} 
      size="small" 
      variant="outlined"
    />
  );
}

function AlertsList() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingNotRelevant, setMarkingNotRelevant] = useState<number | null>(null);
  
  // Tab state
  const [currentTab, setCurrentTab] = useState(searchParams.get('tab') || 'active');
  
  // Filters
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || '');
  const [severityFilter, setSeverityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get('category') || '');
  
  // Tab counts for badges
  const [tabCounts, setTabCounts] = useState({
    active: 0,
    review: 0,
    completed: 0,
    notRelevant: 0,
  });

  const getStatusForTab = (tab: string) => {
    switch (tab) {
      case 'active':
        return 'New,Under Review,Action Required,In Progress';
      case 'review':
        return 'Under Review,In Progress';
      case 'completed':
        return 'Completed';
      case 'notRelevant':
        return 'Closed';
      default:
        return undefined;
    }
  };

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get status filter based on current tab
      const tabStatus = getStatusForTab(currentTab);
      
      const response = await alertsApi.getAlerts({
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        search: search || undefined,
        status: currentTab !== 'all' ? tabStatus : statusFilter || undefined,
        priority: priorityFilter || undefined,
        severity: severityFilter || undefined,
        category: categoryFilter || undefined,
      });
      
      setAlerts(response.items);
      setTotal(response.total);
    } catch (err: any) {
      setError('Failed to load alerts');
      console.error('Alerts error:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchTabCounts = async () => {
    try {
      // Fetch counts for each tab
      const [activeResp, reviewResp, completedResp, notRelevantResp] = await Promise.all([
        alertsApi.getAlerts({ limit: 1, status: 'New,Under Review,Action Required,In Progress' }),
        alertsApi.getAlerts({ limit: 1, status: 'Under Review,In Progress' }),
        alertsApi.getAlerts({ limit: 1, status: 'Completed' }),
        alertsApi.getAlerts({ limit: 1, status: 'Closed' }),
      ]);
      
      setTabCounts({
        active: activeResp.total,
        review: reviewResp.total,
        completed: completedResp.total,
        notRelevant: notRelevantResp.total,
      });
    } catch (err) {
      console.error('Failed to fetch tab counts:', err);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [page, rowsPerPage, statusFilter, priorityFilter, severityFilter, currentTab, categoryFilter]);
  
  useEffect(() => {
    fetchTabCounts();
  }, []);

  const handleSearch = () => {
    setPage(0);
    fetchAlerts();
  };

  const handleClearFilters = () => {
    setSearch('');
    setStatusFilter('');
    setPriorityFilter('');
    setSeverityFilter('');
    setCategoryFilter('');
    setPage(0);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  if (loading && alerts.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setCurrentTab(newValue);
    setPage(0);
    setStatusFilter(''); // Clear manual status filter when changing tabs
  };

  const handleMarkNotRelevant = async (alertId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Mark this alert as not relevant?')) {
      try {
        setMarkingNotRelevant(alertId);
        await alertsApi.markNotRelevant(alertId);
        await fetchAlerts();
        await fetchTabCounts();
      } catch (err) {
        console.error('Failed to mark as not relevant:', err);
      } finally {
        setMarkingNotRelevant(null);
      }
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        All Alerts
      </Typography>

      {/* Tabs for different alert categories */}
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant={isMobile ? "scrollable" : "standard"}
          scrollButtons={isMobile ? "auto" : false}
        >
          <Tab 
            value="active" 
            label={
              <Badge badgeContent={tabCounts.active} color="error">
                Active
              </Badge>
            }
            icon={<NewIcon />} 
            iconPosition="start"
          />
          <Tab 
            value="review" 
            label={
              <Badge badgeContent={tabCounts.review} color="warning">
                Under Review
              </Badge>
            }
            icon={<ReviewIcon />} 
            iconPosition="start"
          />
          <Tab 
            value="completed" 
            label={
              <Badge badgeContent={tabCounts.completed} color="success">
                Completed
              </Badge>
            }
            icon={<CompletedIcon />} 
            iconPosition="start"
          />
          <Tab 
            value="notRelevant" 
            label={
              <Badge badgeContent={tabCounts.notRelevant} color="default">
                Not Relevant
              </Badge>
            }
            icon={<NotRelevantIcon />} 
            iconPosition="start"
          />
          <Tab 
            value="all" 
            label="All Alerts"
          />
        </Tabs>
      </Paper>

      {/* Show category filter if navigated from dashboard */}
      {categoryFilter && (
        <Alert 
          severity="info" 
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => setCategoryFilter('')}>
              Clear Filter
            </Button>
          }
        >
          Showing alerts for category: <strong>{categoryFilter}</strong>
        </Alert>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box display="flex" flexWrap="wrap" gap={2} alignItems="center">
          <TextField
            placeholder="Search alerts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            size="small"
            sx={{ minWidth: 200 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
          
          {/* Only show status filter in "All" tab */}
          {currentTab === 'all' && (
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="New">New</MenuItem>
                <MenuItem value="Under Review">Under Review</MenuItem>
                <MenuItem value="Action Required">Action Required</MenuItem>
                <MenuItem value="In Progress">In Progress</MenuItem>
                <MenuItem value="Completed">Completed</MenuItem>
                <MenuItem value="Closed">Closed</MenuItem>
              </Select>
            </FormControl>
          )}
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Priority</InputLabel>
            <Select
              value={priorityFilter}
              label="Priority"
              onChange={(e) => setPriorityFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="P1-Immediate">P1-Immediate</MenuItem>
              <MenuItem value="P2-Within 48h">P2-Within 48h</MenuItem>
              <MenuItem value="P3-Within 1 week">P3-Within 1 week</MenuItem>
              <MenuItem value="P4-Routine">P4-Routine</MenuItem>
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={severityFilter}
              label="Severity"
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="Critical">Critical</MenuItem>
              <MenuItem value="High">High</MenuItem>
              <MenuItem value="Medium">Medium</MenuItem>
              <MenuItem value="Low">Low</MenuItem>
            </Select>
          </FormControl>
          
          <Button variant="contained" onClick={handleSearch} startIcon={<SearchIcon />}>
            Search
          </Button>
          
          <Button variant="outlined" onClick={handleClearFilters} startIcon={<ClearIcon />}>
            Clear
          </Button>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Alerts Table/Cards */}
      {isMobile ? (
        // Mobile view - Cards
        <Box>
          {alerts.map((alert) => (
            <Card key={alert.id} sx={{ mb: 2 }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={1}>
                  <Typography variant="h6">
                    {alert.govuk_reference || alert.alert_id}
                  </Typography>
                  <StatusChip status={alert.status} />
                </Box>
                
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  {alert.title}
                </Typography>
                
                <Box display="flex" gap={1} mb={1}>
                  {alert.alert_category && <CategoryChip category={alert.alert_category} />}
                  {alert.severity && <SeverityChip severity={alert.severity} />}
                  {alert.priority && <Chip label={alert.priority} size="small" variant="outlined" />}
                </Box>
                
                {alert.product_name && (
                  <Typography variant="body2">
                    Product: {alert.product_name}
                  </Typography>
                )}
                
                <Box display="flex" justifyContent="space-between" alignItems="center" mt={2}>
                  <Typography variant="caption" color="textSecondary">
                    {alert.published_date && format(new Date(alert.published_date), 'dd MMM yyyy')}
                  </Typography>
                  <Box display="flex" gap={1}>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<ViewIcon />}
                      onClick={() => navigate(`/alerts/${alert.id}`)}
                    >
                      Details
                    </Button>
                    <IconButton
                      size="small"
                      component="a"
                      href={alert.url?.startsWith('http') ? alert.url : `https://www.gov.uk${alert.url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="View on GOV.UK"
                    >
                      <LaunchIcon />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      ) : (
        // Desktop view - Table
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Reference</TableCell>
                <TableCell>Title</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Severity</TableCell>
                <TableCell>Published</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {alerts.map((alert) => (
                <TableRow
                  key={alert.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/alerts/${alert.id}`)}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {alert.govuk_reference || alert.alert_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {alert.title}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <CategoryChip category={alert.alert_category} />
                  </TableCell>
                  <TableCell>
                    <StatusChip status={alert.status} />
                  </TableCell>
                  <TableCell>
                    {alert.priority && <Chip label={alert.priority} size="small" variant="outlined" />}
                  </TableCell>
                  <TableCell>
                    <SeverityChip severity={alert.severity} />
                  </TableCell>
                  <TableCell>
                    {alert.published_date && format(new Date(alert.published_date), 'dd MMM yyyy')}
                  </TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/alerts/${alert.id}`);
                      }}
                      title="View Details"
                    >
                      <ViewIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      component="a"
                      href={alert.url?.startsWith('http') ? alert.url : `https://www.gov.uk${alert.url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      title="View on GOV.UK"
                    >
                      <LaunchIcon />
                    </IconButton>
                    {alert.status !== 'Closed' && alert.status !== 'Completed' && (
                      <IconButton
                        size="small"
                        onClick={(e) => handleMarkNotRelevant(alert.id, e)}
                        disabled={markingNotRelevant === alert.id}
                        title="Mark as Not Relevant"
                        color="error"
                      >
                        <ThumbDownIcon />
                      </IconButton>
                    )}
                    {alert.date_first_reviewed && (
                      <IconButton size="small" disabled title="Reviewed">
                        <TimerIcon color="success" />
                      </IconButton>
                    )}
                    {alert.notes && (
                      <IconButton size="small" disabled title="Has Notes">
                        <NoteIcon color="primary" />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            rowsPerPageOptions={[5, 10, 25]}
            component="div"
            count={total}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </TableContainer>
      )}
    </Box>
  );
}

export default AlertsList;