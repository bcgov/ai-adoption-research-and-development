import { OCRResult } from '../types/ocr-result.types';

/**
 * Request DTO for policy evaluation
 */
export interface PolicyEvaluationRequest {
  ocrResult: OCRResult;
  policyPackage?: string; // Optional: specific policy package to evaluate
}

/**
 * Policy violation details
 */
export interface PolicyViolation {
  rule: string;
  message: string;
  severity: 'error' | 'warning';
  field?: string;
  value?: unknown;
}

/**
 * Policy evaluation result
 */
export interface PolicyEvaluationResult {
  valid: boolean;
  violations: PolicyViolation[];
  warnings: PolicyViolation[];
  dataQualityScore?: number;
  businessRuleCompliance?: boolean;
  metadata?: Record<string, unknown>;
}

/**
 * Response DTO for policy evaluation
 */
export interface PolicyEvaluationResponse {
  allowed: boolean;
  result: PolicyEvaluationResult;
}

/**
 * Policy package information
 */
export interface PolicyPackage {
  name: string;
  description?: string;
  rules: string[];
}

