import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { AuditLogger } from '@my-org/observability';
import { MockAuthGuard, UserContext } from '@my-org/shared-types';

// Audit logging guard that wraps authentication checks.
// Explanation: Provides comprehensive security auditing by logging all authentication
// attempts, regardless of success or failure, for compliance and monitoring purposes.
@Injectable()
export class AuditAuthGuard implements CanActivate {
  // Delegate to mock auth guard (likely for testing/development)
  // Explanation: Uses a mock implementation that always allows access,
  // but wraps it with audit logging for security monitoring.
  private readonly delegate = new MockAuthGuard();

  constructor(private readonly auditLogger: AuditLogger) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const allowed = await Promise.resolve(this.delegate.canActivate(context));
    const request = context.switchToHttp().getRequest();

    // Extract user context or default to anonymous
    // Explanation: Handles both authenticated and unauthenticated requests,
    // providing consistent audit logging for security monitoring.
    const user = (request.user ?? { userId: 'anonymous', roles: [] }) as UserContext;

    // Log authentication outcome with full context
    // Explanation: Records who attempted access, what resource they tried to reach,
    // whether they succeeded, and additional metadata for security analysis.
    await this.auditLogger.log({
      action: 'auth',
      actorId: user.userId,
      roles: user.roles,
      outcome: allowed ? 'success' : 'failure',
      resource: request.url,
      metadata: {
        path: request.url,
        method: request.method,
      },
    });
    return allowed;
  }
}

