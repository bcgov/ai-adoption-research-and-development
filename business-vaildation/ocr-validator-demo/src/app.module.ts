import { Module } from '@nestjs/common';
import { ValidationModule } from './validation/validation.module';
import { AdaptersModule } from './adapters/adapters.module';
import { ValidationController } from './controllers/validation.controller';
import { OcrController } from './controllers/ocr.controller';
import { ValidationService } from './services/validation.service';

@Module({
  imports: [ValidationModule, AdaptersModule],
  controllers: [ValidationController, OcrController],
  providers: [ValidationService],
})
export class AppModule {}

