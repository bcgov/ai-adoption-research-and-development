/**
 * Evaluates rule conditions against data
 */

import { Condition, ConditionOperator } from './types';
import { DataAccessor } from '../utils/data-accessor';

export class RuleEvaluator {
  /**
   * Evaluate a condition against data
   */
  static evaluate(condition: Condition, data: any): boolean {
    if (!condition || !data) {
      return false;
    }

    const operator = condition.operator;

    switch (operator) {
      case 'always':
        return true;
      case 'and':
        return this.evaluateAnd(condition, data);
      case 'or':
        return this.evaluateOr(condition, data);
      case 'not':
        return this.evaluateNot(condition, data);
      case 'exists':
        return DataAccessor.exists(data, condition.field || '');
      case 'not_exists':
        return !DataAccessor.exists(data, condition.field || '');
      case 'equals':
        return this.evaluateEquals(condition, data);
      case 'not_equals':
        return !this.evaluateEquals(condition, data);
      case 'contains':
        return this.evaluateContains(condition, data);
      case 'not_contains':
        return !this.evaluateContains(condition, data);
      case 'regex':
        return this.evaluateRegex(condition, data);
      case 'gt':
        return this.evaluateComparison(condition, data, (a, b) => a > b);
      case 'gte':
        return this.evaluateComparison(condition, data, (a, b) => a >= b);
      case 'lt':
        return this.evaluateComparison(condition, data, (a, b) => a < b);
      case 'lte':
        return this.evaluateComparison(condition, data, (a, b) => a <= b);
      case 'in':
        return this.evaluateIn(condition, data);
      case 'not_in':
        return !this.evaluateIn(condition, data);
      case 'starts_with':
        return this.evaluateStartsWith(condition, data);
      case 'ends_with':
        return this.evaluateEndsWith(condition, data);
      default:
        console.warn(`Unknown operator: ${operator}`);
        return false;
    }
  }

  private static evaluateAnd(condition: Condition, data: any): boolean {
    if (!condition.conditions || condition.conditions.length === 0) {
      return false;
    }
    return condition.conditions.every(subCondition =>
      this.evaluate(subCondition, data)
    );
  }

  private static evaluateOr(condition: Condition, data: any): boolean {
    if (!condition.conditions || condition.conditions.length === 0) {
      return false;
    }
    return condition.conditions.some(subCondition =>
      this.evaluate(subCondition, data)
    );
  }

  private static evaluateNot(condition: Condition, data: any): boolean {
    if (!condition.conditions || condition.conditions.length === 0) {
      return false;
    }
    // NOT operator should have a single condition
    return !this.evaluate(condition.conditions[0], data);
  }

  private static evaluateEquals(condition: Condition, data: any): boolean {
    if (!condition.field) {
      return false;
    }
    const fieldValue = DataAccessor.getValue(data, condition.field);
    return this.compareValues(fieldValue, condition.value);
  }

  private static evaluateContains(condition: Condition, data: any): boolean {
    if (!condition.field) {
      return false;
    }
    const fieldValue = DataAccessor.getValue(data, condition.field);
    if (typeof fieldValue === 'string' && typeof condition.value === 'string') {
      return fieldValue.includes(condition.value);
    }
    if (Array.isArray(fieldValue)) {
      return fieldValue.includes(condition.value);
    }
    return false;
  }

  private static evaluateRegex(condition: Condition, data: any): boolean {
    if (!condition.field || typeof condition.value !== 'string') {
      return false;
    }
    const fieldValue = DataAccessor.getValue(data, condition.field);
    if (typeof fieldValue !== 'string') {
      return false;
    }
    try {
      const regex = new RegExp(condition.value, condition.params?.flags || '');
      return regex.test(fieldValue);
    } catch (error) {
      console.warn(`Invalid regex pattern: ${condition.value}`, error);
      return false;
    }
  }

  private static evaluateComparison(
    condition: Condition,
    data: any,
    compareFn: (a: number, b: number) => boolean
  ): boolean {
    if (!condition.field) {
      return false;
    }
    const fieldValue = DataAccessor.getValue(data, condition.field);
    const compareValue = condition.value;
    
    if (typeof fieldValue === 'number' && typeof compareValue === 'number') {
      return compareFn(fieldValue, compareValue);
    }
    
    // Try to convert to numbers
    const numValue = Number(fieldValue);
    const numCompare = Number(compareValue);
    if (!isNaN(numValue) && !isNaN(numCompare)) {
      return compareFn(numValue, numCompare);
    }
    
    return false;
  }

  private static evaluateIn(condition: Condition, data: any): boolean {
    if (!condition.field || !Array.isArray(condition.value)) {
      return false;
    }
    const fieldValue = DataAccessor.getValue(data, condition.field);
    return condition.value.includes(fieldValue);
  }

  private static evaluateStartsWith(condition: Condition, data: any): boolean {
    if (!condition.field || typeof condition.value !== 'string') {
      return false;
    }
    const fieldValue = DataAccessor.getValue(data, condition.field);
    if (typeof fieldValue !== 'string') {
      return false;
    }
    return fieldValue.startsWith(condition.value);
  }

  private static evaluateEndsWith(condition: Condition, data: any): boolean {
    if (!condition.field || typeof condition.value !== 'string') {
      return false;
    }
    const fieldValue = DataAccessor.getValue(data, condition.field);
    if (typeof fieldValue !== 'string') {
      return false;
    }
    return fieldValue.endsWith(condition.value);
  }

  private static compareValues(a: any, b: any): boolean {
    if (a === b) {
      return true;
    }
    // Handle type coercion for numbers
    if (typeof a === 'number' && typeof b === 'string') {
      return a === Number(b);
    }
    if (typeof a === 'string' && typeof b === 'number') {
      return Number(a) === b;
    }
    // Case-insensitive string comparison
    if (typeof a === 'string' && typeof b === 'string') {
      return a.toLowerCase() === b.toLowerCase();
    }
    return false;
  }
}

