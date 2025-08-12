import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  Grid,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  TextField,
  FormControlLabel,
  Checkbox,
  CircularProgress,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  RadioGroup,
  Radio,
  FormLabel,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import {
  ArrowBack as BackIcon,
  OpenInNew as ExternalLinkIcon,
  CheckCircle as CheckIcon,
  RadioButtonUnchecked as UncheckedIcon,
  Warning as WarningIcon,
  Save as SaveIcon,
  Done as DoneIcon,
  Assignment as ClipboardIcon,
  People as PeopleIcon,
  LocalPharmacy as PharmacyIcon,
  Email as EmailIcon,
  MedicalServices as MedicalIcon,
  LocalHospital as EmergencyIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { alertsApi, Alert as AlertType, AlertUpdate } from '../services/api';

interface ChecklistItem {
  id: string;
  label: string;
  field: keyof AlertUpdate;
  type: 'boolean' | 'text' | 'number' | 'date' | 'select' | 'yes-no';
  required?: boolean;
  condition?: (alert: AlertType, updates: AlertUpdate) => boolean;
  options?: { value: string; label: string }[];
  followUpFields?: ChecklistItem[];
}

const getChecklistItems = (alert: AlertType, updates: AlertUpdate): ChecklistItem[] => {
  const patientCount = updates.patients_affected_count ?? alert.patients_affected_count ?? 0;
  
  const items: ChecklistItem[] = [
    {
      id: 'acknowledge',
      label: 'Alert acknowledged',
      field: 'date_first_reviewed',
      type: 'date',
      required: true,
    },
    {
      id: 'emis_search',
      label: 'Was EMIS search completed?',
      field: 'emis_search_completed',
      type: 'yes-no',
      required: true,
      followUpFields: [
        {
          id: 'emis_search_date',
          label: 'Date of EMIS search',
          field: 'emis_search_date',
          type: 'date',
          condition: () => updates.emis_search_completed === true,
        },
        {
          id: 'patient_count',
          label: 'Number of patients identified',
          field: 'patients_affected_count',
          type: 'number',
          required: true,
          condition: () => updates.emis_search_completed === true,
        },
        {
          id: 'emis_search_reason',
          label: 'Reason EMIS search not completed',
          field: 'emis_search_reason',
          type: 'text',
          condition: () => updates.emis_search_completed === false,
        },
      ],
    },
    {
      id: 'emergency_drugs',
      label: 'Are any emergency drugs affected?',
      field: 'emergency_drugs_check',
      type: 'yes-no',
      required: true,
      followUpFields: [
        {
          id: 'emergency_drugs_affected',
          label: 'Which emergency drugs are affected?',
          field: 'emergency_drugs_affected',
          type: 'text',
          condition: () => updates.emergency_drugs_check === true,
        },
      ],
    },
    {
      id: 'team_notified',
      label: 'Has the clinical team been notified?',
      field: 'practice_team_notified',
      type: 'yes-no',
      required: true,
      followUpFields: [
        {
          id: 'team_notification_date',
          label: 'Date team was notified',
          field: 'practice_team_notified_date',
          type: 'date',
          condition: () => updates.practice_team_notified === true,
        },
        {
          id: 'team_notification_method',
          label: 'Method of notification',
          field: 'team_notification_method',
          type: 'select',
          options: [
            { value: 'Email', label: 'Email' },
            { value: 'Meeting', label: 'Team Meeting' },
            { value: 'Phone', label: 'Phone' },
            { value: 'Teams', label: 'Teams Message' },
            { value: 'Multiple', label: 'Multiple Methods' },
          ],
          condition: () => updates.practice_team_notified === true,
        },
      ],
    },
  ];

  // Only show patient-specific fields if there are affected patients
  if (patientCount > 0) {
    items.push(
      {
        id: 'patients_contacted',
        label: 'Have affected patients been contacted?',
        field: 'patients_contacted',
        type: 'select',
        options: [
          { value: 'Yes', label: 'Yes - All contacted' },
          { value: 'In Progress', label: 'In Progress' },
          { value: 'No', label: 'No - Not required' },
          { value: 'Planned', label: 'Planned' },
        ],
        followUpFields: [
          {
            id: 'contact_method',
            label: 'Contact method used',
            field: 'contact_method',
            type: 'select',
            options: [
              { value: 'SMS', label: 'SMS' },
              { value: 'Letter', label: 'Letter' },
              { value: 'Phone', label: 'Phone' },
              { value: 'F2F', label: 'Face to Face' },
              { value: 'Multiple', label: 'Multiple methods' },
            ],
            condition: () => updates.patients_contacted === 'Yes' || updates.patients_contacted === 'In Progress',
          },
        ],
      },
      {
        id: 'medication_stopped',
        label: 'Was medication stopped for affected patients?',
        field: 'medication_stopped',
        type: 'yes-no',
        followUpFields: [
          {
            id: 'medication_stopped_date',
            label: 'Date medication stopped',
            field: 'medication_stopped_date',
            type: 'date',
            condition: () => updates.medication_stopped === true,
          },
          {
            id: 'medication_alternative',
            label: 'Was alternative medication provided?',
            field: 'medication_alternative_provided',
            type: 'yes-no',
            condition: () => updates.medication_stopped === true,
          },
          {
            id: 'medication_not_stopped_reason',
            label: 'Reason medication not stopped',
            field: 'medication_not_stopped_reason',
            type: 'text',
            condition: () => updates.medication_stopped === false,
          },
        ],
      },
      {
        id: 'patient_harm_assessed',
        label: 'Has patient harm assessment been completed?',
        field: 'patient_harm_assessed',
        type: 'yes-no',
        required: true,
        followUpFields: [
          {
            id: 'patient_harm_occurred',
            label: 'Was any patient harm identified?',
            field: 'patient_harm_occurred',
            type: 'yes-no',
            condition: () => updates.patient_harm_assessed === true,
          },
          {
            id: 'harm_severity',
            label: 'Severity of harm',
            field: 'harm_severity',
            type: 'select',
            options: [
              { value: 'Minor', label: 'Minor' },
              { value: 'Moderate', label: 'Moderate' },
              { value: 'Severe', label: 'Severe' },
            ],
            condition: () => updates.patient_harm_occurred === true,
          },
          {
            id: 'patient_harm_details',
            label: 'Details of patient harm',
            field: 'patient_harm_details',
            type: 'text',
            condition: () => updates.patient_harm_occurred === true,
          },
          {
            id: 'harm_assessment_planned',
            label: 'Planned assessment date',
            field: 'harm_assessment_planned_date',
            type: 'date',
            condition: () => updates.patient_harm_assessed === false,
          },
        ],
      }
    );
  }

  // Flatten follow-up fields into main list based on conditions
  const expandedItems: ChecklistItem[] = [];
  items.forEach(item => {
    expandedItems.push(item);
    if (item.followUpFields) {
      item.followUpFields.forEach(followUp => {
        if (!followUp.condition || followUp.condition(alert, updates)) {
          expandedItems.push(followUp);
        }
      });
    }
  });

  return expandedItems;
};

function AlertDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [alert, setAlert] = useState<AlertType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [updates, setUpdates] = useState<AlertUpdate>({});
  const [notes, setNotes] = useState('');
  const [showCompleteDialog, setShowCompleteDialog] = useState(false);

  useEffect(() => {
    fetchAlert();
  }, [id]);

  const fetchAlert = async () => {
    if (!id) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await alertsApi.getAlert(parseInt(id));
      setAlert(data);
      setNotes(data.notes || '');
      
      // Debug logging
      console.log('Alert data received:', {
        emis_search_completed: data.emis_search_completed,
        emergency_drugs_check: data.emergency_drugs_check,
        practice_team_notified: data.practice_team_notified,
      });
      
      // Initialize updates with existing values for yes-no fields
      const initialUpdates: AlertUpdate = {};
      if (data.emis_search_completed !== null) initialUpdates.emis_search_completed = data.emis_search_completed;
      if (data.emergency_drugs_check !== null) initialUpdates.emergency_drugs_check = data.emergency_drugs_check;
      if (data.practice_team_notified !== null) initialUpdates.practice_team_notified = data.practice_team_notified;
      if (data.medication_stopped !== null) initialUpdates.medication_stopped = data.medication_stopped;
      if (data.patient_harm_assessed !== null) initialUpdates.patient_harm_assessed = data.patient_harm_assessed;
      if (data.patient_harm_occurred !== null) initialUpdates.patient_harm_occurred = data.patient_harm_occurred;
      if (data.medication_alternative_provided !== null) initialUpdates.medication_alternative_provided = data.medication_alternative_provided;
      setUpdates(initialUpdates);
      
      // Set initial active step based on completion
      if (data.date_first_reviewed) setActiveStep(1);
      if (data.emis_search_completed !== null) setActiveStep(2);
      if (data.emergency_drugs_check !== null) setActiveStep(3);
      if (data.practice_team_notified !== null) setActiveStep(4);
    } catch (err: any) {
      setError('Failed to load alert details');
      console.error('Alert detail error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkReviewed = async () => {
    if (!alert) return;
    
    try {
      setSaving(true);
      await alertsApi.markReviewed(alert.id);
      await fetchAlert();
    } catch (err) {
      console.error('Failed to mark as reviewed:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateField = (field: keyof AlertUpdate, value: any) => {
    setUpdates((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveProgress = async () => {
    if (!alert) return;
    
    try {
      setSaving(true);
      const updateData = { ...updates, notes };
      await alertsApi.updateAlert(alert.id, updateData);
      await fetchAlert();
      setUpdates({});
    } catch (err) {
      console.error('Failed to save progress:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = async () => {
    if (!alert) return;
    
    try {
      setSaving(true);
      const updateData = {
        ...updates,
        notes,
        status: 'Completed' as const,
        action_completed_date: new Date().toISOString(),
      };
      console.log('Sending update data:', updateData);
      const response = await alertsApi.updateAlert(alert.id, updateData);
      console.log('Update response:', response);
      setShowCompleteDialog(false);
      navigate('/dashboard');
    } catch (err: any) {
      console.error('Failed to complete alert:', err);
      console.error('Error response:', err.response?.data);
      alert(`Failed to complete: ${err.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'Critical': return 'error';
      case 'High': return 'warning';
      case 'Medium': return 'info';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !alert) {
    return (
      <Alert severity="error">
        {error || 'Alert not found'}
      </Alert>
    );
  }

  const checklistItems = getChecklistItems(alert, updates);
  const checklistProgress = checklistItems.filter(
    item => {
      const value = updates[item.field] ?? alert[item.field as keyof AlertType];
      if (item.type === 'yes-no') {
        return value === true || value === false; // Only true/false counts for yes-no
      }
      return value !== null && value !== undefined && value !== '';
    }
  ).length;

  const requiredItemsCompleted = checklistItems
    .filter(item => item.required)
    .every(item => {
      const value = updates[item.field] ?? alert[item.field as keyof AlertType];
      if (item.type === 'yes-no') {
        return value === true || value === false; // Only true/false counts for yes-no
      }
      return value !== null && value !== undefined && value !== '';
    });

  const renderFieldInput = (item: ChecklistItem, currentValue: any) => {
    switch (item.type) {
      case 'yes-no':
        return (
          <FormControl component="fieldset">
            <RadioGroup
              row
              value={currentValue === true ? 'yes' : currentValue === false ? 'no' : ''}
              onChange={(e) => handleUpdateField(item.field, e.target.value === 'yes')}
            >
              <FormControlLabel value="yes" control={<Radio />} label="Yes" />
              <FormControlLabel value="no" control={<Radio />} label="No" />
            </RadioGroup>
          </FormControl>
        );
      
      case 'boolean':
        return (
          <FormControlLabel
            control={
              <Checkbox
                checked={currentValue === true}
                onChange={(e) => handleUpdateField(item.field, e.target.checked)}
              />
            }
            label="Complete"
          />
        );
      
      case 'text':
        return (
          <TextField
            fullWidth
            multiline
            rows={2}
            size="small"
            value={currentValue || ''}
            onChange={(e) => handleUpdateField(item.field, e.target.value)}
            placeholder={`Enter ${item.label.toLowerCase()}`}
          />
        );
      
      case 'number':
        return (
          <TextField
            type="number"
            size="small"
            value={currentValue ?? ''}
            onChange={(e) => {
              const val = e.target.value === '' ? 0 : parseInt(e.target.value);
              handleUpdateField(item.field, val);
            }}
            placeholder="Enter count (0 if none)"
            inputProps={{ min: 0 }}
          />
        );
      
      case 'select':
        return (
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <Select
              value={currentValue || ''}
              onChange={(e) => handleUpdateField(item.field, e.target.value)}
            >
              <MenuItem value="">None</MenuItem>
              {item.options?.map(opt => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );
      
      case 'date':
        if (currentValue) {
          return (
            <Typography variant="body2" color="textSecondary">
              Completed: {format(new Date(currentValue), 'dd MMM yyyy HH:mm')}
            </Typography>
          );
        }
        return (
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DatePicker
              label="Select date"
              value={currentValue ? new Date(currentValue) : null}
              onChange={(newValue) => handleUpdateField(item.field, newValue?.toISOString())}
              renderInput={(params) => <TextField {...params} size="small" />}
            />
          </LocalizationProvider>
        );
      
      default:
        return null;
    }
  };

  return (
    <Box>
      <Button
        startIcon={<BackIcon />}
        onClick={() => navigate('/alerts')}
        sx={{ mb: 2 }}
      >
        Back to Alerts
      </Button>

      {/* Alert Summary */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={8}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <Chip
                label={alert.severity || 'Unknown'}
                color={getSeverityColor(alert.severity) as any}
                icon={<WarningIcon />}
              />
              {alert.priority && (
                <Chip label={alert.priority} variant="outlined" />
              )}
              <Chip label={alert.status} color="primary" />
            </Box>
            
            <Typography variant="h5" gutterBottom>
              {alert.title}
            </Typography>
            
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Reference: {alert.govuk_reference || alert.alert_id} | 
              Issued: {alert.issued_date ? format(new Date(alert.issued_date), 'dd MMM yyyy') : 'Unknown'}
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Button
              fullWidth
              variant="outlined"
              startIcon={<ExternalLinkIcon />}
              href={alert.url}
              target="_blank"
              sx={{ mb: 1 }}
            >
              View Official Alert
            </Button>
            {!alert.date_first_reviewed && (
              <Button
                fullWidth
                variant="contained"
                color="primary"
                onClick={handleMarkReviewed}
                disabled={saving}
              >
                Mark as Reviewed
              </Button>
            )}
          </Grid>
        </Grid>
      </Paper>

      <Grid container spacing={3}>
        {/* Action Checklist */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Action Checklist ({checklistProgress}/{checklistItems.length})
            </Typography>
            
            <Stepper activeStep={activeStep} orientation="vertical">
              {checklistItems.map((item, index) => {
                const currentValue = updates[item.field] ?? alert[item.field as keyof AlertType];
                const isCompleted = item.type === 'yes-no' 
                  ? currentValue === true || currentValue === false  // Only true/false counts as completed for yes-no
                  : currentValue !== null && currentValue !== undefined && currentValue !== '';
                
                return (
                  <Step key={item.id} completed={isCompleted}>
                    <StepLabel
                      optional={!item.required && <Typography variant="caption">Optional</Typography>}
                      StepIconComponent={() => (
                        isCompleted ? <CheckIcon color="success" /> : <UncheckedIcon />
                      )}
                    >
                      {item.label}
                    </StepLabel>
                    <StepContent>
                      {renderFieldInput(item, currentValue)}
                      
                      <Box mt={1}>
                        <Button
                          size="small"
                          onClick={() => setActiveStep(index + 1)}
                          disabled={index === checklistItems.length - 1}
                        >
                          Next
                        </Button>
                      </Box>
                    </StepContent>
                  </Step>
                );
              })}
            </Stepper>
            
            <Divider sx={{ my: 2 }} />
            
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any additional notes..."
            />
            
            <Box display="flex" gap={2} mt={2}>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSaveProgress}
                disabled={saving}
              >
                Save Progress
              </Button>
              <Button
                variant="contained"
                color="success"
                startIcon={<DoneIcon />}
                onClick={() => setShowCompleteDialog(true)}
                disabled={saving || !requiredItemsCompleted}
              >
                Mark Complete
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Product Details & Actions */}
        <Grid item xs={12} md={4}>
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Product Details
              </Typography>
              <List dense>
                {alert.product_name && (
                  <ListItem>
                    <ListItemIcon><PharmacyIcon /></ListItemIcon>
                    <ListItemText primary="Product" secondary={alert.product_name} />
                  </ListItem>
                )}
                {alert.batch_numbers && (
                  <ListItem>
                    <ListItemIcon><ClipboardIcon /></ListItemIcon>
                    <ListItemText primary="Batch Numbers" secondary={alert.batch_numbers} />
                  </ListItem>
                )}
                {alert.manufacturer && (
                  <ListItem>
                    <ListItemText primary="Manufacturer" secondary={alert.manufacturer} />
                  </ListItem>
                )}
                {alert.expiry_dates && (
                  <ListItem>
                    <ListItemText primary="Expiry Dates" secondary={alert.expiry_dates} />
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>

          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Emergency Drugs Status
              </Typography>
              {updates.emergency_drugs_check === true ? (
                <>
                  <Chip 
                    icon={<EmergencyIcon />}
                    label="Emergency Drugs Affected" 
                    color="error" 
                    sx={{ mb: 1 }}
                  />
                  {(updates.emergency_drugs_affected || alert.emergency_drugs_affected) && (
                    <Typography variant="body2" color="error">
                      Affected: {updates.emergency_drugs_affected || alert.emergency_drugs_affected}
                    </Typography>
                  )}
                </>
              ) : updates.emergency_drugs_check === false ? (
                <Chip 
                  icon={<CheckIcon />}
                  label="No Emergency Drugs Affected" 
                  color="success" 
                />
              ) : (
                <Typography variant="body2" color="textSecondary">
                  Not yet checked
                </Typography>
              )}
            </CardContent>
          </Card>

          {((updates.patients_affected_count ?? alert.patients_affected_count ?? 0) > 0) && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Patient Impact
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemIcon><PeopleIcon /></ListItemIcon>
                    <ListItemText 
                      primary="Patients Affected" 
                      secondary={updates.patients_affected_count ?? alert.patients_affected_count}
                    />
                  </ListItem>
                  {updates.medication_stopped === true && (
                    <ListItem>
                      <ListItemIcon><MedicalIcon /></ListItemIcon>
                      <ListItemText 
                        primary="Medication Stopped" 
                        secondary={
                          (updates.medication_stopped_date || alert.medication_stopped_date)
                            ? format(new Date(updates.medication_stopped_date || alert.medication_stopped_date!), 'dd MMM yyyy')
                            : 'Yes'
                        }
                      />
                    </ListItem>
                  )}
                  {updates.patient_harm_assessed === true && (
                    <ListItem>
                      <ListItemText 
                        primary="Harm Assessment" 
                        secondary={
                          updates.patient_harm_occurred === true
                            ? `Harm occurred - ${updates.harm_severity || alert.harm_severity || 'See details'}`
                            : 'No harm identified'
                        }
                      />
                    </ListItem>
                  )}
                </List>
              </CardContent>
            </Card>
          )}

          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Actions Required
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemText 
                    primary="EMIS Search Terms"
                    secondary={alert.emis_search_terms || 'Check prescription records'}
                  />
                </ListItem>
                {alert.action_required && (
                  <ListItem>
                    <ListItemText 
                      primary="Required Actions"
                      secondary={alert.action_required}
                    />
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Complete Dialog */}
      <Dialog open={showCompleteDialog} onClose={() => setShowCompleteDialog(false)}>
        <DialogTitle>Complete Alert Review</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to mark this alert as complete? 
            Please ensure all required actions have been taken.
          </Typography>
          {updates.patient_harm_occurred === true && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Patient harm has been recorded. Ensure CQC reporting requirements are met.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCompleteDialog(false)}>Cancel</Button>
          <Button onClick={handleComplete} variant="contained" color="success">
            Complete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default AlertDetail;