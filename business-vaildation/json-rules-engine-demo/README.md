# JSON Rules Engine for OCR Post-Processing

A flexible, JSON-driven rules engine for post-processing OCR results. Rules are defined in JSON format, allowing dynamic configuration without code changes.

## Features

- **JSON-driven rule definitions** - No code changes needed to modify rules
- **Four rule types**:
  - **Validation Rules**: Check conditions and report errors/warnings
  - **Transformation Rules**: Clean, normalize, and format data
  - **Enrichment Rules**: Add computed fields and lookup values
  - **Correction Rules**: Auto-fix common OCR errors
- **Complex condition support** - Nested logical operators (and, or, not)
- **JSONPath field access** - Access nested data structures
- **Rule priorities** - Control execution order
- **Comprehensive error reporting** - Detailed validation results
- **OCR-specific utilities** - Common error pattern detection and correction

## Installation

```bash
npm install
npm run build
```

## Quick Start

### Run the Demo

```bash
npm run demo
```

This will process several sample OCR scenarios and show how the rules engine:
- Corrects OCR character errors (0→O, 1→I, etc.)
- Normalizes data formats (tax IDs, invoice numbers)
- Enriches data (calculates totals, adds timestamps)
- Validates data integrity

### Process Your Own Data

```bash
# Process a JSON file
node dist/main.js ./path/to/your-data.json

# Save results to a file
node dist/main.js ./path/to/your-data.json ./output.json
```

## Usage

### Basic Example

```typescript
import { RulesEngine } from './src/engine/rules-engine';
import { RuleLoader } from './src/rules/rule-loader';

// Load rules from JSON file
const rules = await RuleLoader.loadRules('./rules/default-rules.json');

// Initialize engine
const engine = new RulesEngine(rules);

// Process OCR result
const ocrResult = {
  invoiceNumber: "INV-2024-001",
  amount: 1250.50,
  taxId: "tax-123-456",  // Needs normalization
  vendorName: "Acme C0rp",  // OCR error (0 instead of O)
  lineItems: [
    { description: "Service", quantity: 1, unitPrice: 1250.50 }
  ]
};

const result = await engine.process(ocrResult);

// Result contains:
// - processedData: Transformed/enriched data
// - validationErrors: Array of validation errors
// - warnings: Array of warnings
// - appliedRules: List of rules that were executed
// - executionLog: Detailed execution log
```

## Rule Format

Rules are defined in JSON with the following structure:

```json
{
  "name": "rule-name",
  "description": "Rule description",
  "priority": 100,
  "enabled": true,
  "type": "validation|transformation|enrichment|correction",
  "condition": {
    "operator": "and|or|not|equals|contains|regex|exists|gt|lt|gte|lte",
    "field": "path.to.field",
    "value": "expected-value",
    "conditions": []
  },
  "action": {
    "type": "validate|transform|enrich|correct",
    "field": "path.to.field",
    "operation": "set|append|remove|format|lookup|regex_replace|calculate",
    "value": "new-value",
    "params": {}
  },
  "onSuccess": "continue|stop",
  "onFailure": "continue|stop|warn"
}
```

## Rule Types

### Validation Rules

Check conditions and report errors or warnings:

```json
{
  "name": "validate-amount-positive",
  "type": "validation",
  "priority": 100,
  "condition": {
    "operator": "lt",
    "field": "amount",
    "value": 0
  },
  "action": {
    "type": "validate",
    "field": "amount",
    "message": "Amount must be positive"
  }
}
```

### Transformation Rules

Clean, normalize, and format data:

```json
{
  "name": "normalize-tax-id",
  "type": "transformation",
  "priority": 80,
  "condition": {
    "operator": "exists",
    "field": "taxId"
  },
  "action": {
    "type": "transform",
    "field": "taxId",
    "operation": "regex_replace",
    "params": {
      "pattern": "[^A-Z0-9]",
      "replacement": "",
      "flags": "g"
    }
  }
}
```

### Enrichment Rules

Add computed fields and lookup values:

```json
{
  "name": "calculate-line-total",
  "type": "enrichment",
  "priority": 50,
  "condition": {
    "operator": "exists",
    "field": "lineItems"
  },
  "action": {
    "type": "enrich",
    "field": "lineItems[*].total",
    "operation": "calculate",
    "expression": "quantity * unitPrice"
  }
}
```

### Correction Rules

Auto-fix common OCR errors:

