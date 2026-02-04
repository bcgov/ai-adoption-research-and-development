import { Module } from '@nestjs/common';
import { OcrAdapter } from './ocr.adapter';
import { ReferenceDataAdapter } from './reference-data.adapter';

@Module({
  providers: [OcrAdapter, ReferenceDataAdapter],
  exports: [OcrAdapter, ReferenceDataAdapter],
})
export class AdaptersModule {}

