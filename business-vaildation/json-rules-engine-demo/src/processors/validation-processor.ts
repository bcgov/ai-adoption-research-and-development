/**
 * Processor for validation rules
 */

import { Rule, ValidationError } from '../engine/types';
import { RuleExecutor } from '../engine/rule-executor';

export class ValidationProcessor {
  /**
   * Process a validation rule
   */
  process(rule: Rule, data: any): { errors: ValidationError[]; warnings: ValidationError[] } {
    const errors: ValidationError[] = [];
    const warnings: ValidationError[] = [];

    if (rule.action.type !== 'validate') {
      return { errors, warnings };
    }

    const error: ValidationError = {
      rule: rule.name,
      field: rule.action.field,
      message: rule.action.message || `Validation failed: ${rule.name}`,
      value: rule.action.field ? this.getFieldValue(data, rule.action.field) : undefined,
      severity: rule.onFailure === 'warn' ? 'warning' : 'error',
    };

    if (error.severity === 'error') {
      errors.push(error);
    } else {
      warnings.push(error);
    }

    return { errors, warnings };
  }

  private getFieldValue(data: any, field: string): any {
    if (!field) {
      return undefined;
    }

    const parts = field.split('.');
    let value = data;
    for (const part of parts) {
      if (value === null || value === undefined) {
        return undefined;
      }
      value = value[part];
    }
    return value;
  }
}

