// extension/source-integration/sciencedirect/index.ts
// ScienceDirect integration with custom metadata extractor

import { BaseSourceIntegration } from '../base-source';
import { MetadataExtractor } from '../metadata-extractor';
import { loguru } from '../../utils/logger';

const logger = loguru.getLogger('sciencedirect-integration');

/**
 * Custom metadata extractor for ScienceDirect pages
 */
class ScienceDirectMetadataExtractor extends MetadataExtractor {
  /**
   * Extract title using citation meta tags
   */
  protected extractTitle(): string {
    const metaTitle = this.getMetaContent('meta[name="citation_title"]') ||
                      this.getMetaContent('meta[property="og:title"]');
    return metaTitle || super.extractTitle();
  }

  /**
   * Extract authors from citation meta tags
   */
  protected extractAuthors(): string {
    const citationAuthors: string[] = [];
    this.document.querySelectorAll('meta[name="citation_author"]').forEach(el => {
      const content = el.getAttribute('content');
      if (content) citationAuthors.push(content);
    });

    if (citationAuthors.length > 0) {
      return citationAuthors.join(', ');
    }

    return super.extractAuthors();
  }

  /**
   * Extract abstract/description
   */
  protected extractDescription(): string {
    const metaDescription = this.getMetaContent('meta[name="description"]') ||
                            this.getMetaContent('meta[property="og:description"]');
    return metaDescription || super.extractDescription();
  }

  /**
   * Extract publication date
   */
  protected extractPublishedDate(): string {
    return this.getMetaContent('meta[name="citation_publication_date"]') ||
           this.getMetaContent('meta[name="citation_online_date"]') ||
           super.extractPublishedDate();
  }

  /**
   * Extract DOI
   */
  protected extractDoi(): string {
    return this.getMetaContent('meta[name="citation_doi"]') || super.extractDoi();
  }

  /**
   * Extract journal name
   */
  protected extractJournalName(): string {
    return this.getMetaContent('meta[name="citation_journal_title"]') || super.extractJournalName();
  }

  /**
   * Extract keywords/tags
   */
  protected extractTags(): string[] {
    const keywords = this.getMetaContent('meta[name="citation_keywords"]') ||
                    this.getMetaContent('meta[name="keywords"]');

    if (keywords) {
      return keywords.split(/[;,]/).map(tag => tag.trim()).filter(Boolean);
    }

    return super.extractTags();
  }
}

/**
 * ScienceDirect integration for Elsevier journals
 */
export class ScienceDirectIntegration extends BaseSourceIntegration {
  readonly id = 'sciencedirect';
  readonly name = 'ScienceDirect';

  // URL pattern for ScienceDirect articles with PII
  readonly urlPatterns = [
    /sciencedirect\.com\/science\/article\/pii\/([A-Z0-9]+)/i,
    /sciencedirect\.com\/science\/article\/abs\/pii\/([A-Z0-9]+)/i,
  ];

  /**
   * Extract paper ID (PII) from URL
   */
  extractPaperId(url: string): string | null {
    for (const pattern of this.urlPatterns) {
      const match = url.match(pattern);
      if (match) {
        return match[1];
      }
    }
    return null;
  }

  /**
   * Create custom metadata extractor for ScienceDirect
   */
  protected createMetadataExtractor(document: Document): MetadataExtractor {
    return new ScienceDirectMetadataExtractor(document);
  }
}

// Export singleton instance
export const scienceDirectIntegration = new ScienceDirectIntegration();
