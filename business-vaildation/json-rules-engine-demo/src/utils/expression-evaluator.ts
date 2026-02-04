/**
 * Expression evaluator for calculating values from data
 */

import { DataAccessor } from './data-accessor';

export class ExpressionEvaluator {
  /**
   * Evaluate a simple expression like "quantity * unitPrice"
   * Supports basic arithmetic operations and field references
   */
  static evaluate(expression: string, data: any, context?: any): number {
    if (!expression) {
      return 0;
    }

    // Handle special context variables
    const contextVars: Record<string, any> = {
      currentItem: context?.currentItem || data.currentItem || data,
    };

    // Replace field references with actual values
    let evaluated = expression;
    
    // Extract field references (words that might be field paths)
    const fieldPattern = /([a-zA-Z_][a-zA-Z0-9_.]*)/g;
    const matches = expression.match(fieldPattern);
    
    if (matches) {
      for (const field of matches) {
        // Skip JavaScript keywords and operators
        if (['true', 'false', 'null', 'undefined', 'if', 'else', 'for', 'while', 'return'].includes(field)) {
          continue;
        }
        
        // Check context variables first
        if (contextVars[field] !== undefined) {
          const value = contextVars[field];
          const regex = new RegExp(`\\b${field}\\b`, 'g');
          evaluated = evaluated.replace(regex, String(value));
          continue;
        }
        
        // Try to get value from data or context
        let value = DataAccessor.getValue(data, field);
        if (value === undefined && context) {
          value = DataAccessor.getValue(context, field);
        }
        
        if (value !== undefined) {
          // Replace the field reference with its value
          const regex = new RegExp(`\\b${field}\\b`, 'g');
          evaluated = evaluated.replace(regex, String(value));
        }
      }
    }

    // Evaluate the expression safely
    try {
      // Use Function constructor for safe evaluation
      const result = new Function('return ' + evaluated)();
      return typeof result === 'number' ? result : 0;
    } catch (error) {
      console.warn(`Failed to evaluate expression: ${expression}`, error);
      return 0;
    }
  }

  /**
   * Format a value using a format string
   */
  static format(value: any, formatString: string): string {
    if (value === null || value === undefined) {
      return '';
    }

    // Simple format patterns
    if (formatString === 'currency') {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
      }).format(Number(value));
    }

    if (formatString === 'date') {
      return new Date(value).toISOString().split('T')[0];
    }

    if (formatString === 'datetime') {
      return new Date(value).toISOString();
    }

    if (formatString.startsWith('number:')) {
      const decimals = parseInt(formatString.split(':')[1]) || 2;
      return Number(value).toFixed(decimals);
    }

    // Use format string as template
    return formatString.replace(/\{value\}/g, String(value));
  }
}

