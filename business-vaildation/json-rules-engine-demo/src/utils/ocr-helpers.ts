/**
 * OCR-specific utility functions for common error patterns
 */

export class OcrHelpers {
  /**
   * Common OCR character substitutions
   */
  private static readonly commonSubstitutions: Map<string, string> = new Map([
    ['0', 'O'], // Zero to letter O (in text context)
    ['1', 'I'], // One to letter I (in text context)
    ['5', 'S'], // Five to letter S (in text context)
    ['8', 'B'], // Eight to letter B (in text context)
  ]);

  /**
   * Common OCR error patterns and their corrections
   */
  private static readonly errorPatterns: Array<{ pattern: RegExp; replacement: string }> = [
    // Fix common character confusions in uppercase text
    { pattern: /([A-Z])0([A-Z])/g, replacement: '$1O$2' }, // Letter0Letter -> LetterOLetter
    { pattern: /([A-Z])1([A-Z])/g, replacement: '$1I$2' }, // Letter1Letter -> LetterILetter
    { pattern: /([A-Z])5([A-Z])/g, replacement: '$1S$2' }, // Letter5Letter -> LetterSSLetter
    { pattern: /([A-Z])8([A-Z])/g, replacement: '$1B$2' }, // Letter8Letter -> LetterBLetter
    
    // Fix spacing issues
    { pattern: /([a-z])([A-Z])/g, replacement: '$1 $2' }, // Add space between lowercase and uppercase
    { pattern: /\s+/g, replacement: ' ' }, // Normalize multiple spaces
    
    // Fix common date format issues
    { pattern: /(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})/g, replacement: '$1/$2/$3' }, // Normalize date separators
    
    // Fix currency symbol issues
    { pattern: /([0-9,]+)\s*[S$]/g, replacement: '$$$1' }, // Fix dollar sign placement
  ];

  /**
   * Fix common OCR errors in text
   */
  static fixCommonErrors(text: string): string {
    if (!text || typeof text !== 'string') {
      return text;
    }

    let fixed = text;

    // Apply error pattern corrections
    for (const { pattern, replacement } of this.errorPatterns) {
      fixed = fixed.replace(pattern, replacement);
    }

    return fixed.trim();
  }

  /**
   * Normalize text for comparison (remove extra spaces, convert to uppercase)
   */
  static normalizeText(text: string): string {
    if (!text || typeof text !== 'string') {
      return '';
    }
    return text
      .trim()
      .replace(/\s+/g, ' ')
      .toUpperCase();
  }

  /**
   * Extract numbers from text (useful for amounts, IDs, etc.)
   */
  static extractNumbers(text: string): string {
    if (!text || typeof text !== 'string') {
      return '';
    }
    return text.replace(/\D/g, '');
  }

  /**
   * Check if text likely contains OCR errors
   */
  static hasLikelyErrors(text: string): boolean {
    if (!text || typeof text !== 'string') {
      return false;
    }

    // Check for common OCR error patterns
    const errorIndicators = [
      /[A-Z]0[A-Z]/, // Letter0Letter pattern
      /[A-Z]1[A-Z]/, // Letter1Letter pattern
      /\s{3,}/, // Multiple consecutive spaces
      /[^\w\s\-.,$%()]/g, // Unusual characters
    ];

    return errorIndicators.some(pattern => pattern.test(text));
  }

  /**
   * Suggest corrections for a text value
   */
  static suggestCorrections(text: string): string[] {
    const suggestions: string[] = [];
    
    if (!text || typeof text !== 'string') {
      return suggestions;
    }

    // Generate suggestions based on common patterns
    const fixed = this.fixCommonErrors(text);
    if (fixed !== text) {
      suggestions.push(fixed);
    }

    return suggestions;
  }
}

