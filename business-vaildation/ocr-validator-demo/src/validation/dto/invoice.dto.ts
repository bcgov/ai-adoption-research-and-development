import {
  IsString,
  IsNumber,
  IsArray,
  IsOptional,
  Min,
  Max,
  Length,
  Matches,
  ValidateNested,
  ArrayMinSize,
} from 'class-validator';
import { Type } from 'class-transformer';
import { IsValidDateFormat } from '../validators/date-format.validator';
import { IsValidAmountRange } from '../validators/amount-range.validator';
import { LineItemDto } from './line-item.dto';

export class InvoiceDto {
  @IsString()
  @Length(3, 50)
  invoiceNumber: string;

  @IsString()
  @IsValidDateFormat()
  date: string;

  @IsNumber()
  @IsValidAmountRange()
  @Min(0)
  @Max(999999.99)
  @Type(() => Number)
  amount: number;

  @IsString()
  @Matches(/^[A-Z0-9]{9,15}$/, {
    message: 'Tax ID must be 9-15 alphanumeric characters (uppercase letters and numbers only)',
  })
  taxId: string;

  @IsString()
  @Length(2, 100)
  vendorName: string;

  @IsArray()
  @ArrayMinSize(1)
  @ValidateNested({ each: true })
  @Type(() => LineItemDto)
  lineItems: LineItemDto[];

  @IsOptional()
  @IsString()
  @Matches(/^[A-Z]{3}$/, {
    message: 'Currency must be a 3-letter ISO 4217 code',
  })
  currency?: string;

  @IsOptional()
  @IsString()
  @Length(0, 500)
  notes?: string;
}

