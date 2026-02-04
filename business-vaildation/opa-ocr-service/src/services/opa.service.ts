import axios, { AxiosInstance } from 'axios';
import * as fs from 'fs';
import * as path from 'path';

/**
 * OPA Service - Handles communication with OPA server
 * Supports both external OPA server (HTTP) and embedded evaluation
 */
export class OpaService {
  private opaClient: AxiosInstance | null = null;
  private opaServerUrl: string;
  private policiesDir: string;
  private policies: Map<string, string> = new Map();

  constructor() {
    this.opaServerUrl = process.env.OPA_SERVER_URL || 'http://localhost:8181';
    // Use process.cwd() for policies directory to work in both dev and production
    const baseDir = process.env.POLICIES_DIR || path.join(process.cwd(), 'policies');
    this.policiesDir = path.isAbsolute(baseDir) ? baseDir : path.join(process.cwd(), baseDir);

    // Initialize OPA client if using external server
    if (this.opaServerUrl) {
      this.opaClient = axios.create({
        baseURL: this.opaServerUrl,
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    }

    // Load policies from directory
    this.loadPolicies();
  }

  /**
   * Load Rego policies from the policies directory
   */
  private loadPolicies(): void {
    try {
      if (!fs.existsSync(this.policiesDir)) {
        console.warn(`Policies directory not found: ${this.policiesDir}`);
        return;
      }

      const files = fs.readdirSync(this.policiesDir);
      const regoFiles = files.filter((file) => file.endsWith('.rego'));

      for (const file of regoFiles) {
        const filePath = path.join(this.policiesDir, file);
        const content = fs.readFileSync(filePath, 'utf-8');
        const policyName = path.basename(file, '.rego');
        this.policies.set(policyName, content);
        console.log(`Loaded policy: ${policyName}`);
      }
    } catch (error) {
      console.error('Error loading policies:', error);
    }
  }

  /**
   * Evaluate input against OPA policies
   */
  async evaluate(input: unknown, policyPackage?: string): Promise<unknown> {
    if (!this.opaClient) {
      throw new Error('OPA client not initialized. Set OPA_SERVER_URL environment variable.');
    }

    const packagePath = policyPackage || 'ocr/validation';
    const url = `/v1/data/${packagePath.replace(/\./g, '/')}`;

    try {
      const response = await this.opaClient.post(url, { input });
      return response.data.result;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `OPA evaluation failed: ${error.response?.status} ${error.response?.statusText} - ${JSON.stringify(error.response?.data)}`
        );
      }
      throw error;
    }
  }

  /**
   * Check if OPA server is healthy
   */
  async healthCheck(): Promise<boolean> {
    if (!this.opaClient) {
      return false;
    }

    try {
      const response = await this.opaClient.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('OPA health check failed:', error);
      return false;
    }
  }

  /**
   * Get list of loaded policies
   */
  getPolicies(): string[] {
    return Array.from(this.policies.keys());
  }

  /**
   * Get policy content by name
   */
  getPolicyContent(policyName: string): string | undefined {
    return this.policies.get(policyName);
  }

  /**
   * Reload policies from directory
   */
  reloadPolicies(): void {
    this.policies.clear();
    this.loadPolicies();
  }
}

