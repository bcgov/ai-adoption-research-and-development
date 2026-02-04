/**
 * Processor for transformation rules
 */

import { Rule } from '../engine/types';
import { RuleExecutor } from '../engine/rule-executor';

export class TransformationProcessor {
  /**
   * Process a transformation rule
   */
  process(rule: Rule, data: any): any {
    if (rule.action.type !== 'transform') {
      return data;
    }

    return RuleExecutor.execute(rule.action, data);
  }
}

