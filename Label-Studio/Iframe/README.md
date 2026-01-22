# Label Studio Iframe POC with Proxy Authentication

A proof-of-concept demonstrating how to embed Label Studio in an iframe with single sign-on (SSO) authentication via a proxy server.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    React App (/app)                        │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              Our App Header                          │  │  │
│  │  │  [Label Studio]              [user@email] [Logout]   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              iframe src="/ls/projects"               │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │         Label Studio UI (same origin)         │  │  │  │
│  │  │  │                                               │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Vite Dev Server (:5173)                       │
│  - Serves React app at /app                                      │
│  - Proxies /api/*, /ls/*, /static/*, etc. to Express backend    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Express Backend (:3001)                       │
│  - Handles /api/auth/* for login/logout/session                 │
│  - Manages Express sessions with Label Studio session IDs       │
│  - Proxies /ls/* and Label Studio paths to Label Studio         │
│  - Forwards session cookies to Label Studio on proxied requests │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Label Studio (:8081)                          │
│  - Docker container running Label Studio                         │
│  - Receives authenticated requests via session cookies           │
└─────────────────────────────────────────────────────────────────┘
```

## How It Works

### Authentication Flow

1. **User visits React app** at `http://localhost:5173/app/login`

2. **User enters credentials** (same as their Label Studio credentials)

3. **React app sends login request** to `POST /api/auth/login`

4. **Express backend authenticates with Label Studio**:
   - Gets CSRF token from Label Studio login page
   - POSTs credentials to Label Studio
   - Receives session cookie from Label Studio
   - Stores Label Studio session ID in Express session

5. **User is redirected to main page** with embedded iframe

6. **Iframe loads `/ls/projects`** which:
   - Express proxy intercepts the request
   - Attaches the Label Studio session cookie from Express session
   - Forwards to Label Studio
   - Returns Label Studio HTML (with `X-Frame-Options` removed)

7. **All subsequent requests** (API calls, static assets) are proxied with session cookies

### Key Components

#### React Frontend (`/src`)
- **AuthContext**: Manages authentication state
- **LoginForm**: Login page with email/password form
- **LabelStudioEmbed**: Renders iframe pointing to `/ls/projects`
- **ProtectedRoute**: Redirects unauthenticated users to login

#### Express Backend (`/server/src`)
- **auth.ts**: Authentication routes (`/api/auth/login`, `/logout`, `/me`)
- **proxy.ts**: Proxy configuration for Label Studio paths
- **labelStudio.ts**: Service for authenticating with Label Studio API

#### Vite Configuration
- Routes `/api`, `/ls`, `/static`, `/projects`, etc. to Express backend
- React app served at `/app` base path

## Setup

### Prerequisites
- Node.js 18+
- Docker and Docker Compose

### 1. Start Label Studio

```bash
docker-compose up -d
```

This starts Label Studio on port 8081 with default credentials:
- Email: `admin@example.com`
- Password: `admin123`

### 2. Install Dependencies

```bash
# Install React app dependencies
npm install

# Install server dependencies
cd server && npm install && cd ..
```

### 3. Configure Environment

The server `.env` file (`server/.env`) should contain:

```env
PORT=3001
LABEL_STUDIO_URL=http://localhost:8081
SESSION_SECRET=dev-secret-change-in-prod
FRONTEND_URL=http://localhost:5173
```

### 4. Start the Application

In two terminal windows:

**Terminal 1 - Express Backend:**
```bash
cd server
npm run dev
```

**Terminal 2 - Vite Dev Server:**
```bash
npm run dev
```

### 5. Access the Application

Open `http://localhost:5173/app/login` in your browser.

Login with the Label Studio credentials (`admin@example.com` / `admin123`).

## Project Structure

```
Iframe/
├── docker-compose.yml      # Label Studio Docker configuration
├── package.json            # React app dependencies
├── vite.config.ts          # Vite configuration with proxy rules
├── src/
│   ├── App.tsx             # Main React app with routing
│   ├── components/
│   │   ├── LoginForm.tsx   # Login page
│   │   ├── LabelStudioEmbed.tsx  # Iframe wrapper
│   │   └── ProtectedRoute.tsx    # Auth guard
│   ├── contexts/
│   │   └── AuthContext.tsx # Authentication state
│   ├── hooks/
│   │   └── useAuth.ts      # Auth hook
│   └── services/
│       └── api.ts          # API client
└── server/
    ├── package.json        # Server dependencies
    ├── .env                # Environment variables
    └── src/
        ├── index.ts        # Express app setup
        ├── routes/
        │   ├── auth.ts     # Auth endpoints
        │   └── proxy.ts    # Label Studio proxy
        └── services/
            └── labelStudio.ts  # LS authentication
```

## How the Proxy Works

The proxy is essential for making Label Studio work in an iframe:

1. **Same-Origin Policy**: By proxying Label Studio through our Express server, the iframe content is served from the same origin as our React app. This:
   - Removes `X-Frame-Options` restrictions
   - Allows cookies to be shared (same-origin)
   - Enables JavaScript communication between parent and iframe

2. **Session Cookie Forwarding**: When the proxy receives a request:
   - It retrieves the Label Studio session ID from the Express session
   - Attaches it as a `Cookie` header on the proxied request
   - Label Studio sees an authenticated request

3. **Path Routing**:
   - `/ls/*` - Main Label Studio proxy with path rewriting
   - `/static/*`, `/react-app/*`, `/api/*` - Label Studio assets (no path rewriting)
   - `/api/auth/*` - Our authentication endpoints (not proxied)

## Customization

### Changing the Embedded Page

By default, the iframe loads `/ls/projects` (the projects list). You can change this in `LabelStudioEmbed.tsx`:

```tsx
// Load a specific project
<LabelStudioEmbed path="/projects/1" />

// Load the labeling interface
<LabelStudioEmbed path="/projects/1/data?task=123" />
```

### Adding Header Actions

The `LabelStudioEmbed` component includes a header with user info. Customize it as needed:

```tsx
<header>
  <h1>Your App Name</h1>
  <nav>
    {/* Add navigation items */}
  </nav>
  <UserInfo />
</header>
```

### Production Deployment

For production:

1. Build the React app: `npm run build`
2. Build the server: `cd server && npm run build`
3. Set secure environment variables
4. Use a reverse proxy (nginx) to serve both apps
5. Enable HTTPS
6. Set `cookie.secure: true` in session config

## Troubleshooting

### Login fails
- Ensure Label Studio is running: `docker ps | grep label`
- Check Label Studio URL in `server/.env`
- Verify credentials match Label Studio user

### Iframe shows blank/error
- Check browser console for CORS or CSP errors
- Ensure all Label Studio paths are proxied in `vite.config.ts`
- Check Express server logs for proxy errors

### Session expires quickly
- Adjust `maxAge` in session configuration
- Label Studio sessions may expire; implement token refresh

## License

MIT
