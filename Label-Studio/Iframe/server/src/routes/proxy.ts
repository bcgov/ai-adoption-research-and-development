import { Express } from 'express';
import { createProxyMiddleware, Options } from 'http-proxy-middleware';
import { IncomingMessage } from 'http';

const LABEL_STUDIO_URL = process.env.LABEL_STUDIO_URL || 'http://localhost:8080';

// Extend IncomingMessage to include express session
interface RequestWithSession extends IncomingMessage {
  session?: {
    lsSessionId?: string;
    lsCsrfToken?: string;
  };
}

/**
 * Setup Label Studio proxy
 * Proxies all /ls/* requests to Label Studio, forwarding session cookies
 */
export function setupProxy(app: Express): void {
  const proxyOptions: Options = {
    target: LABEL_STUDIO_URL,
    changeOrigin: true,
    ws: true, // Enable WebSocket proxying

    // Rewrite /ls/... to /...
    pathRewrite: {
      '^/ls': '',
    },

    // Add Label Studio session cookies to proxied requests
    on: {
      proxyReq: (proxyReq, req) => {
        const expressReq = req as RequestWithSession;
        const session = expressReq.session;
        console.log('[/ls proxy] Path:', req.url, 'Has session:', !!session, 'Has lsSessionId:', !!session?.lsSessionId);

        if (session?.lsSessionId) {
          // Build cookie header with Label Studio session
          const cookies = [
            `sessionid=${session.lsSessionId}`,
          ];

          if (session.lsCsrfToken) {
            cookies.push(`csrftoken=${session.lsCsrfToken}`);
            // Also set CSRF header for POST/PUT/DELETE requests
            proxyReq.setHeader('X-CSRFToken', session.lsCsrfToken);
          }

          proxyReq.setHeader('Cookie', cookies.join('; '));
        }
      },

      proxyRes: (proxyRes) => {
        // Remove X-Frame-Options to allow iframe embedding
        // Since we're same-origin via proxy, this is safe
        delete proxyRes.headers['x-frame-options'];

        // Also remove Content-Security-Policy frame-ancestors if present
        const csp = proxyRes.headers['content-security-policy'];
        if (csp && typeof csp === 'string') {
          proxyRes.headers['content-security-policy'] = csp
            .replace(/frame-ancestors[^;]*;?/gi, '')
            .trim();
        }

        // Prevent browser from caching auth-related responses incorrectly
        if (proxyRes.headers['set-cookie']) {
          // Don't forward Label Studio's set-cookie to browser
          // Our backend manages the session
          delete proxyRes.headers['set-cookie'];
        }
      },

      error: (err, _req, res) => {
        console.error('Proxy error:', err);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Proxy error', details: err.message }));
        }
      },
    },
  };

  // Apply proxy middleware for /ls/* paths
  app.use('/ls', createProxyMiddleware(proxyOptions));

  // Proxy Label Studio static assets and other paths
  // These are referenced without /ls prefix in Label Studio's HTML
  // Use a custom filter function to match paths
  const lsPathPrefixes = [
    '/static',
    '/react-app',
    '/label-studio-frontend',
    '/dm',
    '/user',
    '/projects',
    // '/sw.js', // Don't proxy service worker - it causes scope issues in iframe
    '/data',
    '/settings',
    '/organization',
    '/favicon.ico',
    '/version',
    '/api',  // Label Studio API (our /api/auth is mounted before this, so it takes precedence)
  ];

  // Special handling for root path - proxy to Label Studio
  // This is needed because Label Studio navigates to / internally
  app.get('/', (req, res, next) => {
    // If this is the root path, proxy to Label Studio
    const expressReq = req as unknown as RequestWithSession;
    if (expressReq.session?.lsSessionId) {
      // Redirect to /projects if authenticated
      res.redirect('/projects');
    } else {
      // Redirect to login if not authenticated
      res.redirect('/user/login/');
    }
  });

  const staticProxy = createProxyMiddleware({
    target: LABEL_STUDIO_URL,
    changeOrigin: true,
    // Use function filter to match paths without stripping them
    pathFilter: (path: string) => {
      return lsPathPrefixes.some(prefix => path === prefix || path.startsWith(prefix + '/') || path.startsWith(prefix + '?'));
    },
    on: {
      proxyReq: (proxyReq, req) => {
        // Forward session for authenticated paths
        const expressReq = req as RequestWithSession;
        const session = expressReq.session;

        if (session?.lsSessionId) {
          const cookies = [`sessionid=${session.lsSessionId}`];
          if (session.lsCsrfToken) {
            cookies.push(`csrftoken=${session.lsCsrfToken}`);
            proxyReq.setHeader('X-CSRFToken', session.lsCsrfToken);
          }
          proxyReq.setHeader('Cookie', cookies.join('; '));
        }
      },
      proxyRes: (proxyRes) => {
        delete proxyRes.headers['x-frame-options'];
        delete proxyRes.headers['set-cookie'];
      },
    },
  });

  // Mount at root level - pathFilter handles matching
  app.use(staticProxy);
}
