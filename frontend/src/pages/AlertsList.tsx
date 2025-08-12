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
} from '@mui/material';
import {
  Search as SearchIcon,
  Visibility as ViewIcon,
  Timer as TimerIcon,
  Note as NoteIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
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

function AlertsList() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || '');
  const [severityFilter, setSeverityFilter] = useState('');

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await alertsApi.getAlerts({
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        search: search || undefined,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        severity: severityFilter || undefined,
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

  useEffect(() => {
    fetchAlerts();
  }, [page, rowsPerPage, statusFilter, priorityFilter, severityFilter]);

  const handleSearch = () => {
    setPage(0);
    fetchAlerts();
  };

  const handleClearFilters = () => {
    setSearch('');
    setStatusFilter('');
    setPriorityFilter('');
    setSeverityFilter('');
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

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        All Alerts
      </Typography>

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
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<ViewIcon />}
                    onClick={() => navigate(`/alerts/${alert.id}`)}
                  >
                    View
                  </Button>
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
                <TableCell>Status</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Severity</TableCell>
                <TableCell>Product</TableCell>
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
                    <StatusChip status={alert.status} />
                  </TableCell>
                  <TableCell>
                    {alert.priority && <Chip label={alert.priority} size="small" variant="outlined" />}
                  </TableCell>
                  <TableCell>
                    <SeverityChip severity={alert.severity} />
                  </TableCell>
                  <TableCell>{alert.product_name || '-'}</TableCell>
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
                    >
                      <ViewIcon />
                    </IconButton>
                    {alert.date_first_reviewed && (
                      <IconButton size="small" disabled>
                        <TimerIcon color="success" />
                      </IconButton>
                    )}
                    {alert.notes && (
                      <IconButton size="small" disabled>
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