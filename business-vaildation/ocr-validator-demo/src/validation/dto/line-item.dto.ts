import { IsString, IsNumber, Min, Max, Length } from 'class-validator';
import { Type } from 'class-transformer';
import { IsValidAmountRange } from '../validators/amount-range.validator';

export class LineItemDto {
  @IsString()
  @Length(1, 200)
  description: string;

  @IsNumber()
  @Min(0.01)
  @Max(10000)
  @Type(() => Number)
  quantity: number;

  @IsNumber()
  @IsValidAmountRange()
  @Min(0)
  @Max(99999.99)
  @Type(() => Number)
  unitPrice: number;
}

