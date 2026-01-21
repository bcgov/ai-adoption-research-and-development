import { Injectable, UnauthorizedException } from '@nestjs/common';
import axios from 'axios';
import { AuditLogger } from '@my-org/observability';
import {
  AuthLoginRequestDto,
  AuthTokens,
  JwtClaims,
  Role,
  UserContext,
  WorkerAuthTokenPayload,
  AuthCodeRequestDto,
  verifyWorkerToken,
} from '@my-org/shared-types';
import * as jwt from 'jsonwebtoken';
import jwksClient, { SigningKey, JwksClient } from 'jwks-rsa';

@Injectable()
export class AuthService {
  // JWKS client for dynamic JWT key retrieval from identity providers.
  // Explanation: Manages public keys for verifying JWT tokens from external auth providers like Keycloak,
  // caching keys to reduce network calls while maintaining security through regular refresh.
  private jwks: JwksClient | null =
    process.env['JWKS_URL'] && process.env['JWKS_URL'].length > 0
      ? jwksClient({
          jwksUri: process.env['JWKS_URL'],
          cache: true,
          cacheMaxEntries: 5,
          cacheMaxAge: 10 * 60 * 1000,
        })
      : null;

  constructor(private readonly audit: AuditLogger) {}

  // Core authentication method supporting multiple token types (JWT, worker tokens).
  // Explanation: Validates Bearer tokens from HTTP Authorization headers, handling both user JWTs
  // and service worker tokens for microservice authentication.
  async verify(authHeader?: string): Promise<UserContext> {
    if (!authHeader?.startsWith('Bearer ')) {
      throw new UnauthorizedException('Missing bearer token');
    }
    const token = authHeader.slice('Bearer '.length);

    // Check for service worker tokens first (higher priority for internal services)
    // Explanation: Worker tokens allow microservices to authenticate without full user context,
    // useful for background jobs and inter-service communication.
    const workerPayload = this.verifyWorkerToken(token);
    if (workerPayload) {
      const user: UserContext = {
        userId: workerPayload.serviceId,
        roles: (workerPayload.roles ?? []) as Role[],
      };

      await this.audit.log({
        action: 'auth.verify',
        actorId: user.userId,
        roles: user.roles,
        outcome: 'success',
      });

      return user;
    }

    // Verify standard JWT token and extract user information
    // Explanation: Processes JWT tokens from identity providers, extracting user identity,
    // roles, and profile information to create a unified UserContext for the application.
    const decoded = await this.verifyJwt(token);
    const roles = this.resolveRoles(decoded);

    const user: UserContext = {
      userId: decoded.sub ?? decoded.preferred_username ?? 'unknown',
      roles: (roles ?? []).filter(Boolean) as Role[],
      email: decoded['email'],
      name: decoded['name'],
    };

    await this.audit.log({
      action: 'auth.verify',
      actorId: user.userId,
      roles: user.roles,
      outcome: 'success',
    });

    return user;
  }

  // Multi-provider password authentication with Keycloak or local fallback.
  // Explanation: Supports enterprise SSO through Keycloak or simple local authentication
  // for development/testing, automatically choosing the appropriate provider based on configuration.
  async loginWithPassword(payload: AuthLoginRequestDto): Promise<AuthTokens> {
    try {
      const tokens = this.hasKeycloakTokenUrl()
        ? await this.loginWithKeycloak(payload)
        : await this.loginWithLocalSecret(payload);

      await this.audit.log({
        action: 'auth.login',
        actorId: payload.username,
        roles: [],
        outcome: 'success',
      });

      return tokens;
    } catch (err) {
      await this.audit.log({
        action: 'auth.login',
        actorId: payload.username,
        roles: [],
        outcome: 'failure',
        metadata: { error: err instanceof Error ? err.message : 'unknown' },
      });
      throw err;
    }
  }

