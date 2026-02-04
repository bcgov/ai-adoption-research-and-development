import { Request, Response, Router } from 'express';
import { PolicyService } from '../services/policy.service';
import { PolicyEvaluationRequest } from '../dto/policy-evaluation.dto';

/**
 * Policy Controller - REST API endpoints for policy evaluation
 */
export class PolicyController {
  private router: Router;

  constructor(private policyService: PolicyService) {
    this.router = Router();
    this.setupRoutes();
  }

  private setupRoutes(): void {
    // Evaluate OCR results against policies
    this.router.post('/evaluate', this.evaluate.bind(this));

    // List available policies
    this.router.get('/policies', this.getPolicies.bind(this));

    // Health check
    this.router.get('/health', this.healthCheck.bind(this));
  }

  /**
   * POST /api/policy/evaluate
   * Evaluate OCR results against OPA policies
   */
  private async evaluate(req: Request, res: Response): Promise<void> {
    try {
      const request: PolicyEvaluationRequest = req.body;

      if (!request.ocrResult) {
        res.status(400).json({
          error: 'Missing required field: ocrResult',
        });
        return;
      }

      const result = await this.policyService.evaluatePolicy(request);
      res.json(result);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Evaluation error:', errorMessage);
      res.status(500).json({
        error: 'Policy evaluation failed',
        message: errorMessage,
      });
    }
  }

  /**
   * GET /api/policy/policies
   * List all available policy packages and rules
   */
  private async getPolicies(req: Request, res: Response): Promise<void> {
    try {
      const policies = this.policyService.getAvailablePolicies();
      res.json({
        policies,
        count: policies.length,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json({
        error: 'Failed to retrieve policies',
        message: errorMessage,
      });
    }
  }

  /**
   * GET /api/policy/health
   * Health check for OPA service connectivity
   */
  private async healthCheck(req: Request, res: Response): Promise<void> {
    try {
      const status = await this.policyService.getHealthStatus();
      const statusCode = status.healthy ? 200 : 503;
      res.status(statusCode).json(status);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      res.status(503).json({
        healthy: false,
        opaConnected: false,
        error: errorMessage,
      });
    }
  }

  /**
   * Get the Express router
   */
  getRouter(): Router {
    return this.router;
  }
}

