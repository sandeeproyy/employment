/**
 * AutoApply — API Client
 *
 * Typed fetch wrapper for all backend API endpoints.
 */

const getApiBase = () => {
  // Respect user-specified non-localhost API URL if baked in during build
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && !envUrl.includes('localhost')) {
    return envUrl;
  }
  
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    // Fallback: use current domain/IP with backend port 8000
    return `${protocol}//${hostname}:8000`;
  }
  
  return envUrl || 'http://localhost:8000';
};

export const API_BASE = getApiBase();

export const getApiToken = (): string => {
  if (typeof window === 'undefined') return '';
  let token = sessionStorage.getItem('api_token') || '';
  if (!token) {
    token = 'session_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    sessionStorage.setItem('api_token', token);
  }
  return token;
};

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = process.env.NEXT_PUBLIC_API_TOKEN || getApiToken();
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  } as Record<string, string>;

  if (token) {
    headers['X-API-Token'] = token;
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('api_token');
      window.dispatchEvent(new Event('unauthorized'));
    }
    throw new Error('unauthorized');
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// ── Types ─────────────────────────────────────────────

export interface ResumeStructured {
  skills: string[];
  projects: Array<{
    name: string;
    description: string;
    technologies: string[];
    highlights?: string[];
  }>;
  education: Array<{
    institution: string;
    degree: string;
    field: string;
    year: string;
    gpa?: string;
  }>;
  experience: Array<{
    company: string;
    title: string;
    duration: string;
    description: string;
    technologies?: string[];
  }>;
  interests: string[];
}

export interface Profile {
  id: number;
  name: string;
  email: string;
  resume_structured: ResumeStructured | null;
  resume_pdf_path: string | null;
  resume_latex_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface MatchBreakdown {
  skills: number;
  projects: number;
  education: number;
  location: number;
  career_goals: number;
  total: number;
  matched_skills: string[];
  missing_skills: string[];
  reason: string;
}

export interface Job {
  id: number;
  canonical_id: string;
  title: string;
  company: string;
  description: string;
  location: string;
  remote_allowed: boolean;
  posted_at: string | null;
  job_type: string;
  experience_level: string;
  department: string;
  source: string;
  source_url: string;
  apply_url: string;
  all_source_urls: string[];
  skills_required: string[];
  salary_info: string | null;
  match_score: number;
  match_breakdown: MatchBreakdown | null;
  status: string;
  discovered_at: string;
  expires_at: string | null;
  scored_at: string | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface LocationPreference {
  country: string;
  state?: string;
  city?: string;
  remote_allowed: boolean;
  radius_km?: number;
}

export interface JobSourceConfig {
  type: string;
  board_token?: string;
  company?: string;
  url?: string;
  keywords?: string;
  location?: string;
  job_type?: string;
  interval_minutes: number;
  enabled: boolean;
  label: string;
}

export interface Preferences {
  id: number;
  job_types: string[];
  domains: string[];
  experience_level: string;
  locations: LocationPreference[];
  target_companies: string[];
  min_match_score: number;
  job_sources: JobSourceConfig[];
}

export interface Application {
  id: number;
  job_id: number;
  tailored_resume_path: string | null;
  cover_letter_text: string | null;
  cover_letter_path: string | null;
  status: string;
  application_answers: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
  applied_at: string | null;
  updated_at: string;
  job_title?: string;
  job_company?: string;
  job_match_score?: number;
}

export interface Analytics {
  total_applied: number;
  total_interviews: number;
  total_assessments: number;
  total_offers: number;
  total_rejected: number;
  total_pending: number;
  response_rate: number;
  offer_rate: number;
}

export interface KanbanColumn {
  status: string;
  label: string;
  applications: Application[];
  count: number;
}

export interface KanbanBoard {
  columns: KanbanColumn[];
  analytics: Analytics;
}

export interface DashboardStats {
  total_jobs_discovered: number;
  high_match_jobs: number;
  jobs_by_status: Record<string, number>;
  applications_by_status: Record<string, number>;
  is_scanning: boolean;
  is_scoring: boolean;
  recent_jobs: Array<{
    id: number;
    title: string;
    company: string;
    match_score: number;
    status: string;
    discovered_at: string;
  }>;
}

// ── API Functions ─────────────────────────────────────

// Profile
export const api = {
  // Dashboard
  getDashboard: () => apiFetch<DashboardStats>('/api/dashboard'),
  getHealth: () => apiFetch<{ status: string }>('/api/health'),

  // Profile
  getProfile: () => apiFetch<Profile>('/api/profile'),
  updateProfile: (data: Partial<Profile>) =>
    apiFetch<Profile>('/api/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  uploadResume: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getApiToken();
    const headers: Record<string, string> = {};
    if (token) headers['X-API-Token'] = token;
    const res = await fetch(`${API_BASE}/api/profile/resume`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  // Preferences
  getPreferences: () => apiFetch<Preferences>('/api/preferences'),
  updatePreferences: (data: Partial<Preferences>) =>
    apiFetch<Preferences>('/api/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // Jobs
  getJobs: (params?: Record<string, string | number | boolean>) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          searchParams.set(k, String(v));
        }
      });
    }
    const qs = searchParams.toString();
    return apiFetch<JobListResponse>(`/api/jobs${qs ? `?${qs}` : ''}`);
  },
  getJob: (id: number) => apiFetch<Job>(`/api/jobs/${id}`),
  approveJob: (id: number) =>
    apiFetch<{ message: string }>(`/api/jobs/${id}/approve`, { method: 'POST' }),
  rejectJob: (id: number) =>
    apiFetch<{ message: string }>(`/api/jobs/${id}/reject`, { method: 'POST' }),
  triggerDiscovery: () =>
    apiFetch<{ message: string; task_id?: string }>('/api/jobs/trigger-discovery', { method: 'POST' }),
  triggerScoring: () =>
    apiFetch<{ message: string; task_id?: string }>('/api/jobs/trigger-scoring', { method: 'POST' }),

