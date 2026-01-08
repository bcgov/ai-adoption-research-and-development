import 'dotenv/config';

/**
 * Main worker entry point
 * Loads all workflow workers
 */

// OCR Workflow workers (Azure Document Intelligence)
import './ocr';

// GitHub Agent Workflow workers (Gemini AI)
import './githubAgent';

console.log('');
console.log('='.repeat(50));
console.log('Camunda 7 Workers Ready');
console.log('='.repeat(50));
console.log('Workflows:');
console.log('  • OCR Document Processing (7 task handlers)');
console.log('  • GitHub AI Agent (1 task handler)');
console.log('='.repeat(50));
