/**
 * Processor for correction rules (auto-fix OCR errors)
 */

import { Rule } from '../engine/types';
import { RuleExecutor } from '../engine/rule-executor';
import { OcrHelpers } from '../utils/ocr-helpers';

export class CorrectionProcessor {
  /**
   * Process a correction rule
   */
  process(rule: Rule, data: any): any {
    if (rule.action.type !== 'correct') {
      return data;
    }

    // If the action uses OCR helpers, apply them
    if (rule.action.operation === 'regex_replace' && rule.action.params?.useOcrHelpers) {
      const field = rule.action.field;
      if (field) {
        const currentValue = this.getFieldValue(data, field);
        if (typeof currentValue === 'string') {
          const corrected = OcrHelpers.fixCommonErrors(currentValue);
          this.setFieldValue(data, field, corrected);
          return data;
        }
      }
    }

    // Otherwise, use standard rule executor
    return RuleExecutor.execute(rule.action, data);
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

  private setFieldValue(data: any, field: string, value: any): void {
    if (!field) {
      return;
    }

    const parts = field.split('.');
    let current = data;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (!current[part]) {
        current[part] = {};
      }
      current = current[part];
    }
    current[parts[parts.length - 1]] = value;
  }
}

