import { Injectable } from '@nestjs/common';
import { InvoiceDto } from '../validation/dto/invoice.dto';

export interface OcrResult {
  data: Partial<InvoiceDto>;
  confidence: number;
  rawText: string;
  processingTime: number;
  errors?: string[];
}

@Injectable()
export class OcrAdapter {
  private readonly mockProcessingDelay = 500; // milliseconds

  /**
   * Simulates OCR processing of an invoice image
   * Returns structured data with potential OCR errors
   */
  async processInvoice(imageData: Buffer | string): Promise<OcrResult> {
    // Simulate processing delay
    await this.delay(this.mockProcessingDelay);

    // Simulate different OCR scenarios based on a simple hash of the input
    const inputHash = this.hashInput(imageData);
    const scenario = inputHash % 4;

    switch (scenario) {
      case 0:
        // Perfect OCR result
        return {
          data: {
            invoiceNumber: 'INV-2024-001',
            date: new Date().toISOString(),
            amount: 1250.50,
            taxId: 'TAX123456789',
            vendorName: 'Acme Corporation',
            lineItems: [
              {
                description: 'Software License',
                quantity: 1,
                unitPrice: 1000.00,
              },
              {
                description: 'Support Services',
                quantity: 2.5,
                unitPrice: 100.20,
              },
            ],
            currency: 'USD',
          },
          confidence: 0.95,
          rawText: 'Invoice INV-2024-001\nDate: 2024-01-15\nAmount: $1,250.50\n...',
          processingTime: this.mockProcessingDelay,
        };

      case 1:
        // OCR with some errors (missing fields, wrong format)
        return {
          data: {
            invoiceNumber: 'INV-2024-002',
            date: '2024-01-15', // Missing time component
            amount: 2500.75,
            taxId: 'tax-123-456', // Wrong format (lowercase, dashes)
            vendorName: 'Tech Solutions Inc',
            lineItems: [
              {
                description: 'Hardware',
                quantity: 5,
                unitPrice: 500.15,
              },
            ],
          },
          confidence: 0.72,
          rawText: 'Invoice INV-2024-002\nDate: 2024-01-15\nAmount: $2,500.75\n...',
          processingTime: this.mockProcessingDelay,
          errors: ['Date format incomplete', 'Tax ID format incorrect'],
        };

      case 2:
        // OCR with validation issues (future date, negative amount)
        return {
          data: {
            invoiceNumber: 'INV-2024-003',
            date: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
            amount: -100.00, // Negative amount
            taxId: 'TAX987654321',
            vendorName: 'Global Services',
            lineItems: [
              {
                description: 'Consulting',
                quantity: 10,
                unitPrice: 100.00,
              },
            ],
          },
          confidence: 0.68,
          rawText: 'Invoice INV-2024-003\nDate: 2025-12-31\nAmount: -$100.00\n...',
          processingTime: this.mockProcessingDelay,
          errors: ['Date is in the future', 'Amount is negative'],
        };

      case 3:
        // OCR with missing required fields
        return {
          data: {
            invoiceNumber: 'INV-2024-004',
            amount: 750.25,
            vendorName: 'Quick Services',
            // Missing: date, taxId, lineItems
          },
          confidence: 0.55,
          rawText: 'Invoice INV-2024-004\nAmount: $750.25\n...',
          processingTime: this.mockProcessingDelay,
          errors: ['Missing required field: date', 'Missing required field: taxId', 'Missing required field: lineItems'],
        };

      default:
        throw new Error('Unexpected OCR scenario');
    }
  }

  /**
   * Simulates OCR processing with custom data (for testing)
   */
  async processInvoiceWithData(customData: Partial<InvoiceDto>): Promise<OcrResult> {
    await this.delay(this.mockProcessingDelay);

    return {
      data: customData,
      confidence: 0.85,
      rawText: JSON.stringify(customData),
      processingTime: this.mockProcessingDelay,
    };
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private hashInput(input: Buffer | string): number {
    const str = typeof input === 'string' ? input : input.toString('base64');
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
  }
}

