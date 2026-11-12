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
  start_date: string | null;
  origin: string | null;
  selected_accommodation_index: number | null;
  selected_flight_index: number | null;
  traveler_count: number;
}

export interface FlightOffer {
  price: string | null;
  price_raw: number | null;
  currency: string;
  airline: string | null;
  duration_minutes: number | null;
  stops: number | null;
  origin: string | null;
  destination: string | null;
  departure: string | null;
  arrival: string | null;
  source: "real";
  origin_query?: string;
  destination_query?: string;
}

export const RECOMMENDATION_TAGS = ["best_overall", "cheapest", "fastest", "best_value", "most_convenient"] as const;
export type RecommendationTag = (typeof RECOMMENDATION_TAGS)[number];

export interface ScoredFlightOffer {
  index: number;
  total_price: number | null;
  within_budget: boolean;
  duration_minutes: number | null;
  stops: number | null;
  price_per_hour: number | null;
  composite_score: number;
}

export interface FlightRecommendations {
  offers: ScoredFlightOffer[];
  recommended: Partial<Record<RecommendationTag, number>>;
  labels: Record<RecommendationTag, string>;
  reasons: Partial<Record<RecommendationTag, string>>;
  weights: Record<string, number>;
  traveler_count: number;
  max_flight_budget: number | null;
  any_in_budget: boolean;
  assumptions: string[];
}

export interface BudgetAllocation {
  total_budget: number;
  committed_amount: number;
  remaining_after_committed: number;
  budget_level: string;
  traveler_count: number;
  days: number;
  allocation: Record<string, number>;
  per_traveler: Record<string, number>;
  per_day: Record<string, number>;
  capped_categories: string[];
  basis: "estimated";
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
  cuisine?: string;
  price_range?: string;
  location?: string;
  neighborhood?: string;
  reservation?: string;
  description?: string;
  source?: "real" | "llm";
  [key: string]: unknown;
}

export interface Accommodation {
  name: string;
  type?: string;
  location?: string;
  neighborhood?: string;
  price_per_night?: string;
  price_raw?: number | null;
  currency?: string;
  rating?: string;
  amenities?: string[];
  highlights?: string[];
  source?: "real" | "llm";
  [key: string]: unknown;
}

export interface DayActivity {
  time: string;
  type: "attraction" | "meal";
  name: string;
  description?: string;
  duration?: string;
  duration_minutes?: number;
  travel_time_before_minutes?: number;
  /** "estimated" - this agent computed it; "unscheduled" - no scheduling data at all, never a real booking slot. */
  time_source?: "estimated" | "unscheduled";
  booking_status?: "not_booked";
  /** "conflict" - estimated start runs past a reasonable day-end hour, or past midnight. */
  scheduling_status?: "ok" | "conflict";
  category?: string;
  meal_type?: string;
  cuisine?: string;
  price_range?: string;
  coordinates?: { lat: number; lng: number } | null;
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

export interface TransportationRoute {
  mode: "driving";
  from: string;
  to: string;
  distance_km: number;
  duration_h: number;
  geometry: [number, number][];
  source: "real";
}

export type TransportMode = "walk" | "cycle" | "taxi_or_transit" | "dedicated_transfer";

export interface AirportTransferRecommendation extends TransportationRoute {
  recommended_mode: TransportMode;
  reason: string;
}

export interface LocalTransportHop {
  day: number;
  from: string | null;
  to: string | null;
  distance_km: number;
  duration_h: number | null;
  recommended_mode: TransportMode;
  reason: string;
  source: "real";
}

export interface TransportRecommendations {
  airport_transfer: AirportTransferRecommendation | null;
  local_transport: LocalTransportHop[];
  intercity_transport: null;
  assumptions: string[];
}

export const ACCOMMODATION_RECOMMENDATION_TAGS = ["best_overall", "cheapest", "highest_rated", "best_value", "most_central"] as const;
export type AccommodationRecommendationTag = (typeof ACCOMMODATION_RECOMMENDATION_TAGS)[number];

export interface ScoredAccommodationOffer {
  index: number;
  price_per_night: number;
  total_price: number;
  within_budget: boolean;
  rating: number | null;
  distance_km: number | null;
  value_score: number | null;
  composite_score: number;
}

export interface AccommodationRecommendations {
  offers: ScoredAccommodationOffer[];
  recommended: Partial<Record<AccommodationRecommendationTag, number>>;
  labels: Record<AccommodationRecommendationTag, string>;
  reasons: Partial<Record<AccommodationRecommendationTag, string>>;
  weights: Record<string, number>;
  nights: number;
  max_nightly_budget: number | null;
  any_in_budget: boolean;
  assumptions: string[];
}

export interface TripPlan {
  attractions: Attraction[];
  itinerary: ItineraryResult;
  restaurants: Restaurant[];
  accommodations: Accommodation[];
  flights?: FlightOffer[];
  transportation?: TransportationRoute | null;
}

export interface TraceEntry {
  step: string;
  duration_ms: number;
  status: "success" | "error" | "skipped";
  error?: string;
}

export interface WorkflowStep {
  id: string;
  label: string;
  agent: string;
  description: string;
  always_runs: boolean;
}

export interface WorkflowsResponse {
  frameworks: FrameworkInfo[];
  steps: WorkflowStep[];
  edges: [string, string][];
}

export interface TripDetail extends TripSummary {
  dietary_preferences: string[];
  plan: TripPlan | null;
  errors: string[];
  budget_amount: number | null;
  max_flight_budget_amount: number | null;
  max_transport_budget_amount: number | null;
  model: string | null;
  framework: string | null;
  trace: TraceEntry[];
  share_token: string | null;
  budget_allocation: BudgetAllocation | null;
  flight_recommendations: FlightRecommendations | null;
  transport_recommendations: TransportRecommendations | null;
  accommodation_recommendations: AccommodationRecommendations | null;
}

export interface TripCreateRequest {
  destination: string;
  days: number;
  trip_type: string;
  budget: string;
  dietary_preferences: string[];
  model?: string;
  framework?: string;
  start_date?: string;
  origin?: string;
  traveler_count?: number;
  max_flight_budget_amount?: number;
  max_transport_budget_amount?: number;
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

export interface PlaceSuggestion {
  title?: string;
  subtitle?: string;
  sky_id?: string;
  entity_id?: string;
  type?: string;
  dest_id?: string;
  search_type?: string;
  label?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
}

export interface FlightOffer {
  price: string | null;
  price_raw: number | null;
  currency: string;
  airline: string | null;
  duration_minutes: number | null;
  stops: number | null;
  origin: string | null;
  destination: string | null;
  departure: string | null;
  arrival: string | null;
}

export interface HotelOffer {
  hotel_id: number | null;
  name: string | null;
  price_formatted: string | null;
  price_raw: number | null;
  currency: string;
  review_score: number | null;
  review_score_word: string | null;
  star_rating: number | null;
  photo_url: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface WeatherDay {
  date: string;
  temp_min: number;
  temp_max: number;
  description: string | null;
  icon: string | null;
}

export interface WeatherForecast {
  location: { name: string; country: string | null };
  days: WeatherDay[];
}

export interface CurrencyConversion {
  amount: number;
  from: string;
  to: string;
  rate: number;
  converted: number;
  date: string | null;
  source: "real";
}

export interface CurrencyRates {
  base: string;
  date: string | null;
  rates: Record<string, number>;
  source: "real";
}

export interface MapPlace {
  label: string | null;
  lat: number;
  lng: number;
}

export interface MapRoute {
  distance_km: number;
  duration_h: number;
  geometry: [number, number][];
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
