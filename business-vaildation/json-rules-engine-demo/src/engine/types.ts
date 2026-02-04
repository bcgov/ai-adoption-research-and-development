/**
 * Type definitions for the JSON Rules Engine
 */

export type RuleType = 'validation' | 'transformation' | 'enrichment' | 'correction';

export type ConditionOperator =
  | 'always'
  | 'and'
  | 'or'
  | 'not'
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'regex'
  | 'exists'
  | 'not_exists'
  | 'gt'
  | 'gte'
  | 'lt'
  | 'lte'
  | 'in'
  | 'not_in'
  | 'starts_with'
  | 'ends_with';

export type ActionOperation =
  | 'set'
  | 'append'
  | 'remove'
  | 'format'
  | 'lookup'
  | 'regex_replace'
  | 'calculate'
  | 'uppercase'
  | 'lowercase'
  | 'trim';

export type FlowControl = 'continue' | 'stop' | 'warn';

export interface Condition {
  operator: ConditionOperator;
  field?: string;
  value?: any;
  conditions?: Condition[];
}

export interface Action {
  type: 'validate' | 'transform' | 'enrich' | 'correct';
  field?: string;
  operation?: ActionOperation;
  value?: any;
  message?: string;
  params?: Record<string, any>;
  expression?: string;
}

export interface Rule {
  name: string;
  description?: string;
  priority?: number;
  enabled?: boolean;
  type: RuleType;
  condition: Condition;
  action: Action;
  onSuccess?: FlowControl;
  onFailure?: FlowControl;
}

export interface ValidationError {
  rule: string;
  field?: string;
  message: string;
  value?: any;
  severity: 'error' | 'warning';
}

export interface ProcessingResult {
  processedData: any;
  validationErrors: ValidationError[];
  warnings: ValidationError[];
  appliedRules: string[];
  executionLog: ExecutionLogEntry[];
}

export interface ExecutionLogEntry {
  rule: string;
  type: RuleType;
  conditionMatched: boolean;
  actionExecuted: boolean;
  timestamp: string;
  error?: string;
}

export interface RuleSet {
  name?: string;
  description?: string;
  version?: string;
  rules: Rule[];
}

