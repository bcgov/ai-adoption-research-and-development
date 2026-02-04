/**
 * This is not a production server yet!
 * This is only a minimal backend to get started.
 */

import { Logger, RequestMethod, ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import { AppModule } from './app/app.module';
import { SecurityConfigService } from './app/security/security.service';
import { NextFunction, Request, Response } from 'express';
import { initTelemetry, shutdownTelemetry } from '@my-org/observability';
import * as fs from 'fs';
import { loadTlsConfig } from './config/tls.config';
import { createSessionTimeoutMiddleware } from './app/security/session.middleware';
import { createHttpsEnforcementMiddleware } from './app/security/https.middleware';
import { json, urlencoded } from 'express';

async function bootstrap() {
  // Initialize OpenTelemetry for distributed tracing and metrics collection.
  // Explanation: Sets up monitoring tools to track application performance and errors across services.
  await initTelemetry(process.env['OTEL_SERVICE_NAME'] ?? 'ai-ocr-api');

  // Load TLS certificate and key file paths from configuration.
  // Explanation: Retrieves file paths for SSL/TLS certificates needed for HTTPS encryption.
  const { certFile, keyFile } = loadTlsConfig();

  // Conditionally configure HTTPS options if certificate files exist and are valid.
  // Explanation: Only enables secure HTTPS connections when proper SSL certificates are available.
  const httpsOptions =
    certFile && keyFile && fs.existsSync(certFile) && fs.existsSync(keyFile)
      ? {
          cert: fs.readFileSync(certFile),
          key: fs.readFileSync(keyFile),
        }
      : undefined;

  // Create NestJS application instance with Express platform and optional HTTPS configuration.
  // Explanation: Initializes the web framework that handles HTTP requests and routes them to controllers.
  const app = await NestFactory.create<NestExpressApplication>(AppModule, {
    httpsOptions,
  });

  // Set global URL prefix for all API routes, with exceptions for admin endpoints.
  // Explanation: All API endpoints will start with '/api' except for queue management routes that need direct access.
  const globalPrefix = 'api';
  app.setGlobalPrefix(globalPrefix, {
    exclude: [
      { path: 'admin/queues', method: RequestMethod.ALL },
      { path: 'admin/queues/(.*)', method: RequestMethod.ALL },
    ],
  });
  // Configure Express middleware to accept larger request payloads for file uploads.
  // Explanation: Increases the maximum request size to 10MB to support uploading images and documents as base64 encoded data.
  app.use(json({ limit: '10mb' }));
  app.use(urlencoded({ extended: true, limit: '10mb' }));

  // Apply global validation pipe to automatically validate and transform incoming request data.
  // Explanation: Ensures all API inputs match expected formats and automatically converts data types (like strings to numbers).
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: { enableImplicitConversion: true },
    }),
  );
  // Retrieve security configuration service to access security settings.
  // Explanation: Gets centralized security settings that control HTTPS requirements and session management.
  const securityConfig = app.get(SecurityConfigService);

  // Configure Express to trust proxy headers when running behind a reverse proxy (like nginx).
  // Explanation: Allows the app to correctly identify client IP addresses when deployed behind load balancers.
  if (securityConfig.config.trustProxy) {
    app.set('trust proxy', 1);
  }

  // Apply middleware to enforce HTTPS connections when required by configuration.
  // Explanation: Redirects HTTP requests to HTTPS and blocks insecure connections when TLS is mandatory.
  app.use(
    createHttpsEnforcementMiddleware({
      requireTls: securityConfig.config.requireTls,
      trustProxy: securityConfig.config.trustProxy,
    }),
  );

  // Add response header to inform clients about session timeout duration.
  // Explanation: Sends session timeout information to frontend so users know when they'll be automatically logged out.
  app.use((req: Request, res: Response, next: NextFunction) => {
    res.setHeader(
      'X-Session-Timeout-Minutes',
      securityConfig.config.sessionTimeoutMinutes.toString(),
    );
    next();
  });

  // Configure middleware to automatically expire user sessions after period of inactivity.
  // Explanation: Logs users out automatically after being idle to improve security.
  // NOTE: Variable naming inconsistency - sessionTimeoutMinutes is renamed to sessionIdleMinutes but serves the same purpose.
  const port = Number(process.env.PORT) || 3000;
  const sessionIdleMinutes = securityConfig.config.sessionTimeoutMinutes;
  app.use(createSessionTimeoutMiddleware(sessionIdleMinutes));

  // Start the HTTP/HTTPS server and begin accepting requests.
  // Explanation: Binds the application to the specified port and makes it available to handle web requests.
  await app.listen(port);

  // Log successful startup with connection details.
  // Explanation: Confirms the server is running and provides the base URL for API access.
  Logger.log(`🚀 Application is running on port ${port}/${globalPrefix}`);

  // Register graceful shutdown handler for SIGTERM signal (used by container orchestrators like Kubernetes).
  // Explanation: Ensures proper cleanup of resources and telemetry data when the application is being stopped.
  process.on('SIGTERM', async () => {
    await shutdownTelemetry();
    await app.close();
  });
}

// Handle any errors that occur during application startup and perform cleanup.
// Explanation: If something goes wrong starting the server, log the error and cleanly shut down monitoring tools before exiting.
bootstrap().catch((err) => {
  Logger.error('Failed to bootstrap application', err);
  void shutdownTelemetry();
  process.exit(1);
});
