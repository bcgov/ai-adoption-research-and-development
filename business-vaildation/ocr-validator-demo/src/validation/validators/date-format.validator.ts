import {
  registerDecorator,
  ValidationOptions,
  ValidatorConstraint,
  ValidatorConstraintInterface,
  ValidationArguments,
} from 'class-validator';

@ValidatorConstraint({ name: 'isValidDateFormat', async: false })
export class DateFormatValidatorConstraint implements ValidatorConstraintInterface {
  validate(dateString: any, args: ValidationArguments): boolean {
    if (typeof dateString !== 'string') {
      return false;
    }

    // Check ISO 8601 format
    const iso8601Regex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$/;
    if (!iso8601Regex.test(dateString)) {
      return false;
    }

    // Parse the date
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return false;
    }

    // Check if date is not in the future
    const now = new Date();
    if (date > now) {
      return false;
    }

    return true;
  }

  defaultMessage(args: ValidationArguments): string {
    const value = args.value;
    if (typeof value !== 'string') {
      return 'Date must be a string';
    }
    
    const date = new Date(value);
    if (isNaN(date.getTime())) {
      return 'Date must be a valid ISO 8601 date-time string';
    }
    
    if (date > new Date()) {
      return 'Date cannot be in the future';
    }
    
    return 'Date must be a valid ISO 8601 date-time string and not in the future';
  }
}

export function IsValidDateFormat(validationOptions?: ValidationOptions) {
  return function (object: Object, propertyName: string) {
    registerDecorator({
      target: object.constructor,
      propertyName: propertyName,
      options: validationOptions,
      constraints: [],
      validator: DateFormatValidatorConstraint,
    });
  };
}

