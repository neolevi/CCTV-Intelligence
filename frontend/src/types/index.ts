export interface User {
  id: number;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CameraDevice {
  index: number;
  name: string;
  is_available: boolean;
}

export interface CameraStatus {
  is_connected: boolean;
  is_monitoring: boolean;
  camera_id?: number;
  camera_name?: string;
  device_index?: number;
  is_virtual_camera?: boolean;
  current_fps: number;
  activity_state: 'ACTIVE' | 'IDLE' | 'DEEP_IDLE' | string;
  sampling_fps: number;
  uptime_seconds: number;
  total_frames_processed: number;
  total_frames_saved: number;
  motion_score: number;
  is_motion_detected: boolean;
  active_seconds?: number;
  idle_seconds?: number;
  deep_idle_seconds?: number;
}

export interface MotionStatus {
  activity_state: string;
  motion_score: number;
  is_motion_detected: boolean;
  sampling_fps: number;
  time_in_current_state: number;
  active_timeout_remaining: number;
}

export interface MotionStatistics {
  active_percentage: number;
  idle_percentage: number;
  deep_idle_percentage: number;
  total_events_today: number;
  peak_motion_score_today: number;
}

export interface CapturedFrame {
  id: number;
  camera_id: number;
  session_id?: number;
  event_id?: number;
  timestamp: string;
  activity_state: string;
  file_path: string;
  motion_score: number;
}

export interface MotionEvent {
  id: number;
  camera_id: number;
  session_id?: number;
  start_time: string;
  end_time?: string;
  peak_motion_score: number;
  activity_state: string;
  frame_count: number;
  thumbnail_path?: string;
  description?: string;
}

export interface MotionEventDetail extends MotionEvent {
  frames: CapturedFrame[];
}

export interface Recording {
  id: number;
  camera_id: number;
  session_id?: number;
  event_id?: number;
  start_time: string;
  end_time?: string;
  duration_seconds: number;
  file_path: string;
  file_size_bytes: number;
  thumbnail_path?: string;
  activity_state: string;
}

export interface TimelineSegment {
  start_time: string;
  end_time: string;
  activity_state: 'ACTIVE' | 'IDLE' | 'DEEP_IDLE' | 'OFFLINE' | string;
  duration_seconds: number;
  event_count: number;
}

export interface HourlyActivity {
  hour: number;
  label: string;
  event_count: number;
  active_minutes: number;
}

export interface DailySummary {
  id?: number;
  date: string;
  total_monitoring_seconds: number;
  active_seconds: number;
  idle_seconds: number;
  deep_idle_seconds: number;
  total_motion_events: number;
  total_frames_captured: number;
  total_frames_saved: number;
  storage_consumed_bytes: number;
  first_activity_time?: string;
  last_activity_time?: string;
  peak_activity_hour?: number;
  narrative_summary?: string;
  timeline_segments: TimelineSegment[];
  hourly_distribution: HourlyActivity[];
  important_events: MotionEvent[];
  events?: MotionEvent[];
}

export interface DailySummaryDateItem {
  date: string;
  total_events: number;
  active_seconds: number;
  total_monitoring_seconds: number;
  storage_consumed_bytes: number;
  has_summary: boolean;
}

export interface AnalyticsOverview {
  today_active_seconds: number;
  today_idle_seconds: number;
  today_deep_idle_seconds: number;
  total_motion_events_today: number;
  total_recordings_count: number;
  total_storage_used_bytes: number;
  total_monitoring_hours_week: number;
  active_ratio_today: number;
}

export interface AnalyticsTrends {
  dates: string[];
  active_durations: number[];
  idle_durations: number[];
  deep_idle_durations: number[];
  motion_event_counts: number[];
  storage_trend_bytes: number[];
}

export interface SystemSettings {
  motion_sensitivity: number;
  motion_threshold_percent: number;
  idle_timeout_seconds: number;
  deep_idle_timeout_seconds: number;
  active_sampling_fps: number;
  idle_sampling_fps: number;
  deep_idle_sampling_fps: number;
  storage_retention_days: number;
  theme: string;
  default_camera_index: number;
  resolution_width: number;
  resolution_height: number;
  storage_path: string;
  storage_used_bytes: number;
  storage_free_bytes: number;
}
