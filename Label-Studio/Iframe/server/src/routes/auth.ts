import { Router, Request, Response } from 'express';
import { authenticateWithLabelStudio, verifySession } from '../services/labelStudio';

const router = Router();

/**
 * POST /api/auth/login
 * Authenticate user with Label Studio credentials
 */
router.post('/login', async (req: Request, res: Response) => {
  const { email, password } = req.body;

  if (!email || !password) {
    res.status(400).json({ error: 'Email and password are required' });
    return;
  }

  try {
    const authResult = await authenticateWithLabelStudio(email, password);

    // Store Label Studio session info in our session
    req.session.lsSessionId = authResult.sessionId;
    req.session.lsCsrfToken = authResult.csrfToken;
    req.session.user = authResult.user;

    res.json({
      success: true,
      user: authResult.user,
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(401).json({
      error: 'Authentication failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * POST /api/auth/logout
 * Clear session and logout
 */
router.post('/logout', (req: Request, res: Response) => {
  req.session.destroy((err) => {
    if (err) {
      console.error('Session destruction error:', err);
      res.status(500).json({ error: 'Failed to logout' });
      return;
    }
    res.clearCookie('connect.sid');
    res.json({ success: true });
  });
});

/**
 * GET /api/auth/me
 * Get current authenticated user
 */
router.get('/me', async (req: Request, res: Response) => {
  if (!req.session.user || !req.session.lsSessionId) {
    res.status(401).json({ error: 'Not authenticated' });
    return;
  }

  // Verify the Label Studio session is still valid
  const isValid = await verifySession(
    req.session.lsSessionId,
    req.session.lsCsrfToken || ''
  );

  if (!isValid) {
    req.session.destroy(() => {});
    res.status(401).json({ error: 'Session expired' });
    return;
  }

  res.json({
    user: req.session.user,
    authenticated: true,
  });
});

export default router;
