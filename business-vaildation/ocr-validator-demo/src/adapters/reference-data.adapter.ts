import { Injectable } from '@nestjs/common';

export interface VendorInfo {
  taxId: string;
  name: string;
  isValid: boolean;
  registeredDate?: string;
  status?: 'active' | 'inactive' | 'suspended';
}

@Injectable()
export class ReferenceDataAdapter {
  // Mock database of valid tax IDs
  private readonly mockVendorDatabase: Map<string, VendorInfo> = new Map([
    ['TAX123456789', {
      taxId: 'TAX123456789',
      name: 'Acme Corporation',
      isValid: true,
      registeredDate: '2020-01-15',
      status: 'active',
    }],
    ['TAX987654321', {
      taxId: 'TAX987654321',
      name: 'Global Services',
      isValid: true,
      registeredDate: '2019-06-20',
      status: 'active',
    }],
    ['TAX111222333', {
      taxId: 'TAX111222333',
      name: 'Tech Solutions Inc',
      isValid: true,
      registeredDate: '2021-03-10',
      status: 'active',
    }],
    ['TAX444555666', {
      taxId: 'TAX444555666',
      name: 'Suspended Vendor LLC',
      isValid: true,
      registeredDate: '2018-11-05',
      status: 'suspended',
    }],
    ['TAX777888999', {
      taxId: 'TAX777888999',
      name: 'Inactive Company',
      isValid: false,
      registeredDate: '2017-09-12',
      status: 'inactive',
    }],
  ]);

  private readonly mockApiDelay = 200; // milliseconds

  /**
   * Validates a tax ID against the reference data service
   */
  async validateTaxId(taxId: string): Promise<VendorInfo> {
    // Simulate API call delay
    await this.delay(this.mockApiDelay);

    // Normalize tax ID (uppercase, remove dashes/spaces)
    const normalizedTaxId = taxId.toUpperCase().replace(/[-\s]/g, '');

    // Check if tax ID exists in mock database
    const vendorInfo = this.mockVendorDatabase.get(normalizedTaxId);

    if (vendorInfo) {
      return vendorInfo;
    }

    // Tax ID not found - return invalid result
    return {
      taxId: normalizedTaxId,
      name: 'Unknown Vendor',
      isValid: false,
      status: 'inactive',
    };
  }

  /**
   * Gets vendor information by tax ID
   */
  async getVendorInfo(taxId: string): Promise<VendorInfo | null> {
    await this.delay(this.mockApiDelay);

    const normalizedTaxId = taxId.toUpperCase().replace(/[-\s]/g, '');
    const vendorInfo = this.mockVendorDatabase.get(normalizedTaxId);

    return vendorInfo || null;
  }

  /**
   * Simulates a network error scenario (for testing)
   */
  async validateTaxIdWithError(taxId: string): Promise<VendorInfo> {
    await this.delay(this.mockApiDelay);
    throw new Error('Reference data service unavailable');
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

