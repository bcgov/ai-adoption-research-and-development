/**
 * Main entry point for the JSON Rules Engine Demo
 */

import { RulesEngine } from './engine/rules-engine';
import { RuleLoader } from './rules/rule-loader';
import * as path from 'path';

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log('JSON Rules Engine for OCR Post-Processing');
    console.log('\nUsage:');
    console.log('  npm run demo              - Run the demo with sample data');
    console.log('  npm start                 - Start the engine (same as demo)');
    console.log('  node dist/main.js <file>  - Process a JSON file with OCR data');
    console.log('\nExample:');
    console.log('  node dist/main.js ./data/invoice.json');
    return;
  }

  try {
    // Load default rules
    // Handle both compiled (dist) and source (src) paths
    const baseDir = __dirname.includes('dist') 
      ? path.join(__dirname, '../rules')
      : path.join(__dirname, '../../rules');
    const rulesPath = path.join(baseDir, 'default-rules.json');
    console.log(`Loading rules from: ${rulesPath}`);
    const rules = await RuleLoader.loadRules(rulesPath);
    console.log(`Loaded ${rules.length} rules\n`);

    // Initialize engine
    const engine = new RulesEngine(rules);

    // Process input file
    const inputFile = args[0];
    const fs = require('fs');
    const inputData = JSON.parse(fs.readFileSync(inputFile, 'utf-8'));

    console.log('Processing data...\n');
    const result = await engine.process(inputData);

    // Output results
    console.log('=== Processing Results ===\n');
    console.log('Processed Data:');
    console.log(JSON.stringify(result.processedData, null, 2));

    if (result.validationErrors.length > 0) {
      console.log('\nValidation Errors:');
      result.validationErrors.forEach(error => {
        console.log(`  - [${error.severity.toUpperCase()}] ${error.rule}: ${error.message}`);
        if (error.field) {
          console.log(`    Field: ${error.field}`);
        }
      });
    }

    if (result.warnings.length > 0) {
      console.log('\nWarnings:');
      result.warnings.forEach(warning => {
        console.log(`  - ${warning.rule}: ${warning.message}`);
        if (warning.field) {
          console.log(`    Field: ${warning.field}`);
        }
      });
    }

    console.log(`\nApplied Rules: ${result.appliedRules.length}`);
    result.appliedRules.forEach(ruleName => {
      console.log(`  - ${ruleName}`);
    });

    // Write output to file if specified
    if (args[1]) {
      const outputFile = args[1];
      fs.writeFileSync(outputFile, JSON.stringify(result, null, 2));
      console.log(`\nResults written to: ${outputFile}`);
    }
  } catch (error) {
    console.error('Error:', error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(console.error);
}

export { main };

