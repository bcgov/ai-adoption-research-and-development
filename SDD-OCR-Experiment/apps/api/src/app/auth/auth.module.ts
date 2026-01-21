import { Module } from '@nestjs/common';
import { APP_GUARD, Reflector } from '@nestjs/core';
import { TracingModule } from '@my-org/observability';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { JwtAuthGuard } from './jwt-auth.guard';
import { RolesGuard } from './roles.guard';
import { AuditModule } from '../audit/audit.module';

// Authentication module configuring global security guards.
// Explanation: Sets up NestJS dependency injection and registers application-wide guards
// that automatically protect all routes unless explicitly marked as public.
@Module({
  imports: [TracingModule, AuditModule],
  controllers: [AuthController],
  providers: [
    AuthService,
    Reflector, // Required for metadata reflection in guards
    // Global JWT authentication guard (runs first)
    // Explanation: Automatically validates JWT tokens on all protected routes,
    // extracting user context and attaching it to the request object.
    {
      provide: APP_GUARD,
      useClass: JwtAuthGuard,
    },
    // Global role-based authorization guard (runs second)
    // Explanation: Checks if authenticated users have required roles for specific routes,
    // providing fine-grained access control based on user permissions.
    {
      provide: APP_GUARD,
      useClass: RolesGuard,
    },
  ],
  exports: [AuthService],
})
export class AuthModule {}

