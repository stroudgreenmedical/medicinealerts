import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface Alert {
  id: number;
  alert_id: string;
  govuk_reference?: string;
  content_id: string;
  url: string;
  title: string;
  published_date?: string;
  issued_date?: string;
  alert_type?: string;
  severity?: 'Critical' | 'High' | 'Medium' | 'Low';
  priority?: 'P1-Immediate' | 'P2-Within 48h' | 'P3-Within 1 week' | 'P4-Routine';
  message_type?: string;
  medical_specialties?: string;
  auto_relevance?: string;
  final_relevance?: string;
  relevance_reason?: string;
  product_name?: string;
  active_ingredient?: string;
  manufacturer?: string;
  batch_numbers?: string;
  expiry_dates?: string;
  therapeutic_area?: string;
  status: 'New' | 'Under Review' | 'Action Required' | 'In Progress' | 'Completed' | 'Closed';
  assigned_to?: string;
  date_first_reviewed?: string;
  action_required?: string;
  emis_search_terms?: string;
  emis_search_completed?: boolean | null;
  emis_search_date?: string;
  emis_search_reason?: string;
  patients_affected_count?: number;
  emergency_drugs_check?: boolean | null;
  emergency_drugs_affected?: string;
  practice_team_notified?: boolean | null;
  practice_team_notified_date?: string;
  team_notification_method?: string;
  patients_contacted?: string;
  contact_method?: string;
  communication_template?: string;
  medication_stopped?: boolean | null;
  medication_stopped_date?: string;
  medication_alternative_provided?: boolean | null;
  medication_not_stopped_reason?: string;
  patient_harm_assessed?: boolean | null;
  harm_assessment_planned_date?: string;
  patient_harm_occurred?: boolean | null;
  harm_severity?: string;
  patient_harm_details?: string;
  recalls_completed?: boolean | null;
  action_completed_date?: string;
  time_to_first_review?: number;
  time_to_completion?: number;
  evidence_uploaded?: boolean | null;
  evidence_links?: string;
  cqc_reportable?: boolean | null;
  notes?: string;
  created_at: string;
  updated_at: string;
  teams_notified?: boolean | null;
}

export interface DashboardStats {
  total_alerts: number;
  new_alerts: number;
  urgent_alerts: number;
  overdue_alerts: number;
  completed_alerts: number;
  alerts_by_status: Record<string, number>;
  alerts_by_priority: Record<string, number>;
  alerts_by_type: Record<string, number>;
  recent_alerts: Alert[];
}

export interface AlertUpdate {
  status?: string;
  priority?: string;
  date_first_reviewed?: string;
  action_required?: string;
  emis_search_completed?: boolean | null;
  emis_search_date?: string;
  emis_search_reason?: string;
  patients_affected_count?: number;
  emergency_drugs_check?: boolean | null;
  emergency_drugs_affected?: string;
  practice_team_notified?: boolean | null;
  practice_team_notified_date?: string;
  team_notification_method?: string;
  patients_contacted?: string;
  contact_method?: string;
  communication_template?: string;
  medication_stopped?: boolean | null;
  medication_stopped_date?: string;
  medication_alternative_provided?: boolean | null;
  medication_not_stopped_reason?: string;
  patient_harm_assessed?: boolean | null;
  harm_assessment_planned_date?: string;
  patient_harm_occurred?: boolean | null;
  harm_severity?: string;
  patient_harm_details?: string;
  recalls_completed?: boolean | null;
  action_completed_date?: string;
  evidence_uploaded?: boolean | null;
  evidence_links?: string;
  cqc_reportable?: boolean | null;
  notes?: string;
  final_relevance?: string;
}

// Auth API
export const authApi = {
  login: async (credentials: LoginCredentials) => {
    const response = await api.post('/api/auth/login', credentials);
    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
    }
    return response.data;
  },
  
  logout: async () => {
    await api.post('/api/auth/logout');
    localStorage.removeItem('token');
  },
  
  getCurrentUser: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },
};

// Alerts API
export const alertsApi = {
  getAlerts: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    priority?: string;
    severity?: string;
    relevance?: string;
    search?: string;
  }) => {
    const response = await api.get('/api/alerts/', { params });
    return response.data;
  },
  
  getAlert: async (id: number) => {
    const response = await api.get(`/api/alerts/${id}`);
    return response.data;
  },
  
  updateAlert: async (id: number, data: AlertUpdate) => {
    const response = await api.put(`/api/alerts/${id}`, data);
    return response.data;
  },
  
  markReviewed: async (id: number) => {
    const response = await api.post(`/api/alerts/${id}/mark-reviewed`);
    return response.data;
  },
  
  getOverdueAlerts: async () => {
    const response = await api.get('/api/alerts/overdue/list');
    return response.data;
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await api.get('/api/dashboard/stats');
    return response.data;
  },
};

// Reports API
export const reportsApi = {
  exportExcel: async (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const response = await api.get(`/api/reports/export/excel?${params}`, {
      responseType: 'blob',
    });
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `MHRA_Alerts_${new Date().toISOString().split('T')[0]}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },
  
  getMonthlySummary: async (year: number, month: number) => {
    const response = await api.get('/api/reports/summary/monthly', {
      params: { year, month },
    });
    return response.data;
  },
  
  getAnnualSummary: async (year: number) => {
    const response = await api.get('/api/reports/summary/annual', {
      params: { year },
    });
    return response.data;
  },
};

export default api;