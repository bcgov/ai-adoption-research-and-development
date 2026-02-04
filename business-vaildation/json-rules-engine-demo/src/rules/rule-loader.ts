/**
 * Loads rules from JSON files
 */

import * as fs from 'fs';
import * as path from 'path';
import { Rule, RuleSet } from '../engine/types';

export class RuleLoader {
  /**
   * Load rules from a JSON file
   */
  static async loadRules(filePath: string): Promise<Rule[]> {
    try {
      const fullPath = path.resolve(filePath);
      const fileContent = fs.readFileSync(fullPath, 'utf-8');
      const ruleSet: RuleSet | Rule[] = JSON.parse(fileContent);

      // Handle both RuleSet format and array format
      if (Array.isArray(ruleSet)) {
        return ruleSet;
      }

      return ruleSet.rules || [];
    } catch (error) {
      throw new Error(
        `Failed to load rules from ${filePath}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Load rules from multiple JSON files
   */
  static async loadRulesFromFiles(filePaths: string[]): Promise<Rule[]> {
    const allRules: Rule[] = [];

    for (const filePath of filePaths) {
      const rules = await this.loadRules(filePath);
      allRules.push(...rules);
    }

    return allRules;
  }

  /**
   * Load rules from a directory
   */
  static async loadRulesFromDirectory(directoryPath: string): Promise<Rule[]> {
    try {
      const fullPath = path.resolve(directoryPath);
      const files = fs.readdirSync(fullPath);
      const jsonFiles = files.filter(file => file.endsWith('.json'));

      const allRules: Rule[] = [];

      for (const file of jsonFiles) {
        const filePath = path.join(fullPath, file);
        const rules = await this.loadRules(filePath);
        allRules.push(...rules);
      }

      return allRules;
    } catch (error) {
      throw new Error(
        `Failed to load rules from directory ${directoryPath}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Validate rule structure
   */
  static validateRule(rule: any): rule is Rule {
    if (!rule || typeof rule !== 'object') {
      return false;
    }

    if (!rule.name || typeof rule.name !== 'string') {
      return false;
    }

    if (!rule.type || !['validation', 'transformation', 'enrichment', 'correction'].includes(rule.type)) {
      return false;
    }

    if (!rule.condition || typeof rule.condition !== 'object') {
      return false;
    }

    if (!rule.action || typeof rule.action !== 'object') {
      return false;
    }

    return true;
  }

  /**
   * Validate and filter rules
   */
  static validateRules(rules: any[]): Rule[] {
    const validRules: Rule[] = [];

    for (const rule of rules) {
      if (this.validateRule(rule)) {
        validRules.push(rule);
      } else {
        console.warn(`Invalid rule skipped: ${rule.name || 'unnamed'}`);
      }
    }

    return validRules;
  }
}

