/**
 * Demo script showing the JSON Rules Engine in action
 */

import { RulesEngine } from '../engine/rules-engine';
import { RuleLoader } from '../rules/rule-loader';
import * as fs from 'fs';
import * as path from 'path';

async function runDemo() {
  console.log('=== JSON Rules Engine Demo ===\n');

  try {
    // Load rules from default rules file
    // Handle both compiled (dist) and source (src) paths
    const baseDir = __dirname.includes('dist') 
      ? path.join(__dirname, '../../rules')
      : path.join(__dirname, '../../../rules');
    const rulesPath = path.join(baseDir, 'default-rules.json');
    console.log(`Loading rules from: ${rulesPath}`);
    const rules = await RuleLoader.loadRules(rulesPath);
    console.log(`Loaded ${rules.length} rules\n`);

    // Initialize engine
    const engine = new RulesEngine(rules);

    // Load sample OCR data
    // Handle both compiled (dist) and source (src) paths
    const sampleDataPath = path.join(__dirname, 'sample-ocr-data.json');
    console.log(`Loading sample data from: ${sampleDataPath}`);
    const sampleData = JSON.parse(fs.readFileSync(sampleDataPath, 'utf-8'));
    console.log(`Loaded ${sampleData.length} sample scenarios\n`);

    // Process each sample
    for (const sample of sampleData) {
      console.log(`\n${'='.repeat(60)}`);
      console.log(`Processing: ${sample.name}`);
      console.log('='.repeat(60));
      console.log('\nInput Data:');
      console.log(JSON.stringify(sample.data, null, 2));

      const result = await engine.process(sample.data);

      console.log('\n--- Processing Results ---');
      console.log('\nProcessed Data:');
      console.log(JSON.stringify(result.processedData, null, 2));

      if (result.validationErrors.length > 0) {
        console.log('\nValidation Errors:');
        result.validationErrors.forEach(error => {
          console.log(`  - [${error.severity.toUpperCase()}] ${error.rule}: ${error.message}`);
          if (error.field) {
            console.log(`    Field: ${error.field}, Value: ${JSON.stringify(error.value)}`);
          }
        });
      }

      if (result.warnings.length > 0) {
        console.log('\nWarnings:');
        result.warnings.forEach(warning => {
          console.log(`  - ${warning.rule}: ${warning.message}`);
          if (warning.field) {
            console.log(`    Field: ${warning.field}, Value: ${JSON.stringify(warning.value)}`);
          }
        });
      }

      if (result.appliedRules.length > 0) {
        console.log('\nApplied Rules:');
        result.appliedRules.forEach(ruleName => {
          console.log(`  - ${ruleName}`);
        });
      }

      console.log(`\nTotal rules executed: ${result.executionLog.length}`);
      console.log(`Rules applied: ${result.appliedRules.length}`);
      console.log(`Validation errors: ${result.validationErrors.length}`);
      console.log(`Warnings: ${result.warnings.length}`);
    }

    console.log('\n\n=== Demo Complete ===');
  } catch (error) {
    console.error('Error running demo:', error);
    process.exit(1);
  }
}

// Run demo if executed directly
if (require.main === module) {
  runDemo().catch(console.error);
}

export { runDemo };

