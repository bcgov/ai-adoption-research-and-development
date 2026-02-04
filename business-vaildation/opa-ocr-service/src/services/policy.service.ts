import { OpaService } from './opa.service';
import { OCRResult } from '../types/ocr-result.types';
import {
  PolicyEvaluationRequest,
  PolicyEvaluationResponse,
  PolicyEvaluationResult,
  PolicyViolation,
} from '../dto/policy-evaluation.dto';

/**
 * Policy Service - Orchestrates policy evaluation and formats results
 */
export class PolicyService {
  constructor(private opaService: OpaService) {}

  /**
   * Evaluate OCR results against OPA policies
   */
  async evaluatePolicy(
    request: PolicyEvaluationRequest
  ): Promise<PolicyEvaluationResponse> {
    const { ocrResult, policyPackage } = request;

    try {
      // Prepare input for OPA
      const opaInput = {
        ocrResult,
      };

      // Evaluate using OPA
      const opaResult = await this.opaService.evaluate(opaInput, policyPackage);

      // Transform OPA result to our response format
      const result = this.transformOpaResult(opaResult);

      return {
        allowed: result.valid,
        result,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Policy evaluation error:', errorMessage);

      // Return error result
      return {
        allowed: false,
        result: {
          valid: false,
          violations: [
            {
              rule: 'policy_evaluation_error',
              message: errorMessage,
              severity: 'error',
            },
          ],
          warnings: [],
        },
      };
    }
  }

  /**
   * Transform OPA result to our standard format
   */
  private transformOpaResult(opaResult: unknown): PolicyEvaluationResult {
    // OPA typically returns an object with 'allowed' and other fields
    // Handle different OPA response formats
    if (typeof opaResult === 'object' && opaResult !== null) {
      const result = opaResult as Record<string, unknown>;

      // Check if OPA returned an 'allowed' field
      if ('allowed' in result) {
        const allowed = result.allowed === true;
        const violations: PolicyViolation[] = [];
        const warnings: PolicyViolation[] = [];

        // Extract violations if present
        // OPA returns violations as a set (object with keys) or array
        if (result.violations) {
          let violationsArray: unknown[] = [];
          
          if (Array.isArray(result.violations)) {
            violationsArray = result.violations;
          } else if (typeof result.violations === 'object') {
            // Convert set (object) to array
            violationsArray = Object.values(result.violations);
          }

          violations.push(
            ...violationsArray.map((v: unknown) => {
              const violation = v as {
                rule?: string;
                message?: string;
                severity?: string;
                field?: string;
                value?: unknown;
              };
              return {
                rule: violation.rule || 'unknown',
                message: violation.message || 'Policy violation',
                severity: (violation.severity === 'warning' ? 'warning' : 'error') as 'error' | 'warning',
                field: violation.field,
                value: violation.value,
              };
            })
          );
        }

        // Extract warnings separately or from violations
        if (result.warnings) {
          let warningsArray: unknown[] = [];
          
          if (Array.isArray(result.warnings)) {
            warningsArray = result.warnings;
          } else if (typeof result.warnings === 'object') {
            // Convert set (object) to array
            warningsArray = Object.values(result.warnings);
          }

          warnings.push(
            ...warningsArray.map((w: unknown) => {
              const warning = w as {
                rule?: string;
                message?: string;
                field?: string;
                value?: unknown;
              };
              return {
                rule: warning.rule || 'unknown',
                message: warning.message || 'Policy warning',
                severity: 'warning' as const,
                field: warning.field,
                value: warning.value,
              };
            })
          );
        }

        return {
          valid: allowed,
          violations: violations.filter((v) => v.severity === 'error'),
          warnings: [
            ...warnings,
            ...violations.filter((v) => v.severity === 'warning'),
          ],
          dataQualityScore: result.dataQualityScore as number | undefined,
          businessRuleCompliance: result.businessRuleCompliance as boolean | undefined,
          metadata: result.metadata as Record<string, unknown> | undefined,
        };
      }

      // If no 'allowed' field, assume the result itself indicates validity
      return {
        valid: true,
        violations: [],
        warnings: [],
        metadata: result,
      };
    }

    // Fallback for unexpected formats
    return {
      valid: false,
      violations: [
        {
          rule: 'invalid_result_format',
          message: 'OPA returned an unexpected result format',
          severity: 'error',
        },
      ],
      warnings: [],
    };
  }

  /**
   * Get health status of OPA service
   */
  async getHealthStatus(): Promise<{ healthy: boolean; opaConnected: boolean }> {
    const opaConnected = await this.opaService.healthCheck();
    return {
      healthy: opaConnected,
      opaConnected,
    };
  }

  /**
   * Get list of available policies
   */
  getAvailablePolicies(): string[] {
    return this.opaService.getPolicies();
  }
}