  // Applications
  getKanban: () => apiFetch<KanbanBoard>('/api/applications/kanban'),
  getApplications: () => apiFetch<Application[]>('/api/applications'),
  getApplication: (id: number) => apiFetch<Application>(`/api/applications/${id}`),
  updateApplicationStatus: (id: number, status: string) =>
    apiFetch<Application>(`/api/applications/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    }),
  updateApplicationNotes: (id: number, notes: string) =>
    apiFetch<Application>(`/api/applications/${id}/notes`, {
      method: 'PUT',
      body: JSON.stringify({ notes }),
    }),
  getAnalytics: () => apiFetch<Analytics>('/api/applications/analytics'),
  getApplicationLatex: (id: number) => apiFetch<{ latex: string }>(`/api/applications/${id}/latex`),
  resetAllData: () => apiFetch<{ message: string }>('/api/jobs/reset-all', { method: 'POST' }),
  chatbotChat: (messages: Array<{ role: string; content: string }>) =>
    apiFetch<{ response: string; preference_update?: any; suggested_replies?: string[] }>('/api/chatbot/chat', {
      method: 'POST',
      body: JSON.stringify({ messages }),
    }),
};

// ── WebSocket Notification Client ─────────────────────

export function connectNotifications(
  onNotification: (data: {
    type: string;
    notification_type: string;
    title: string;
    body: string;
    data: Record<string, unknown>;
    timestamp: string;
  }) => void
) {
  const token = process.env.NEXT_PUBLIC_API_TOKEN || getApiToken();
  const wsUrl = API_BASE.replace('http', 'ws') + `/ws/notifications${token ? `?token=${encodeURIComponent(token)}` : ''}`;
  let ws: WebSocket;
  let reconnectTimer: NodeJS.Timeout;
  let active = true;

  function connect() {
    if (!active) return;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('🔔 Notifications connected');
      // Request browser notification permission
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'notification') {
          onNotification(data);
          // Show browser notification
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(data.title, {
              body: data.body,
              icon: '/favicon.ico',
            });
          }
        }
      } catch (e) {
        console.error('Notification parse error:', e);
      }
    };

    ws.onclose = () => {
      if (!active) return;
      console.log('🔔 Notifications disconnected, reconnecting...');
      reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    // Heartbeat
    const heartbeat = setInterval(() => {
      if (!active) {
        clearInterval(heartbeat);
        return;
      }
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      } else if (ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
        clearInterval(heartbeat);
      }
    }, 30000);
  }

  connect();

  return () => {
    active = false;
    clearTimeout(reconnectTimer);
    ws?.close();
  };
}
