import { SetMetadata } from '@nestjs/common';
import { Role } from '@my-org/shared-types';

// Decorator for specifying required roles on controller methods.
// Explanation: Allows declaring access control requirements directly on route handlers,
// where the RolesGuard will check if authenticated users possess any of the specified roles.
export const Roles = (...roles: Role[]) => SetMetadata('roles', roles);

