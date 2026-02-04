/**
 * Core rules engine that processes data through a set of rules
 */

import { Rule, RuleType, ProcessingResult, ExecutionLogEntry, ValidationError } from './types';
import { RuleEvaluator } from './rule-evaluator';
import { RuleExecutor } from './rule-executor';
import { ValidationProcessor } from '../processors/validation-processor';
import { TransformationProcessor } from '../processors/transformation-processor';
import { EnrichmentProcessor } from '../processors/enrichment-processor';
import { CorrectionProcessor } from '../processors/correction-processor';

export class RulesEngine {
  private rules: Rule[];
  private validationProcessor: ValidationProcessor;
  private transformationProcessor: TransformationProcessor;
  private enrichmentProcessor: EnrichmentProcessor;
  private correctionProcessor: CorrectionProcessor;

  constructor(rules: Rule[] = []) {
    this.rules = this.sortRulesByPriority(rules);
    this.validationProcessor = new ValidationProcessor();
    this.transformationProcessor = new TransformationProcessor();
    this.enrichmentProcessor = new EnrichmentProcessor();
    this.correctionProcessor = new CorrectionProcessor();
  }

  /**
   * Process data through all rules
   */
  async process(data: any): Promise<ProcessingResult> {
    // Deep clone data to avoid mutating original
    let processedData = JSON.parse(JSON.stringify(data));
    
    const validationErrors: ValidationError[] = [];
    const warnings: ValidationError[] = [];
    const appliedRules: string[] = [];
    const executionLog: ExecutionLogEntry[] = [];

    // Process rules in priority order
    for (const rule of this.rules) {
      if (rule.enabled === false) {
        continue;
      }

      const logEntry: ExecutionLogEntry = {
        rule: rule.name,
        type: rule.type,
        conditionMatched: false,
        actionExecuted: false,
        timestamp: new Date().toISOString(),
      };

      try {
        // Evaluate condition
        const conditionMatched = RuleEvaluator.evaluate(rule.condition, processedData);
        logEntry.conditionMatched = conditionMatched;

        if (conditionMatched) {
          // Execute action based on rule type
          switch (rule.type) {
            case 'validation':
              const validationResult = this.validationProcessor.process(rule, processedData);
              validationErrors.push(...validationResult.errors);
              warnings.push(...validationResult.warnings);
              break;

            case 'transformation':
              processedData = this.transformationProcessor.process(rule, processedData);
              break;

            case 'enrichment':
              processedData = this.enrichmentProcessor.process(rule, processedData);
              break;

            case 'correction':
              processedData = this.correctionProcessor.process(rule, processedData);
              break;
          }

          logEntry.actionExecuted = true;
          appliedRules.push(rule.name);

          // Handle flow control
          if (rule.onSuccess === 'stop') {
            break;
          }
        } else {
          // Condition not matched - check onFailure behavior
          if (rule.onFailure === 'warn') {
            warnings.push({
              rule: rule.name,
              message: `Rule condition not met: ${rule.description || rule.name}`,
              severity: 'warning',
            });
          }
        }
      } catch (error) {
        logEntry.error = error instanceof Error ? error.message : String(error);
        validationErrors.push({
          rule: rule.name,
          message: `Error executing rule: ${error instanceof Error ? error.message : String(error)}`,
          severity: 'error',
        });
      }

      executionLog.push(logEntry);
    }

    return {
      processedData,
      validationErrors,
      warnings,
      appliedRules,
      executionLog,
    };
  }

  /**
   * Add a rule to the engine
   */
  addRule(rule: Rule): void {
    this.rules.push(rule);
    this.rules = this.sortRulesByPriority(this.rules);
  }

  /**
   * Add multiple rules to the engine
   */
  addRules(rules: Rule[]): void {
    this.rules.push(...rules);
    this.rules = this.sortRulesByPriority(this.rules);
  }

  /**
   * Remove a rule by name
   */
  removeRule(ruleName: string): void {
    this.rules = this.rules.filter(rule => rule.name !== ruleName);
  }

  /**
   * Get all rules
   */
  getRules(): Rule[] {
    return [...this.rules];
  }

  /**
   * Get rules by type
   */
  getRulesByType(type: RuleType): Rule[] {
    return this.rules.filter(rule => rule.type === type);
  }

  /**
   * Enable/disable a rule
   */
  setRuleEnabled(ruleName: string, enabled: boolean): void {
    const rule = this.rules.find(r => r.name === ruleName);
    if (rule) {
      rule.enabled = enabled;
    }
  }

  /**
   * Sort rules by priority (higher priority first, then by name)
   */
  private sortRulesByPriority(rules: Rule[]): Rule[] {
    return [...rules].sort((a, b) => {
      const priorityA = a.priority ?? 100;
      const priorityB = b.priority ?? 100;
      
      if (priorityA !== priorityB) {
        return priorityB - priorityA; // Higher priority first
      }
      
      return a.name.localeCompare(b.name);
    });
  }
}

