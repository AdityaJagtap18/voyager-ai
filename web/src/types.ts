export const TRIP_TYPES = [
  "historic",
  "adventure",
  "relaxation",
  "foodie",
  "cultural",
  "romantic",
  "nature",
] as const;

export const BUDGET_LEVELS = ["budget", "mid-range", "premium"] as const;

export type TripType = (typeof TRIP_TYPES)[number];
export type BudgetLevel = (typeof BUDGET_LEVELS)[number];

export type TripStatus = "planning" | "complete" | "failed";

export interface TripSummary {
  id: string;
  destination: string;
  days: number;
  trip_type: string;
  budget: string;
  status: TripStatus;
  created_at: string;
}

export interface Attraction {
  name: string;
  description?: string;
  category?: string;
  duration?: string;
  best_time?: string;
}

export interface Restaurant {
  name: string;
  [key: string]: unknown;
}

export interface Accommodation {
  name: string;
  [key: string]: unknown;
}

export interface DayActivity {
  time: string;
  type: "attraction" | "meal";
  name: string;
  description?: string;
  duration?: string;
  category?: string;
  meal_type?: string;
  cuisine?: string;
  price_range?: string;
}

export interface DayPlan {
  day: number;
  theme: string;
  start_time?: string;
  end_time?: string;
  activities: DayActivity[];
  total_activities: number;
  total_meals: number;
  total_travel_time_hours?: number;
  warnings?: string[];
}

export interface ItineraryResult {
  itinerary: DayPlan[];
  summary?: {
    total_days: number;
    total_attractions: number;
    total_meals_planned: number;
    total_travel_hours: number;
  };
  travel_tips?: string[];
  packing_suggestions?: string[];
}

export interface TripPlan {
  attractions: Attraction[];
  itinerary: ItineraryResult;
  restaurants: Restaurant[];
  accommodations: Accommodation[];
}

export interface TraceEntry {
  step: string;
  duration_ms: number;
  status: "success" | "error";
  error?: string;
}

export interface TripDetail extends TripSummary {
  dietary_preferences: string[];
  plan: TripPlan | null;
  errors: string[];
  budget_amount: number | null;
  model: string | null;
  framework: string | null;
  trace: TraceEntry[];
  share_token: string | null;
}

export interface TripCreateRequest {
  destination: string;
  days: number;
  trip_type: string;
  budget: string;
  dietary_preferences: string[];
  model?: string;
  framework?: string;
}

export interface ModelInfo {
  id: string;
  label: string;
  provider: string;
  context_window: number;
  local: boolean;
  configured: boolean;
}

export interface FrameworkInfo {
  id: string;
  label: string;
  description: string;
  available: boolean;
}

export interface AgentInfo {
  id: string;
  name: string;
  role: string;
  goal: string;
  data_source: string;
}

export interface KnowledgeDocumentCreateRequest {
  destination: string;
  title: string;
  content: string;
}

export interface KnowledgeDocumentSummary {
  id: string;
  destination: string;
  title: string;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeSearchResult {
  document_id: string;
  document_title: string;
  destination: string;
  chunk_text: string;
  score: number;
}

export const BOOKING_TYPES = ["flight", "hotel", "activity", "other"] as const;
export const BOOKING_STATUSES = ["pending", "confirmed", "cancelled"] as const;
export const EXPENSE_CATEGORIES = [
  "flights",
  "accommodation",
  "food",
  "transport",
  "activities",
  "shopping",
  "misc",
] as const;

export interface Booking {
  id: string;
  trip_id: string;
  type: (typeof BOOKING_TYPES)[number];
  title: string;
  reference: string | null;
  status: (typeof BOOKING_STATUSES)[number];
  cost: number | null;
  notes: string | null;
  created_at: string;
}

export interface BookingCreateRequest {
  type: string;
  title: string;
  reference?: string;
  cost?: number;
  notes?: string;
}

export interface TripExpense {
  id: string;
  trip_id: string;
  category: (typeof EXPENSE_CATEGORIES)[number];
  description: string | null;
  amount: number;
  created_at: string;
}

export interface ExpenseCreateRequest {
  category: string;
  description?: string;
  amount: number;
}

export interface EvaluationRunRequest {
  model?: string;
  framework?: string;
}

export interface EvaluationCaseResult {
  case_id: string;
  description: string;
  passed: boolean;
  reason: string;
  duration_ms: number;
}

export interface EvaluationRunSummary {
  id: string;
  model: string | null;
  framework: string | null;
  pass_count: number;
  fail_count: number;
  created_at: string;
}

export interface EvaluationRunDetail extends EvaluationRunSummary {
  results: EvaluationCaseResult[];
}

export interface GuardrailScanResult {
  risk: "none" | "medium" | "high";
  categories: string[];
  matches: string[];
  blocked: boolean;
}

export interface GuardrailEventSummary {
  id: string;
  source: string;
  text_excerpt: string;
  risk: "none" | "medium" | "high";
  categories: string[];
  blocked: boolean;
  created_at: string;
}

export interface TripDocumentSummary {
  id: string;
  trip_id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  created_at: string;
}

export interface ShareLinkResponse {
  share_token: string;
}

export interface PublicTripView {
  destination: string;
  days: number;
  trip_type: string;
  budget: string;
  status: string;
  plan: TripPlan | null;
}
