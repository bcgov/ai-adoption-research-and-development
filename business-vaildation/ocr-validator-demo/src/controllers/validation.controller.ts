import {
  Controller,
  Post,
  Get,
  Body,
  HttpCode,
  HttpStatus,
  BadRequestException,
} from '@nestjs/common';
import { ValidationService } from '../services/validation.service';
import { InvoiceDto } from '../validation/dto/invoice.dto';

@Controller('api/validation')
export class ValidationController {
  constructor(private readonly validationService: ValidationService) {}

  @Post('validate')
  @HttpCode(HttpStatus.OK)
  async validate(@Body() invoiceData: InvoiceDto) {
    try {
      const result = await this.validationService.validateInvoice(invoiceData);
      
      if (!result.isValid) {
        throw new BadRequestException({
          message: 'Validation failed',
          errors: result.errors,
          schemaErrors: result.schemaErrors,
          dtoErrors: result.dtoErrors,
          customValidatorErrors: result.customValidatorErrors,
        });
      }

      return {
        message: 'Validation successful',
        data: invoiceData,
      };
    } catch (error) {
      if (error instanceof BadRequestException) {
        throw error;
      }
      throw new BadRequestException({
        message: 'Validation error',
        error: error.message,
      });
    }
  }

  @Get('schema')
  getSchema() {
    return {
      schema: this.validationService.getSchema(),
    };
  }
}

