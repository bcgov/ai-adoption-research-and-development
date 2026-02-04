import {
  Controller,
  Post,
  Body,
  HttpCode,
  HttpStatus,
  BadRequestException,
} from '@nestjs/common';
import { OcrAdapter } from '../adapters/ocr.adapter';
import { ValidationService } from '../services/validation.service';
import { InvoiceDto } from '../validation/dto/invoice.dto';

@Controller('api/ocr')
export class OcrController {
  constructor(
    private readonly ocrAdapter: OcrAdapter,
    private readonly validationService: ValidationService,
  ) {}

  @Post('process')
  @HttpCode(HttpStatus.OK)
  async processInvoice(@Body() body: { imageData?: string; customData?: Partial<InvoiceDto> }) {
    try {
      let ocrResult;

      // If custom data is provided, use it for testing
      if (body.customData) {
        ocrResult = await this.ocrAdapter.processInvoiceWithData(body.customData);
      } else {
        // Simulate OCR processing from image data
        const imageData = body.imageData || 'mock-image-data';
        ocrResult = await this.ocrAdapter.processInvoice(imageData);
      }

      // Validate the OCR result
      const validationResult = await this.validationService.validateInvoice(ocrResult.data);

      return {
        ocr: {
          data: ocrResult.data,
          confidence: ocrResult.confidence,
          rawText: ocrResult.rawText,
          processingTime: ocrResult.processingTime,
          errors: ocrResult.errors,
        },
        validation: {
          isValid: validationResult.isValid,
          errors: validationResult.errors,
          schemaErrors: validationResult.schemaErrors,
          dtoErrors: validationResult.dtoErrors,
          customValidatorErrors: validationResult.customValidatorErrors,
        },
      };
    } catch (error) {
      throw new BadRequestException({
        message: 'OCR processing failed',
        error: error.message,
      });
    }
  }
}

