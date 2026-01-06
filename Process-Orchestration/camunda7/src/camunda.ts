import 'dotenv/config';

export interface CamundaAuthConfig {
  username: string;
  password: string;
}

export const CAMUNDA_ENGINE_URL =
  process.env.CAMUNDA_ENGINE_URL || 'http://localhost:8080/engine-rest';

export function getCamundaAuth(): CamundaAuthConfig | undefined {
  const username = process.env.CAMUNDA_BASIC_AUTH_USER;
  const password = process.env.CAMUNDA_BASIC_AUTH_PASSWORD;

  if (username && password) {
    return { username, password };
  }

  return undefined;
}


