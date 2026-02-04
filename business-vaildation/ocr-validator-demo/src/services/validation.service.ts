import { Injectable } from '@nestjs/common';
import { validate } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import * as fs from 'fs';
import * as path from 'path';
import { InvoiceDto } from '../validation/dto/invoice.dto';
import { ReferenceDataAdapter } from '../adapters/reference-data.adapter';

export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  schemaErrors?: ValidationError[];
  dtoErrors?: ValidationError[];
  customValidatorErrors?: ValidationError[];
}

@Injectable()
export class ValidationService {
  private ajv: Ajv;
  private invoiceSchema: any;

  constructor(private readonly referenceDataAdapter: ReferenceDataAdapter) {
    // Initialize AJV with formats support
    this.ajv = new Ajv({ allErrors: true, strict: false });
    addFormats(this.ajv);

    // Load JSON schema
    const schemaPath = path.join(__dirname, '../validation/schemas/invoice.schema.json');
    this.invoiceSchema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));
  }

  /**
   * Validates invoice data using multiple validation strategies
   */
  async validateInvoice(data: any): Promise<ValidationResult> {
    const errors: ValidationError[] = [];

    // 1. JSON Schema Validation
    const schemaErrors = this.validateWithJsonSchema(data);
    errors.push(...schemaErrors);

    // 2. DTO Validation (class-validator)
    const dtoErrors = await this.validateWithDto(data);
    errors.push(...dtoErrors);

    // 3. Custom Business Logic Validation
    const customErrors = await this.validateCustomBusinessRules(data);
    errors.push(...customErrors);

    return {
      isValid: errors.length === 0,
      errors,
      schemaErrors,
      dtoErrors,
      customValidatorErrors: customErrors,
    };
  }

  /**
   * Validates using JSON Schema
   */
  private validateWithJsonSchema(data: any): ValidationError[] {
    const errors: ValidationError[] = [];
    const validate = this.ajv.compile(this.invoiceSchema);
    const valid = validate(data);

    if (!valid && validate.errors) {
      for (const error of validate.errors) {
        const field = error.instancePath || error.schemaPath || 'root';
        errors.push({
          field: field.replace(/^\//, ''), // Remove leading slash
          message: error.message || 'Schema validation failed',
          value: error.data,
        });
      }
    }

    return errors;
  }

  /**
   * Validates using DTO (class-validator)
   */
  private async validateWithDto(data: any): Promise<ValidationError[]> {
    const errors: ValidationError[] = [];

    try {
      const invoiceDto = plainToInstance(InvoiceDto, data);
      const validationErrors = await validate(invoiceDto);

      for (const error of validationErrors) {
        const field = error.property;
        const messages = Object.values(error.constraints || {});
        
        for (const message of messages) {
          errors.push({
            field,
            message,
            value: error.value,
          });
        }
      }
    } catch (error) {
      errors.push({
        field: 'dto',
        message: `DTO validation failed: ${error.message}`,
      });
    }

    return errors;
  }

  /**
   * Custom business logic validation
   */
  private async validateCustomBusinessRules(data: any): Promise<ValidationError[]> {
    const errors: ValidationError[] = [];

    // Validate tax ID against reference data
    if (data.taxId) {
      try {
        const vendorInfo = await this.referenceDataAdapter.validateTaxId(data.taxId);
        if (!vendorInfo.isValid) {
          errors.push({
            field: 'taxId',
            message: `Tax ID ${data.taxId} is not valid or not found in reference data`,
            value: data.taxId,
          });
        } else if (vendorInfo.status === 'suspended') {
          errors.push({
            field: 'taxId',
            message: `Vendor with tax ID ${data.taxId} is suspended`,
            value: data.taxId,
          });
        }
      } catch (error) {
        // Reference data service unavailable - log but don't fail validation
        console.warn('Reference data service unavailable:', error.message);
      }
    }

    // Validate line items sum matches total amount
    if (data.lineItems && Array.isArray(data.lineItems) && data.amount !== undefined) {
      const calculatedTotal = data.lineItems.reduce(
        (sum: number, item: any) => sum + (item.quantity || 0) * (item.unitPrice || 0),
        0,
      );

      const tolerance = 0.01; // Allow small rounding differences
      if (Math.abs(calculatedTotal - data.amount) > tolerance) {
        errors.push({
          field: 'amount',
          message: `Invoice amount (${data.amount}) does not match sum of line items (${calculatedTotal.toFixed(2)})`,
          value: data.amount,
        });
      }
    }

    return errors;
  }

  /**
   * Get the JSON schema
   */
  getSchema(): any {
    return this.invoiceSchema;
  }
}