  async loginWithOidcCode(payload: AuthCodeRequestDto): Promise<AuthTokens> {
    if (!this.hasKeycloakTokenUrl()) {
      throw new UnauthorizedException('No OIDC provider configured');
    }

    try {
      const tokens = await this.loginWithAuthorizationCode(payload);
      await this.audit.log({
        action: 'auth.login',
        actorId: 'oidc',
        roles: [],
        outcome: 'success',
      });
      return tokens;
    } catch (err) {
      await this.audit.log({
        action: 'auth.login',
        actorId: 'oidc',
        roles: [],
        outcome: 'failure',
        metadata: { error: err instanceof Error ? err.message : 'unknown' },
      });
      throw err;
    }
  }

  async exchangeBearer(accessToken: string): Promise<AuthTokens> {
    try {
      await this.verifyJwt(accessToken);
      await this.audit.log({
        action: 'auth.exchange',
        actorId: 'bearer',
        roles: [],
        outcome: 'success',
      });
      return { accessToken };
    } catch (err) {
      await this.audit.log({
        action: 'auth.exchange',
        actorId: 'bearer',
        roles: [],
        outcome: 'failure',
        metadata: { error: err instanceof Error ? err.message : 'unknown' },
      });
      throw err;
    }
  }

  // Multi-strategy JWT verification with fallback options.
  // Explanation: Tries different verification methods in order of preference:
  // static public key, dynamic JWKS retrieval, or local HMAC secret for development.
  private async verifyJwt(token: string): Promise<JwtClaims> {
    // Primary: Static public key (most secure, no network calls)
    // Explanation: Uses pre-configured RSA public key for high-trust environments
    // where key rotation is managed through config updates.
    const publicKey = process.env['KEYCLOAK_PUBLIC_KEY'];
    if (publicKey) {
      return jwt.verify(token, publicKey, { algorithms: ['RS256'] }) as JwtClaims;
    }

    // Secondary: Dynamic JWKS retrieval (flexible, requires network)
    // Explanation: Fetches public keys dynamically from identity provider's JWKS endpoint,
    // supporting automatic key rotation but requiring network connectivity.
    if (this.jwks) {
      const decodedHeader = jwt.decode(token, { complete: true });
      const kid = (decodedHeader?.header as jwt.JwtHeader | undefined)?.kid;
      if (!kid) throw new UnauthorizedException('Missing kid');
      const key = await new Promise<SigningKey>((resolve, reject) => {
        this.jwks!.getSigningKey(
          kid,
          (error: Error | null, k?: SigningKey) => {
            if (error || !k) return reject(error ?? new UnauthorizedException('No signing key'));
            resolve(k);
          },
        );
      });
      const signingKey = key.getPublicKey();
      return jwt.verify(token, signingKey, { algorithms: ['RS256'] }) as JwtClaims;
    }

    // Fallback: Local HMAC secret (development only)
    // Explanation: Simple symmetric key verification for local development
    // when external identity providers are not available.
    const localSecret = process.env['LOCAL_AUTH_SECRET'];
    if (localSecret) {
      return jwt.verify(token, localSecret, { algorithms: ['HS256'] }) as JwtClaims;
    }

    throw new UnauthorizedException('No verification key configured');
  }

  // Extract roles from JWT claims with fallback hierarchy.
  // Explanation: Keycloak supports roles at different levels (realm, client-specific, or direct),
  // this method tries each location in order of specificity to find user permissions.
  private resolveRoles(decoded: JwtClaims): Role[] {
    const clientId = process.env['KEYCLOAK_CLIENT_ID'] ?? 'ai-ocr';
    return (
      decoded.realm_access?.roles || // Global realm roles (broadest scope)
      decoded.resource_access?.[clientId]?.roles || // Client-specific roles (recommended)
      decoded.roles || // Direct roles claim (fallback)
      []
    ) as Role[];
  }

  private verifyWorkerToken(token: string): WorkerAuthTokenPayload | null {
    return verifyWorkerToken(token);
  }

  private hasKeycloakTokenUrl(): boolean {
    return !!process.env['KEYCLOAK_TOKEN_URL'];
  }

