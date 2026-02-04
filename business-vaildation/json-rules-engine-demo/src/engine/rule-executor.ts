/**
 * Executes rule actions on data
 */

import { Action, ActionOperation } from './types';
import { DataAccessor } from '../utils/data-accessor';
import { ExpressionEvaluator } from '../utils/expression-evaluator';
import { OcrHelpers } from '../utils/ocr-helpers';

export class RuleExecutor {
  /**
   * Execute an action on data
   */
  static execute(action: Action, data: any, context?: any): any {
    if (!action || !data) {
      return data;
    }

    const operation = action.operation || 'set';

    switch (operation) {
      case 'set':
        return this.executeSet(action, data);
      case 'append':
        return this.executeAppend(action, data);
      case 'remove':
        return this.executeRemove(action, data);
      case 'format':
        return this.executeFormat(action, data);
      case 'regex_replace':
        return this.executeRegexReplace(action, data);
      case 'calculate':
        return this.executeCalculate(action, data, context);
      case 'uppercase':
        return this.executeUppercase(action, data);
      case 'lowercase':
        return this.executeLowercase(action, data);
      case 'trim':
        return this.executeTrim(action, data);
      default:
        console.warn(`Unknown operation: ${operation}`);
        return data;
    }
  }

  private static executeSet(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    let value = action.value;
    
    // Handle special values
    if (typeof value === 'string') {
      if (value === 'NOW' || value === '$NOW') {
        value = new Date().toISOString();
      } else if (value.startsWith('$')) {
        // If value is a string starting with $, treat it as a field reference
        const refField = value.substring(1);
        const refValue = DataAccessor.getValue(data, refField);
        // Only use the reference if it exists, otherwise keep the original string
        if (refValue !== undefined) {
          value = refValue;
        }
      }
    }

    DataAccessor.setValue(data, action.field, value);
    return data;
  }

  private static executeAppend(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    const currentValue = DataAccessor.getValue(data, action.field);
    const newValue = action.value;

    if (Array.isArray(currentValue)) {
      DataAccessor.setValue(data, action.field, [...currentValue, newValue]);
    } else if (typeof currentValue === 'string') {
      DataAccessor.setValue(data, action.field, currentValue + String(newValue));
    } else {
      DataAccessor.setValue(data, action.field, newValue);
    }

    return data;
  }

  private static executeRemove(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    // For arrays, remove the value
    const currentValue = DataAccessor.getValue(data, action.field);
    if (Array.isArray(currentValue)) {
      const filtered = currentValue.filter(item => item !== action.value);
      DataAccessor.setValue(data, action.field, filtered);
    } else {
      // For objects, delete the field
      const parts = action.field.split('.');
      let current = data;
      for (let i = 0; i < parts.length - 1; i++) {
        current = current[parts[i]];
        if (!current) return data;
      }
      delete current[parts[parts.length - 1]];
    }

    return data;
  }

  private static executeFormat(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    const currentValue = DataAccessor.getValue(data, action.field);
    const formatString = action.params?.format || action.value || '';

    const formatted = ExpressionEvaluator.format(currentValue, formatString);
    DataAccessor.setValue(data, action.field, formatted);

    return data;
  }

  private static executeRegexReplace(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    const currentValue = DataAccessor.getValue(data, action.field);
    if (typeof currentValue !== 'string') {
      return data;
    }

    const pattern = action.params?.pattern || action.params?.regex || '';
    const replacement = action.params?.replacement || '';
    const flags = action.params?.flags || 'g';

    try {
      const regex = new RegExp(pattern, flags);
      const replaced = currentValue.replace(regex, replacement);
      DataAccessor.setValue(data, action.field, replaced);
    } catch (error) {
      console.warn(`Invalid regex pattern: ${pattern}`, error);
    }

    return data;
  }

  private static executeCalculate(action: Action, data: any, context?: any): any {
    if (!action.field || !action.expression) {
      return data;
    }

    // Handle array wildcards for calculations
    if (action.field.includes('[*]')) {
      const basePath = action.field.substring(0, action.field.indexOf('[*]'));
      const restPath = action.field.substring(action.field.indexOf('[*]') + 4);
      const array = DataAccessor.getValue(data, basePath);
      
      if (Array.isArray(array)) {
        array.forEach((item, index) => {
          const itemPath = `${basePath}[${index}]${restPath ? '.' + restPath : ''}`;
          const itemData = { ...data, currentItem: item };
          const result = ExpressionEvaluator.evaluate(action.expression!, itemData, context);
          DataAccessor.setValue(data, itemPath, result);
        });
      }
      return data;
    }

    const result = ExpressionEvaluator.evaluate(action.expression, data, context);
    DataAccessor.setValue(data, action.field, result);

    return data;
  }

  private static executeUppercase(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    const currentValue = DataAccessor.getValue(data, action.field);
    if (typeof currentValue === 'string') {
      DataAccessor.setValue(data, action.field, currentValue.toUpperCase());
    }

    return data;
  }

  private static executeLowercase(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    const currentValue = DataAccessor.getValue(data, action.field);
    if (typeof currentValue === 'string') {
      DataAccessor.setValue(data, action.field, currentValue.toLowerCase());
    }

    return data;
  }

  private static executeTrim(action: Action, data: any): any {
    if (!action.field) {
      return data;
    }

    const currentValue = DataAccessor.getValue(data, action.field);
    if (typeof currentValue === 'string') {
      DataAccessor.setValue(data, action.field, currentValue.trim());
    }

    return data;
  }
}

