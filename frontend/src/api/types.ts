export type ReportType = 'lost' | 'found'
export type ReportStatus = 'open' | 'recovered' | 'closed' | string
export type ModelState = 'idle' | 'warming' | 'ready' | 'mock' | 'failed'

export interface User {
  id: string
  email: string
  display_name: string
  /** Hex color for the avatar chip; optional until the API exposes it. */
  avatar?: string
}

/** One-tap demo persona from GET /api/auth/demo-accounts. Password is always `demo`. */
export interface DemoAccount {
  name: string
  email: string
  avatar: string
  summary: string
}

export interface LocationPin {
  id?: string
  latitude: number
  longitude: number
  radius_meters: number
}

export interface Report {
  id: string
  report_type: ReportType
  description: string
  category?: string | null
  urgency?: string | null
  created_at?: string
  event_time: string
  latitude?: number | null
  longitude?: number | null
  radius_meters?: number | null
  locations: LocationPin[]
  status: ReportStatus
  prefer_anonymous: boolean
  holding_note?: string | null
  image_urls: string[]
  contact_email?: string | null
  contact_phone?: string | null
  /** Positive undismissed matches; present on GET /api/reports?scope=mine. */
  match_count?: number
}

export interface ClassificationResult {
  category?: string | null
  urgency?: string | null
  is_mock?: boolean
  [key: string]: unknown
}

export interface VisualEvidence {
  shortlisted: boolean
  dino_score?: number | null
  inliers?: number | null
  inlier_ratio?: number | null
  /** When true, photos are treated as the same object even if inliers < 4. */
  same_object?: boolean | null
}

export interface MatchItem {
  overall_score: number
  text_score?: number | null
  image_score?: number | null
  category_score?: number | null
  geo_score?: number | null
  time_score?: number | null
  distance_meters?: number | null
  image_error?: string | null
  gate_reason?: string | null
  visual?: VisualEvidence | null
  lost: Report
  found: Report
}

/** Response from GET /api/matches?report_id= */
export interface MatchesResponse {
  status: 'ready' | 'computing'
  anchor?: Report
  matches: MatchItem[]
}

export interface HealthModels {
  classifier: ModelState
  text: ModelState
  dino: ModelState
  features: ModelState
  segmenter: ModelState
}

export interface HealthResponse {
  status: string
  mock_ml: boolean
  device?: string
  image_backend?: string
  models: HealthModels
  demo_reset_allowed?: boolean
}

/** One in-app match alert from GET /api/notifications. */
export interface MatchNotification {
  id: string
  kind: string
  lost_report_id: string
  found_report_id: string
  overall_score: number
  created_at: string
  read_at?: string | null
  /** Viewer's own report this alert is about, when the API sends it. */
  report_id?: string | null
  lost?: Report | null
  found?: Report | null
}

export interface NotificationsResponse {
  notifications: MatchNotification[]
  unread_count: number
}

export interface NotificationReadResponse {
  notification: MatchNotification
  unread_count: number
}

export interface Preset {
  id: string
  label: string
  report_type: ReportType
  description: string
  latitude: number
  longitude: number
  radius_meters: number
  image_url: string
}

export interface Meetup {
  id?: string
  match_id?: string
  location_name: string
  meeting_time: string
  status: 'proposed' | 'accepted' | 'declined' | string
  proposed_by?: 'lost' | 'found' | string
}

export interface CoordinationMessage {
  id?: string
  sender: 'lost' | 'found' | string
  message: string
  created_at?: string
}

/** Contact the API is willing to show the viewer; null when the other party is anonymous. */
export interface OtherContact {
  email?: string | null
  phone?: string | null
}

export interface CoordinationPayload {
  role: 'lost' | 'found'
  lost: Report
  found: Report
  other_contact: OtherContact | null
  /** Display name of the other party when the API chooses to expose it. */
  other_name?: string | null
  meetup: Meetup | null
  messages: CoordinationMessage[]
  recovered: boolean
}

export type MeetupStatus = 'none' | 'proposed' | 'accepted' | 'declined'

/** One active pickup thread from GET /api/coordination. */
export interface CoordinationThread {
  lost: Report
  found: Report
  role: 'lost' | 'found'
  meetup_status: MeetupStatus
  last_message: string | null
  recovered: boolean
}

export interface ApiErrorBody {
  detail?: string
}
