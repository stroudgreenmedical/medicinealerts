import { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Alert,
  Chip,
  Grid,
  Stack,
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  CheckCircle as SuccessIcon,
  Cancel as ErrorIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { systemTestApi } from '../services/api';

interface TestResult {
  status: 'success' | 'error' | 'no_data';
  count: number;
  source: string;
  error: string | null;
}

interface SystemTestResponse {
  test_date: string;
  date_range: {
    start: string;
    end: string;
  };
  summary: {
    total_categories: number;
    successful_tests: number;
    failed_tests: number;
    total_alerts_found: number;
  };
  categories: Record<string, TestResult>;
}

function SystemTest() {
  const [testResults, setTestResults] = useState<SystemTestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSystemTest = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const results = await systemTestApi.runTest();
      setTestResults(results);
    } catch (err) {
      setError('Failed to run system test. Please check the console for details.');
      console.error('System test error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <SuccessIcon color="success" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'no_data':
        return <WarningIcon color="warning" />;
      default:
        return null;
    }
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'success':
        return <Chip label="Connected" color="success" size="small" />;
      case 'error':
        return <Chip label="Failed" color="error" size="small" />;
      case 'no_data':
        return <Chip label="No Source" color="warning" size="small" />;
      default:
        return <Chip label="Unknown" size="small" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        System Test
      </Typography>
      
      <Typography variant="body1" color="text.secondary" paragraph>
        Test the alert system's ability to fetch data from all configured sources.
        This will poll the last 30 days of alerts for each category.
      </Typography>

      {/* Action Buttons */}
      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          color="primary"
          size="large"
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <RunIcon />}
          onClick={runSystemTest}
          disabled={loading}
        >
          {loading ? 'Running Test...' : 'Run System Test'}
        </Button>
        
        {testResults && (
          <Button
            variant="outlined"
            size="large"
            startIcon={<RefreshIcon />}
            onClick={runSystemTest}
            disabled={loading}
            sx={{ ml: 2 }}
          >
            Re-run Test
          </Button>
        )}
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Test Results */}
      {testResults && (
        <>
          {/* Summary Cards */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Total Categories
                  </Typography>
                  <Typography variant="h4">
                    {testResults.summary.total_categories}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Successful Tests
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {testResults.summary.successful_tests}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Failed Tests
                  </Typography>
                  <Typography variant="h4" color={testResults.summary.failed_tests > 0 ? 'error.main' : 'text.primary'}>
                    {testResults.summary.failed_tests}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Total Alerts Found
                  </Typography>
                  <Typography variant="h4" color="primary.main">
                    {testResults.summary.total_alerts_found}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Test Details Table */}
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Alert Category</TableCell>
                  <TableCell align="center">Status</TableCell>
                  <TableCell align="center">Connection</TableCell>
                  <TableCell align="right">Alerts Found</TableCell>
                  <TableCell>Source</TableCell>
                  <TableCell>Error Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(testResults.categories).map(([category, result]) => (
                  <TableRow key={category}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {category}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      {getStatusIcon(result.status)}
                    </TableCell>
                    <TableCell align="center">
                      {getStatusChip(result.status)}
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        fontWeight={result.count > 0 ? 'bold' : 'normal'}
                        color={result.count > 0 ? 'primary' : 'text.secondary'}
                      >
                        {result.count}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {result.source}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {result.error && (
                        <Typography variant="caption" color="error">
                          {result.error.substring(0, 100)}
                          {result.error.length > 100 && '...'}
                        </Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Test Metadata */}
          <Box sx={{ mt: 3 }}>
            <Stack direction="row" spacing={3}>
              <Typography variant="body2" color="text.secondary">
                Test Date: {formatDate(testResults.test_date)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Date Range: {new Date(testResults.date_range.start).toLocaleDateString()} - {new Date(testResults.date_range.end).toLocaleDateString()}
              </Typography>
            </Stack>
          </Box>
        </>
      )}
    </Box>
  );
}

export default SystemTest;