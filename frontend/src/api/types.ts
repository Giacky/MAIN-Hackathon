export type ReportType = 'lost' | 'found'
export type ReportStatus = 'open' | 'recovered' | string
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
