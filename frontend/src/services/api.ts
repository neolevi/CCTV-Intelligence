import {
  AuthResponse,
  CameraDevice,
  CameraStatus,
  MotionStatus,
  MotionStatistics,
  CapturedFrame,
  MotionEvent,
  MotionEventDetail,
  Recording,
  DailySummary,
  AnalyticsOverview,
  AnalyticsTrends,
  SystemSettings,
  User,
} from '../types';

const API_BASE = 'http://localhost:8000';

class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('cctv_auth_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('cctv_auth_token', token);
    } else {
      localStorage.removeItem('cctv_auth_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const headers = new Headers(options.headers || {});

    if (this.token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.setToken(null);
      window.dispatchEvent(new Event('auth:unauthorized'));
      throw new Error('Session expired. Please log in again.');
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status} Error`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // non-json response
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // --- Auth APIs ---
  async login(email: string, password: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async register(email: string, password: string, fullName?: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/api/auth/me');
  }

  logout() {
    this.setToken(null);
  }

  // --- Camera APIs ---
  async getCameraDevices(): Promise<CameraDevice[]> {
    return this.request<CameraDevice[]>('/api/camera/devices');
  }

  async getCameraStatus(): Promise<CameraStatus> {
    return this.request<CameraStatus>('/api/camera/status');
  }

  async startMonitoring(cameraId: number = 1, deviceIndex: number = 0): Promise<{ message: string; status: CameraStatus }> {
    return this.request('/api/camera/start', {
      method: 'POST',
      body: JSON.stringify({ camera_id: cameraId, device_index: deviceIndex }),
    });
  }

  async stopMonitoring(): Promise<{ message: string; status: CameraStatus }> {
    return this.request('/api/camera/stop', {
      method: 'POST',
    });
  }

  async triggerSimulatedMotion(active: boolean): Promise<any> {
    return this.request('/api/camera/trigger_motion', {
      method: 'POST',
      body: JSON.stringify({ active }),
    });
  }

  getLiveStreamUrl(): string {
    return `${API_BASE}/api/camera/stream?t=${Date.now()}`;
  }

  // --- Motion APIs ---
  async getMotionStatus(): Promise<MotionStatus> {
    return this.request<MotionStatus>('/api/motion/status');
  }

  async getMotionStatistics(): Promise<MotionStatistics> {
    return this.request<MotionStatistics>('/api/motion/statistics');
  }

  // --- Frames APIs ---
  async listFrames(params?: { skip?: number; limit?: number; activity_state?: string; event_id?: number }): Promise<CapturedFrame[]> {
    const q = new URLSearchParams();
    if (params?.skip !== undefined) q.set('skip', params.skip.toString());
    if (params?.limit !== undefined) q.set('limit', params.limit.toString());
    if (params?.activity_state) q.set('activity_state', params.activity_state);
    if (params?.event_id) q.set('event_id', params.event_id.toString());
    return this.request<CapturedFrame[]>(`/api/frames?${q.toString()}`);
  }

  getFrameImageUrl(frameId: number): string {
    return `${API_BASE}/api/frames/${frameId}/image`;
  }

  async deleteFrame(frameId: number): Promise<{ message: string }> {
    return this.request(`/api/frames/${frameId}`, { method: 'DELETE' });
  }

  // --- Events APIs ---
  async listEvents(params?: { skip?: number; limit?: number; date?: string; activity_state?: string; search?: string }): Promise<MotionEvent[]> {
    const q = new URLSearchParams();
    if (params?.skip !== undefined) q.set('skip', params.skip.toString());
    if (params?.limit !== undefined) q.set('limit', params.limit.toString());
    if (params?.date) q.set('date', params.date);
    if (params?.activity_state) q.set('activity_state', params.activity_state);
    if (params?.search) q.set('search', params.search);
    return this.request<MotionEvent[]>(`/api/events?${q.toString()}`);
  }

  async getEventDetail(eventId: number): Promise<MotionEventDetail> {
    return this.request<MotionEventDetail>(`/api/events/${eventId}`);
  }

  getEventThumbnailUrl(eventId: number): string {
    return `${API_BASE}/api/events/${eventId}/thumbnail`;
  }

  async deleteEvent(eventId: number): Promise<{ message: string }> {
    return this.request(`/api/events/${eventId}`, { method: 'DELETE' });
  }

  // --- Recordings APIs ---
  async listRecordings(params?: { skip?: number; limit?: number; date?: string; activity_state?: string }): Promise<Recording[]> {
    const q = new URLSearchParams();
    if (params?.skip !== undefined) q.set('skip', params.skip.toString());
    if (params?.limit !== undefined) q.set('limit', params.limit.toString());
    if (params?.date) q.set('date', params.date);
    if (params?.activity_state) q.set('activity_state', params.activity_state);
    return this.request<Recording[]>(`/api/recordings?${q.toString()}`);
  }

  getRecordingStreamUrl(recordingId: number): string {
    return `${API_BASE}/api/recordings/${recordingId}/stream`;
  }

  getRecordingDownloadUrl(recordingId: number): string {
    return `${API_BASE}/api/recordings/${recordingId}/download`;
  }

  getRecordingThumbnailUrl(recordingId: number): string {
    return `${API_BASE}/api/recordings/${recordingId}/thumbnail`;
  }

  async deleteRecording(recordingId: number): Promise<{ message: string }> {
    return this.request(`/api/recordings/${recordingId}`, { method: 'DELETE' });
  }

  // --- Daily Summary APIs ---
  async getDailySummary(date?: string): Promise<DailySummary> {
    const endpoint = date ? `/api/summaries/daily?date=${date}` : '/api/summaries/daily';
    return this.request<DailySummary>(endpoint);
  }

  async generateDailySummary(date: string): Promise<DailySummary> {
    return this.request<DailySummary>(`/api/summaries/generate/${date}`, { method: 'POST' });
  }

  getSummaryDownloadUrl(date: string): string {
    return `${API_BASE}/api/summaries/${date}/download`;
  }

  // --- Analytics APIs ---
  async getAnalyticsOverview(): Promise<AnalyticsOverview> {
    return this.request<AnalyticsOverview>('/api/analytics/overview');
  }

  async getAnalyticsTrends(days: number = 7): Promise<AnalyticsTrends> {
    return this.request<AnalyticsTrends>(`/api/analytics/trends?days=${days}`);
  }

  // --- Settings APIs ---
  async getSettings(): Promise<SystemSettings> {
    return this.request<SystemSettings>('/api/settings');
  }

  async updateSettings(settings: Partial<SystemSettings>): Promise<SystemSettings> {
    return this.request<SystemSettings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }
}

export const api = new ApiService();
