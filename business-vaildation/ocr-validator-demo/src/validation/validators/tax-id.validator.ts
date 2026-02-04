import {
  registerDecorator,
  ValidationOptions,
  ValidatorConstraint,
  ValidatorConstraintInterface,
  ValidationArguments,
} from 'class-validator';

@ValidatorConstraint({ name: 'isValidTaxId', async: false })
export class TaxIdValidatorConstraint implements ValidatorConstraintInterface {
  validate(taxId: any, args: ValidationArguments): boolean {
    if (typeof taxId !== 'string') {
      return false;
    }

    // Basic format validation: alphanumeric, 9-15 characters
    const taxIdPattern = /^[A-Z0-9]{9,15}$/;
    return taxIdPattern.test(taxId);
  }

  defaultMessage(args: ValidationArguments): string {
    const value = args.value;
    if (typeof value !== 'string') {
      return 'Tax ID must be a string';
    }
    
    return 'Tax ID must be 9-15 alphanumeric characters (uppercase letters and numbers only)';
  }
}

export function IsValidTaxId(validationOptions?: ValidationOptions) {
  return function (object: Object, propertyName: string) {
    registerDecorator({
      target: object.constructor,
      propertyName: propertyName,
      options: validationOptions,
      constraints: [],
      validator: TaxIdValidatorConstraint,
    });
  };
}

