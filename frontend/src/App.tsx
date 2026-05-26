import { useState } from "react";

import { getGuardRecommendation, login, type GuardRecommendationResponse } from "./api";

const DEMO_CREDENTIALS = {
  username: "operador",
  password: "rainops-dev",
} as const;

function getTomorrowIsoDate(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow.toISOString().slice(0, 10);
}

export function App() {
  const [username, setUsername] = useState<string>(DEMO_CREDENTIALS.username);
  const [password, setPassword] = useState<string>(DEMO_CREDENTIALS.password);
  const [token, setToken] = useState<string | null>(null);
  const [targetDate, setTargetDate] = useState(getTomorrowIsoDate());
  const [result, setResult] = useState<GuardRecommendationResponse | null>(null);
  const [message, setMessage] = useState("Sistema listo para probar el flujo end-to-end.");

  async function handleLogin() {
    try {
      const data = await login(username, password);
      setToken(data.access_token);
      setMessage(`Sesión iniciada como ${data.user.full_name}`);
    } catch (error) {
      setToken(null);
      setMessage(error instanceof Error ? error.message : "Error inesperado al iniciar sesión");
    }
  }

  async function handleRecommendation() {
    if (!token) {
      setMessage("Primero tenés que iniciar sesión. Sin token no hay predicción, BIEN ahí la seguridad.");
      return;
    }

    try {
      const recommendation = await getGuardRecommendation(token, targetDate);
      setResult(recommendation);
      setMessage("Recomendación generada correctamente.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Error inesperado al consultar la API");
    }
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">ML-RainOps · CEML</p>
          <h1>Predicción de lluvia para planificación de guardias</h1>
        </div>
        <p>
          Flujo mínimo para validar autenticación, consulta protegida y recomendación operativa. Todavía usa una
          respuesta simulada: primero cerramos el circuito, después conectamos SMN, modelo y MLflow.
        </p>
      </section>

      <section className="dashboard-grid">
        <article className="card">
          <h2>1. Iniciar sesión</h2>
          <label>
            Usuario
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            Contraseña
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button onClick={handleLogin}>Obtener token</button>
          <p className="hint">Credenciales demo: operador / rainops-dev</p>
        </article>

        <article className="card">
          <h2>2. Consultar guardia</h2>
          <label>
            Fecha objetivo
            <input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
          </label>
          <button onClick={handleRecommendation}>Generar recomendación</button>
          <p className="hint">Este endpoint exige JWT. Sin login, responde 401.</p>
        </article>

        <article className="card result-card">
          <h2>3. Resultado</h2>
          <p className="status-message">{message}</p>
          {result ? (
            <>
              <dl className="result-summary">
                <div>
                  <dt>Guardia</dt>
                  <dd>{result.recommended_guard}</dd>
                </div>
                <div>
                  <dt>Prob. lluvia</dt>
                  <dd>{Math.round(result.local_model.rain_probability * 100)}%</dd>
                </div>
                <div>
                  <dt>SMN</dt>
                  <dd>{result.smn.daily_precipitation_mm} mm</dd>
                </div>
                <div>
                  <dt>Estación</dt>
                  <dd>{result.smn.reference_station}</dd>
                </div>
              </dl>
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </>
          ) : (
            <p className="hint">Todavía no hay recomendación generada.</p>
          )}
        </article>
      </section>
    </main>
  );
}
