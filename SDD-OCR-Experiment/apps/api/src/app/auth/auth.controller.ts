import { Body, Controller, HttpCode, Post, ValidationPipe } from '@nestjs/common';
import {
  AuthBearerExchangeDto,
  AuthCodeRequestDto,
  AuthLoginRequestDto,
  AuthTokens,
} from '@my-org/shared-types';
import { Public } from './public.decorator';
import { AuthService } from './auth.service';

// REST API controller for authentication operations.
@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  // Password-based authentication endpoint.
  // Explanation: Accepts username/password credentials and returns JWT tokens,
  // supporting both Keycloak SSO and local authentication based on configuration.
  @Public()
  @Post('login')
  @HttpCode(200)
  async login(
    @Body(
      new ValidationPipe({
        whitelist: true, // Remove unknown properties
        forbidNonWhitelisted: true, // Reject requests with unknown properties
        transform: true, // Transform payload to DTO instance
      }),
    )
    body: AuthLoginRequestDto,
  ): Promise<AuthTokens> {
    return this.authService.loginWithPassword(body);
  }

  // OAuth2 Authorization Code flow completion endpoint.
  // Explanation: Exchanges authorization codes from identity providers (like Keycloak)
  // for JWT tokens, completing the OAuth2 redirect flow for web applications.
  @Public()
  @Post('login/code')
  @HttpCode(200)
  async loginWithCode(
    @Body(
      new ValidationPipe({
        whitelist: true,
        forbidNonWhitelisted: true,
        transform: true,
      }),
    )
    body: AuthCodeRequestDto,
  ): Promise<AuthTokens> {
    return this.authService.loginWithOidcCode(body);
  }

  // Token exchange endpoint for validating and refreshing existing tokens.
  // Explanation: Accepts a Bearer token and returns it back if valid,
  // useful for token validation and refresh workflows in client applications.
  @Public()
  @Post('login/bearer')
  @HttpCode(200)
  async exchangeBearer(
    @Body(
      new ValidationPipe({
        whitelist: true,
        forbidNonWhitelisted: true,
        transform: true,
      }),
    )
    body: AuthBearerExchangeDto,
  ): Promise<AuthTokens> {
    return this.authService.exchangeBearer(body.accessToken);
  }
}

