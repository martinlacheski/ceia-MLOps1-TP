import { useState } from "react";

import {
  getGuardRecommendation,
  login,
  type AuthenticatedUser,
  type GuardRecommendationResponse,
} from "./api";

const DEMO_CREDENTIALS = {
  username: "operador",
  password: "rainops-dev",
} as const;

const VIEW = {
  LOGIN: "login",
  CONSULTATION: "consultation",
} as const;

const GUARD_SUMMARY_TITLE = {
  reforzada: "Guardia reforzada recomendada",
  preventiva: "Guardia preventiva recomendada",
  normal: "Guardia normal recomendada",
} as const;

const RISK_TONE = {
  bajo: "risk-low",
  medio: "risk-medium",
  alto: "risk-high",
} as const;

type View = (typeof VIEW)[keyof typeof VIEW];

interface SessionState {
  token: string;
  user: AuthenticatedUser;
}

function getTomorrowIsoDate(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow.toISOString().slice(0, 10);
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatPercentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatMode(mode: string): string {
  return mode.replaceAll("_", " ");
}

function getSummaryTitle(recommendedGuard: string): string {
  return GUARD_SUMMARY_TITLE[recommendedGuard as keyof typeof GUARD_SUMMARY_TITLE] ??
    `Guardia ${recommendedGuard} recomendada`;
}

export function App() {
  const [username, setUsername] = useState<string>(DEMO_CREDENTIALS.username);
  const [password, setPassword] = useState<string>(DEMO_CREDENTIALS.password);
  const [session, setSession] = useState<SessionState | null>(null);
  const [targetDate, setTargetDate] = useState(getTomorrowIsoDate());
  const [result, setResult] = useState<GuardRecommendationResponse | null>(null);
  const [message, setMessage] = useState("Sistema listo para probar el flujo end-to-end.");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showJson, setShowJson] = useState(false);

  const currentView: View = session ? VIEW.CONSULTATION : VIEW.LOGIN;

  async function handleLogin() {
    setIsLoggingIn(true);

    try {
      const data = await login(username, password);
      setSession({ token: data.access_token, user: data.user });
      setResult(null);
      setShowDetails(false);
      setShowJson(false);
      setMessage(`Sesión iniciada como ${data.user.full_name}`);
    } catch (error) {
      setSession(null);
      setMessage(error instanceof Error ? error.message : "Error inesperado al iniciar sesión");
    } finally {
      setIsLoggingIn(false);
    }
  }

  function handleLogout() {
    setSession(null);
    setResult(null);
    setShowDetails(false);
    setShowJson(false);
    setMessage("Sesión cerrada. Podés volver a iniciar sesión para generar una nueva consulta.");
  }

  async function handleRecommendation() {
    if (!session) {
      setMessage("Primero debés iniciar sesión para consultar la recomendación.");
      return;
    }

    setIsGenerating(true);

    try {
      const recommendation = await getGuardRecommendation(session.token, targetDate);
      setResult(recommendation);
      setShowDetails(false);
      setShowJson(false);
      setMessage("Recomendación generada correctamente.");
    } catch (error) {
      setResult(null);
      setMessage(error instanceof Error ? error.message : "Error inesperado al consultar la API");
    } finally {
      setIsGenerating(false);
    }
  }

  if (currentView === VIEW.LOGIN) {
    return (
      <main className="page-shell login-shell">
        <section className="login-card hero-card">
          <div className="hero-copy">
            <p className="eyebrow">ML-RainOps · CEML</p>
            <h1>Predicción de lluvia para planificación de guardias</h1>
            <p>
              Iniciá sesión para acceder a la consulta protegida y revisar una recomendación operativa basada en el
              modelo local y el pronóstico del SMN.
            </p>
          </div>

          <article className="card form-card">
            <h2>Ingresar al demo</h2>
            <label>
              Usuario
              <input value={username} onChange={(event) => setUsername(event.target.value)} />
            </label>
            <label>
              Contraseña
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <button onClick={handleLogin} disabled={isLoggingIn}>
              {isLoggingIn ? "Ingresando..." : "Iniciar sesión"}
            </button>
            <p className="hint">Credenciales demo: operador / rainops-dev</p>
            <p className="status-message">{message}</p>
          </article>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell consultation-shell">
      <section className="consultation-header hero-card">
        <div className="hero-copy">
          <p className="eyebrow">ML-RainOps · CEML</p>
          <h1>Predicción de lluvia para planificación de guardias</h1>
          <p>Generá una recomendación operativa protegida por sesión autenticada.</p>
        </div>
        <div className="session-panel">
          <div className="session-chip">
            <span className="session-chip-label">Sesión activa</span>
            <strong>{session?.user.full_name}</strong>
            <span>{session?.user.username}</span>
          </div>
          <button className="secondary-button" onClick={handleLogout}>
            Cerrar sesión
          </button>
        </div>
      </section>

      <section className="consultation-grid">
        <article className="card consultation-card">
          <h2>Consultar guardia</h2>
          <label>
            Fecha objetivo
            <input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
          </label>
          <button onClick={handleRecommendation} disabled={isGenerating}>
            {isGenerating ? "Generando..." : "Generar recomendación"}
          </button>
          <p className="hint">La consulta usa JWT y accede al contrato unificado de modelo local + SMN.</p>
          <p className="status-message">{message}</p>
        </article>

        <article className="card result-card">
          <h2>Resultado operativo</h2>
          {result ? (
            <>
              <section className={`summary-card ${RISK_TONE[result.decision.risk_level]}`}>
                <p className="summary-eyebrow">Recomendación</p>
                <h3>{getSummaryTitle(result.decision.recommended_guard)}</h3>
                <div className="summary-meta">
                  <span>Riesgo {result.decision.risk_level}</span>
                  <span>Probabilidad de lluvia {formatPercentage(result.prediction.rain_probability)}</span>
                </div>
                <p>{result.decision.reason}</p>
              </section>

              <dl className="result-summary">
                <div>
                  <dt>Fecha</dt>
                  <dd>{result.target_date}</dd>
                </div>
                <div>
                  <dt>Prob. lluvia</dt>
                  <dd>{formatPercentage(result.prediction.rain_probability)}</dd>
                </div>
                <div>
                  <dt>SMN</dt>
                  <dd>{result.forecast.precipitation_mm} mm</dd>
                </div>
                <div>
                  <dt>Riesgo</dt>
                  <dd>{capitalize(result.decision.risk_level)}</dd>
                </div>
              </dl>

              <button className="secondary-button" onClick={() => setShowDetails((value) => !value)}>
                {showDetails ? "Ocultar detalle" : "Ver detalle"}
              </button>

              {showDetails ? (
                <section className="details-card">
                  <div className="detail-section">
                    <h3>Modelo local</h3>
                    <p>
                      {result.prediction.model_name} ({result.prediction.model_stage}) reporta
                      {` ${formatPercentage(result.prediction.rain_probability)}`} de probabilidad de lluvia con umbral
                      operativo de {formatPercentage(result.prediction.threshold)}.
                    </p>
                  </div>

                  <div className="detail-section">
                    <h3>SMN</h3>
                    <p>
                      La estación {result.forecast.reference_station} informa {result.forecast.precipitation_mm} mm
                      esperados y señal de lluvia {result.forecast.will_rain ? "positiva" : "negativa"}.
                    </p>
                  </div>

                  <div className="detail-section">
                    <h3>Decisión</h3>
                    <p>
                      Se recomienda guardia {result.decision.recommended_guard} con riesgo
                      {` ${result.decision.risk_level}`} porque {result.decision.reason.toLowerCase()}
                    </p>
                  </div>

                  <div className="detail-section">
                    <h3>Trazabilidad</h3>
                    <p>Modo de respuesta: {formatMode(result.metadata.mode)}.</p>
                    <p>Generado en: {result.metadata.generated_at}.</p>
                    <p>Resumen de entrenamiento: {result.metadata.training_summary_path}.</p>
                    <p>Artefacto servido: {result.metadata.serving_artifact_path}.</p>
                    <p>Fuente SMN: {result.metadata.smn_data_path}.</p>
                    <p>
                      Degradaciones: {result.metadata.degradation_reasons.length > 0
                        ? result.metadata.degradation_reasons.join(" · ")
                        : "sin degradaciones reportadas"}.
                    </p>
                  </div>

                  <button className="secondary-button" onClick={() => setShowJson((value) => !value)}>
                    {showJson ? "Ocultar JSON" : "Ver JSON"}
                  </button>

                  {showJson ? <pre className="json-box">{JSON.stringify(result, null, 2)}</pre> : null}
                </section>
              ) : null}
            </>
          ) : (
            <div className="empty-state">
              <p className="status-message">Todavía no hay recomendación generada.</p>
              <p className="hint">Seleccioná una fecha y ejecutá la consulta para ver el resumen operativo.</p>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}