  // OAuth2 Resource Owner Password Credentials flow with Keycloak.
  // Explanation: Direct password authentication against Keycloak's token endpoint,
  // suitable for first-party applications where storing user credentials is acceptable.
  private async loginWithKeycloak(payload: AuthLoginRequestDto): Promise<AuthTokens> {
    const tokenUrl = process.env['KEYCLOAK_TOKEN_URL']!;
    const clientId = process.env['KEYCLOAK_CLIENT_ID'] ?? 'ai-ocr';
    const clientSecret = process.env['KEYCLOAK_CLIENT_SECRET'];

    try {
      const response = await axios.post(
        tokenUrl,
        new URLSearchParams({
          grant_type: 'password',
          username: payload.username,
          password: payload.password,
          client_id: clientId,
          ...(clientSecret ? { client_secret: clientSecret } : {}),
        }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        },
      );

      const accessToken = response.data?.access_token;
      if (!accessToken) {
        throw new UnauthorizedException('Invalid credentials');
      }

      return {
        accessToken,
        refreshToken: response.data?.refresh_token,
      };
    } catch (err) {
      if (err instanceof UnauthorizedException) throw err;
      throw new UnauthorizedException('Authentication failed');
    }
  }

  private async loginWithAuthorizationCode(payload: AuthCodeRequestDto): Promise<AuthTokens> {
    const tokenUrl = process.env['KEYCLOAK_TOKEN_URL']!;
    const clientId = process.env['KEYCLOAK_CLIENT_ID'] ?? 'ai-ocr';
    const clientSecret = process.env['KEYCLOAK_CLIENT_SECRET'];

    try {
      const response = await axios.post(
        tokenUrl,
        new URLSearchParams({
          grant_type: 'authorization_code',
          code: payload.code,
          redirect_uri: payload.redirectUri ?? '',
          client_id: clientId,
          ...(payload.codeVerifier ? { code_verifier: payload.codeVerifier } : {}),
          ...(clientSecret ? { client_secret: clientSecret } : {}),
        }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        },
      );

      const accessToken = response.data?.access_token;
      if (!accessToken) {
        throw new UnauthorizedException('Invalid authorization code');
      }

      return {
        accessToken,
        refreshToken: response.data?.refresh_token,
      };
    } catch (err) {
      if (err instanceof UnauthorizedException) throw err;
      throw new UnauthorizedException('Authorization code exchange failed');
    }
  }

  // Simple local authentication for development/testing environments.
  // Explanation: Provides basic username/password authentication without external dependencies,
  // creating JWT tokens with configurable roles for testing application features.
  private async loginWithLocalSecret(payload: AuthLoginRequestDto): Promise<AuthTokens> {
    const secret = process.env['LOCAL_AUTH_SECRET'];
    const expectedUser = process.env['LOCAL_AUTH_USER'];
    const expectedPassword = process.env['LOCAL_AUTH_PASSWORD'];

    if (!secret || !expectedUser || !expectedPassword) {
      throw new UnauthorizedException('Local auth is not configured');
    }

    if (payload.username !== expectedUser || payload.password !== expectedPassword) {
      throw new UnauthorizedException('Invalid credentials');
    }

    // Parse default roles from environment variable
    // Explanation: Allows configuring test user permissions through environment variables,
    // supporting comma-separated role lists for flexible testing scenarios.
    const defaultRoles = (process.env['LOCAL_AUTH_ROLES'] ?? 'operator,admin')
      .split(',')
      .map((r) => r.trim())
      .filter(Boolean) as Role[];

    // Create access token with user claims and roles
    // Explanation: Short-lived token (1 hour) containing user identity and permissions
    // for API access during the session.
    const accessToken = jwt.sign(
      {
        sub: payload.username,
        preferred_username: payload.username,
        roles: defaultRoles,
      },
      secret,
      { algorithm: 'HS256', expiresIn: '1h' },
    );

    // Create refresh token for session extension
    // Explanation: Long-lived token (30 days) used to obtain new access tokens
    // without requiring full re-authentication.
    const refreshToken = jwt.sign(
      {
        sub: payload.username,
        type: 'refresh',
      },
      secret,
      { algorithm: 'HS256', expiresIn: '30d' },
    );

    return { accessToken, refreshToken };
  }
}