```json
{
  "name": "fix-ocr-character-errors",
  "type": "correction",
  "priority": 90,
  "condition": {
    "operator": "contains",
    "field": "vendorName",
    "value": "0"
  },
  "action": {
    "type": "correct",
    "field": "vendorName",
    "operation": "regex_replace",
    "params": {
      "pattern": "([A-Z])0([A-Z])",
      "replacement": "$1O$2"
    }
  }
}
```

## Condition Operators

- **Logical**: `and`, `or`, `not`, `always`
- **Comparison**: `equals`, `not_equals`, `gt`, `gte`, `lt`, `lte`
- **String**: `contains`, `not_contains`, `starts_with`, `ends_with`, `regex`
- **Existence**: `exists`, `not_exists`
- **Membership**: `in`, `not_in`

## Action Operations

- **Data manipulation**: `set`, `append`, `remove`
- **String operations**: `uppercase`, `lowercase`, `trim`, `regex_replace`
- **Formatting**: `format`
- **Calculation**: `calculate` (with expression evaluation)
- **Lookup**: `lookup` (for reference data)

## Field Paths

Fields can be accessed using dot notation or JSONPath:

- Simple: `invoiceNumber`, `amount`
- Nested: `lineItems[0].description`
- Array wildcard: `lineItems[*].total` (applies to all items)

## Example Rule Sets

The project includes example rule sets in `src/rules/examples/`:

- `invoice-validation.json` - Validation rules for invoices
- `invoice-transformation.json` - Data normalization rules
- `invoice-enrichment.json` - Data enrichment rules
- `ocr-correction.json` - OCR error correction rules

## Project Structure

```
json-rules-engine-demo/
├── src/
│   ├── main.ts                          # Entry point
│   ├── engine/
│   │   ├── rules-engine.ts              # Core rules engine
│   │   ├── rule-evaluator.ts            # Rule condition evaluator
│   │   ├── rule-executor.ts              # Rule action executor
│   │   └── types.ts                     # TypeScript interfaces
│   ├── rules/
│   │   ├── rule-loader.ts               # Load rules from JSON files
│   │   └── examples/                    # Example rule sets
│   ├── processors/
│   │   ├── validation-processor.ts      # Validation rule processor
│   │   ├── transformation-processor.ts  # Transformation rule processor
│   │   ├── enrichment-processor.ts      # Enrichment rule processor
│   │   └── correction-processor.ts      # Correction rule processor
│   ├── utils/
│   │   ├── expression-evaluator.ts      # Evaluate expressions
│   │   ├── data-accessor.ts             # Access nested data paths
│   │   └── ocr-helpers.ts               # OCR-specific utilities
│   └── examples/
│       ├── demo.ts                      # Demo script
│       └── sample-ocr-data.json         # Sample OCR results
├── rules/
│   └── default-rules.json              # Default rule set
├── package.json
├── tsconfig.json
└── README.md
```

## API Reference

### RulesEngine

Main engine class for processing data through rules.

```typescript
class RulesEngine {
  constructor(rules: Rule[]);
  async process(data: any): Promise<ProcessingResult>;
  addRule(rule: Rule): void;
  addRules(rules: Rule[]): void;
  removeRule(ruleName: string): void;
  getRules(): Rule[];
  getRulesByType(type: RuleType): Rule[];
  setRuleEnabled(ruleName: string, enabled: boolean): void;
}
```

### RuleLoader

Utility for loading rules from JSON files.

```typescript
class RuleLoader {
  static async loadRules(filePath: string): Promise<Rule[]>;
  static async loadRulesFromFiles(filePaths: string[]): Promise<Rule[]>;
  static async loadRulesFromDirectory(directoryPath: string): Promise<Rule[]>;
  static validateRule(rule: any): rule is Rule;
  static validateRules(rules: any[]): Rule[];
}
```

## Processing Result

The `process()` method returns a `ProcessingResult` object:

```typescript
interface ProcessingResult {
  processedData: any;              // Transformed/enriched data
  validationErrors: ValidationError[];  // Validation errors
  warnings: ValidationError[];     // Warnings
  appliedRules: string[];          // Names of rules that were executed
  executionLog: ExecutionLogEntry[];  // Detailed execution log
}
```

## Development

```bash
# Build the project
npm run build

# Run in development mode
npm run dev

# Run the demo
npm run demo

# Run tests (if configured)
npm test
```

## Technology Stack

- **TypeScript**: Type-safe implementation
- **jsonpath-plus**: For JSONPath field access
- **Node.js**: Runtime environment

## License

MIT

