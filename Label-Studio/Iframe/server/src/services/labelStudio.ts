import axios from 'axios';

const LABEL_STUDIO_URL = process.env.LABEL_STUDIO_URL || 'http://localhost:8080';

interface LoginResponse {
  token: string;
  csrfToken: string;
  sessionId: string;
  user: {
    id: number;
    email: string;
  };
}

/**
 * Authenticate with Label Studio using email/password
 * Returns the session token and CSRF token needed for subsequent requests
 */
export async function authenticateWithLabelStudio(
  email: string,
  password: string
): Promise<LoginResponse> {
  // First, get the CSRF token from the login page
  const loginPageResponse = await axios.get(`${LABEL_STUDIO_URL}/user/login/`, {
    withCredentials: true,
  });

  // Extract CSRF token from cookies
  const cookies = loginPageResponse.headers['set-cookie'] || [];
  let csrfToken = '';
  let sessionId = '';

  for (const cookie of cookies) {
    if (cookie.startsWith('csrftoken=')) {
      csrfToken = cookie.split(';')[0].split('=')[1];
    }
    if (cookie.startsWith('sessionid=')) {
      sessionId = cookie.split(';')[0].split('=')[1];
    }
  }

  // Perform login with CSRF token
  const loginResponse = await axios.post(
    `${LABEL_STUDIO_URL}/user/login/`,
    new URLSearchParams({
      email,
      password,
      csrfmiddlewaretoken: csrfToken,
    }),
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': `csrftoken=${csrfToken}`,
        'X-CSRFToken': csrfToken,
        'Referer': `${LABEL_STUDIO_URL}/user/login/`,
      },
      maxRedirects: 0,
      validateStatus: (status) => status >= 200 && status < 400,
    }
  );

  // Extract session cookie from login response
  const loginCookies = loginResponse.headers['set-cookie'] || [];
  for (const cookie of loginCookies) {
    if (cookie.startsWith('sessionid=')) {
      sessionId = cookie.split(';')[0].split('=')[1];
    }
    if (cookie.startsWith('csrftoken=')) {
      csrfToken = cookie.split(';')[0].split('=')[1];
    }
  }

  if (!sessionId) {
    throw new Error('Login failed: no session cookie received');
  }

  // Fetch user info using the session
  const userResponse = await axios.get(`${LABEL_STUDIO_URL}/api/current-user/whoami`, {
    headers: {
      'Cookie': `sessionid=${sessionId}; csrftoken=${csrfToken}`,
    },
  });

  return {
    token: sessionId,
    csrfToken,
    sessionId,
    user: {
      id: userResponse.data.id,
      email: userResponse.data.email,
    },
  };
}

/**
 * Verify if a session is still valid
 */
export async function verifySession(sessionId: string, csrfToken: string): Promise<boolean> {
  try {
    const response = await axios.get(`${LABEL_STUDIO_URL}/api/current-user/whoami`, {
      headers: {
        'Cookie': `sessionid=${sessionId}; csrftoken=${csrfToken}`,
      },
      validateStatus: (status) => status < 500,
    });
    return response.status === 200;
  } catch {
    return false;
  }
}
