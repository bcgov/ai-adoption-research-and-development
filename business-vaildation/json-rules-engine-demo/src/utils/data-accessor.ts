/**
 * Utility for accessing nested data using JSONPath-like syntax
 */

import { JSONPath } from 'jsonpath-plus';

export class DataAccessor {
  /**
   * Get value from data using field path (supports dot notation and JSONPath)
   */
  static getValue(data: any, field: string): any {
    if (!field || !data) {
      return undefined;
    }

    // Handle .length for arrays
    if (field.endsWith('.length')) {
      const baseField = field.substring(0, field.length - 7);
      const value = this.getValue(data, baseField);
      return Array.isArray(value) ? value.length : undefined;
    }

    // Simple dot notation
    if (!field.includes('[') && !field.includes('*')) {
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

    // JSONPath for complex paths
    try {
      const results = JSONPath({ path: field, json: data });
      if (results.length === 0) {
        return undefined;
      }
      if (results.length === 1) {
        return results[0];
      }
      return results;
    } catch (error) {
      // Fallback to dot notation if JSONPath fails
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

  /**
   * Set value in data using field path
   */
  static setValue(data: any, field: string, value: any): void {
    if (!field || data === null || data === undefined) {
      return;
    }

    // Handle array wildcards - set value for all matching items
    if (field.includes('[*]')) {
      const basePath = field.substring(0, field.indexOf('[*]'));
      const restPath = field.substring(field.indexOf('[*]') + 4);
      const array = this.getValue(data, basePath);
      
      if (Array.isArray(array)) {
        array.forEach((item, index) => {
          const itemPath = `${basePath}[${index}]${restPath ? '.' + restPath : ''}`;
          this.setValue(data, itemPath, value);
        });
      }
      return;
    }

    // Simple dot notation
    const parts = field.split('.');
    let current = data;
    
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      
      // Handle array indices
      if (part.includes('[') && part.includes(']')) {
        const arrayName = part.substring(0, part.indexOf('['));
        const index = parseInt(part.substring(part.indexOf('[') + 1, part.indexOf(']')));
        
        if (!current[arrayName]) {
          current[arrayName] = [];
        }
        if (!current[arrayName][index]) {
          current[arrayName][index] = {};
        }
        current = current[arrayName][index];
      } else {
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part];
      }
    }

    const lastPart = parts[parts.length - 1];
    if (lastPart.includes('[') && lastPart.includes(']')) {
      const arrayName = lastPart.substring(0, lastPart.indexOf('['));
      const index = parseInt(lastPart.substring(lastPart.indexOf('[') + 1, lastPart.indexOf(']')));
      if (!current[arrayName]) {
        current[arrayName] = [];
      }
      current[arrayName][index] = value;
    } else {
      current[lastPart] = value;
    }
  }

  /**
   * Check if field exists in data
   */
  static exists(data: any, field: string): boolean {
    const value = this.getValue(data, field);
    return value !== undefined && value !== null;
  }
}

