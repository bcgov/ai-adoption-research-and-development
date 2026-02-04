import { SetMetadata } from '@nestjs/common';

// Metadata key for marking routes as public (bypassing authentication)
// Explanation: Defines a constant for consistent metadata key usage across the application,
// preventing typos and making refactoring easier.
export const IS_PUBLIC_KEY = 'isPublic';

// Decorator to mark controller methods as publicly accessible.
// Explanation: Applied to routes like login endpoints that should be accessible
// without JWT authentication, instructing guards to skip token validation.
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
