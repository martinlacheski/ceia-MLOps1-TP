const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export const GUARD_RECOMMENDATION_MODE = {
  MODEL_ARTIFACT_AND_SMN: "model_artifact_and_smn",
  MODEL_ARTIFACT_ONLY_FALLBACK: "model_artifact_only_fallback",
  SMN_ONLY_FALLBACK: "smn_only_fallback",
  DEGRADED_FALLBACK: "degraded_fallback",
} as const;

export const RISK_LEVEL = {
  LOW: "bajo",
  MEDIUM: "medio",
  HIGH: "alto",
} as const;

type GuardRecommendationMode =
  (typeof GUARD_RECOMMENDATION_MODE)[keyof typeof GUARD_RECOMMENDATION_MODE];
type RiskLevel = (typeof RISK_LEVEL)[keyof typeof RISK_LEVEL];

export interface AuthenticatedUser {
  username: string;
  full_name: string;
  permissions: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthenticatedUser;
}

interface RainPredictionSignal {
  source: string;
  model_name: string;
  model_stage: string;
  rain_probability: number;
  threshold: number;
  will_rain: boolean;
}

interface ForecastSignal {
  source: string;
  reference_station: string;
  precipitation_mm: number;
  will_rain: boolean;
}

interface OperationalDecision {
  recommended_guard: string;
  risk_level: RiskLevel;
  reason: string;
}

interface RecommendationMetadata {
  generated_at: string;
  mode: GuardRecommendationMode;
  training_summary_path: string;
  serving_artifact_path: string;
  smn_data_path: string;
  degradation_reasons: string[];
}

export interface GuardRecommendationResponse {
  target_date: string;
  prediction: RainPredictionSignal;
  forecast: ForecastSignal;
  decision: OperationalDecision;
  metadata: RecommendationMetadata;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const formData = new URLSearchParams();
  formData.set("username", username);
  formData.set("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData,
  });

  if (!response.ok) {
    throw new Error("No se pudo iniciar sesión");
  }

  return response.json();
}

export async function getGuardRecommendation(
  token: string,
  targetDate: string,
): Promise<GuardRecommendationResponse> {
  const response = await fetch(`${API_BASE_URL}/predictions/guard-recommendation`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ target_date: targetDate }),
  });

  if (!response.ok) {
    throw new Error("No se pudo obtener la recomendación");
  }

  return response.json();
}
