// extension/source-integration/springer/index.ts
// Springer integration with custom metadata extractor

import { BaseSourceIntegration } from '../base-source';
import { MetadataExtractor } from '../metadata-extractor';
import { loguru } from '../../utils/logger';

const logger = loguru.getLogger('springer-integration');

/**
 * Custom metadata extractor for Springer pages
 */
class SpringerMetadataExtractor extends MetadataExtractor {
  /**
   * Extract title using citation meta tags
   */
  protected extractTitle(): string {
    const metaTitle = this.getMetaContent('meta[name="citation_title"]') ||
                      this.getMetaContent('meta[property="og:title"]') ||
                      this.getMetaContent('meta[name="dc.title"]');
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

    // Fallback to DC creator
    const dcCreators: string[] = [];
    this.document.querySelectorAll('meta[name="dc.creator"]').forEach(el => {
      const content = el.getAttribute('content');
      if (content) dcCreators.push(content);
    });

    if (dcCreators.length > 0) {
      return dcCreators.join(', ');
    }

    return super.extractAuthors();
  }

  /**
   * Extract abstract/description
   */
  protected extractDescription(): string {
    const metaDescription = this.getMetaContent('meta[name="dc.description"]') ||
                            this.getMetaContent('meta[name="description"]') ||
                            this.getMetaContent('meta[property="og:description"]');
    return metaDescription || super.extractDescription();
  }

  /**
   * Extract publication date
   */
  protected extractPublishedDate(): string {
    return this.getMetaContent('meta[name="citation_publication_date"]') ||
           this.getMetaContent('meta[name="citation_online_date"]') ||
           this.getMetaContent('meta[name="dc.date"]') ||
           super.extractPublishedDate();
  }

  /**
   * Extract DOI
   */
  protected extractDoi(): string {
    return this.getMetaContent('meta[name="citation_doi"]') ||
           this.getMetaContent('meta[name="dc.identifier"]') ||
           super.extractDoi();
  }

  /**
   * Extract journal name
   */
  protected extractJournalName(): string {
    return this.getMetaContent('meta[name="citation_journal_title"]') ||
           this.getMetaContent('meta[name="citation_conference_title"]') ||
           this.getMetaContent('meta[name="prism.publicationName"]') ||
           super.extractJournalName();
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
 * Springer integration for Springer Link articles
 */
export class SpringerIntegration extends BaseSourceIntegration {
  readonly id = 'springer';
  readonly name = 'Springer';

  // URL patterns for Springer articles
  readonly urlPatterns = [
    /link\.springer\.com\/article\/(10\.\d+\/[^\s?]+)/,
    /link\.springer\.com\/chapter\/(10\.\d+\/[^\s?]+)/,
  ];

  /**
   * Extract paper ID (DOI) from URL
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
   * Create custom metadata extractor for Springer
   */
  protected createMetadataExtractor(document: Document): MetadataExtractor {
    return new SpringerMetadataExtractor(document);
  }
}

// Export singleton instance
export const springerIntegration = new SpringerIntegration();
