import 'dotenv/config';

// Start all workers
import './readFileFromDisk';
import './prepareFileData';
import './submitToAzureOCR';
import './extractRequestId';
import './pollOCRResults';
import './incrementRetryCount';
import './extractOCRResults';

console.log('All OCR workflow workers started and ready to process tasks.');






