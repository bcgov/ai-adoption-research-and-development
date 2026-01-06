import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Role, UserContext } from '@my-org/shared-types';

// Role-based authorization guard for NestJS.
// Explanation: Checks if authenticated users have the required roles to access specific routes,
// providing fine-grained access control based on user permissions.
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    // Get required roles from route metadata
    // Explanation: Uses reflection to read role requirements set by @Roles() decorator
    // on controller methods, allowing different access levels per endpoint.
    const requiredRoles = this.reflector.get<Role[]>('roles', context.getHandler());
    if (!requiredRoles || requiredRoles.length === 0) return true;

    // Get authenticated user from request (set by JwtAuthGuard)
    // Explanation: Assumes authentication has already occurred and user context
    // is available on the request object.
    const request = context.switchToHttp().getRequest();
    const user: UserContext | undefined = request.user;
    if (!user) return false;

    // Check if user has any of the required roles
    // Explanation: Uses inclusive logic - user needs at least one matching role
    // to access the protected resource.
    return user.roles.some((r) => requiredRoles.includes(r as Role));
  }
}

