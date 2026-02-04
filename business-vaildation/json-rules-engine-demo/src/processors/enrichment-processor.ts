/**
 * Processor for enrichment rules
 */

import { Rule } from '../engine/types';
import { RuleExecutor } from '../engine/rule-executor';

export class EnrichmentProcessor {
  /**
   * Process an enrichment rule
   */
  process(rule: Rule, data: any): any {
    if (rule.action.type !== 'enrich') {
      return data;
    }

    return RuleExecutor.execute(rule.action, data);
  }
}

