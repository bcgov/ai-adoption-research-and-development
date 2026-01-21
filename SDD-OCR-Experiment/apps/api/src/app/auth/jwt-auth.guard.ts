import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { AuditLogger } from '@my-org/observability';
import { AuthService } from './auth.service';

// Global JWT authentication guard for NestJS.
// Explanation: Automatically runs before route handlers to validate JWT tokens,
// extracting user context and attaching it to requests for downstream use.
@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private readonly authService: AuthService,
    private readonly audit: AuditLogger,
    private readonly reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();

    // Check if route is marked as public (bypasses authentication)
    // Explanation: Uses reflection to read metadata set by @Public() decorator,
    // allowing certain routes like login endpoints to be accessed without tokens.
    const isPublic = this.reflector.get<boolean>('isPublic', context.getHandler());
    if (isPublic) {
      return true;
    }

    try {
      // Verify JWT token and extract user context
      // Explanation: Calls auth service to validate the Bearer token from Authorization header,
      // then attaches the authenticated user to the request for use in controllers and guards.
      const user = await this.authService.verify(request.headers.authorization);
      request.user = user;
      return true;
    } catch (err) {
      // Audit failed authentication attempts
      // Explanation: Logs security events for monitoring and compliance,
      // helping track potential security threats and authentication failures.
      await this.audit.log({
        action: 'auth.verify',
        outcome: 'failure',
        resource: request.url,
        metadata: { path: request.url },
      });
      throw err instanceof UnauthorizedException ? err : new UnauthorizedException();
    }
  }
}

