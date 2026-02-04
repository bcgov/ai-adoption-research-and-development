import {
  registerDecorator,
  ValidationOptions,
  ValidatorConstraint,
  ValidatorConstraintInterface,
  ValidationArguments,
} from 'class-validator';

@ValidatorConstraint({ name: 'isValidAmountRange', async: false })
export class AmountRangeValidatorConstraint implements ValidatorConstraintInterface {
  validate(amount: any, args: ValidationArguments): boolean {
    if (typeof amount !== 'number') {
      return false;
    }

    // Check if amount is within acceptable range
    if (amount < 0 || amount > 999999.99) {
      return false;
    }

    // Check decimal precision (max 2 decimal places)
    const decimalPlaces = (amount.toString().split('.')[1] || '').length;
    if (decimalPlaces > 2) {
      return false;
    }

    return true;
  }

  defaultMessage(args: ValidationArguments): string {
    const value = args.value;
    if (typeof value !== 'number') {
      return 'Amount must be a number';
    }
    
    if (value < 0) {
      return 'Amount must be greater than or equal to 0';
    }
    
    if (value > 999999.99) {
      return 'Amount must be less than or equal to 999999.99';
    }
    
    const decimalPlaces = (value.toString().split('.')[1] || '').length;
    if (decimalPlaces > 2) {
      return 'Amount must have at most 2 decimal places';
    }
    
    return 'Amount must be a valid number between 0 and 999999.99 with at most 2 decimal places';
  }
}

export function IsValidAmountRange(validationOptions?: ValidationOptions) {
  return function (object: Object, propertyName: string) {
    registerDecorator({
      target: object.constructor,
      propertyName: propertyName,
      options: validationOptions,
      constraints: [],
      validator: AmountRangeValidatorConstraint,
    });
  };
}

