const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

interface AuthenticatedUser {
  username: string;
  full_name: string;
  permissions: string[];
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthenticatedUser;
}

interface LocalModelSignal {
  rain_probability: number;
  will_rain: boolean;
}

interface SmnSignal {
  reference_station: string;
  daily_precipitation_mm: number;
  will_rain: boolean;
}

export interface GuardRecommendationResponse {
  predicted_date: string;
  local_model: LocalModelSignal;
  smn: SmnSignal;
  recommended_guard: string;
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
