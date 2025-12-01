// extension/source-integration/acm/index.ts
// ACM Digital Library integration with custom metadata extractor

import { BaseSourceIntegration } from '../base-source';
import { MetadataExtractor } from '../metadata-extractor';
import { loguru } from '../../utils/logger';

const logger = loguru.getLogger('acm-integration');

/**
 * Custom metadata extractor for ACM DL pages
 */
class ACMMetadataExtractor extends MetadataExtractor {
  /**
   * Extract title using citation meta tags
   */
  protected extractTitle(): string {
    const metaTitle = this.getMetaContent('meta[name="citation_title"]') ||
                      this.getMetaContent('meta[property="og:title"]') ||
                      this.getMetaContent('meta[name="dc.Title"]');
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
           this.getMetaContent('meta[name="citation_date"]') ||
           this.getMetaContent('meta[name="dc.Date"]') ||
           super.extractPublishedDate();
  }

  /**
   * Extract DOI
   */
  protected extractDoi(): string {
    return this.getMetaContent('meta[name="citation_doi"]') ||
           this.getMetaContent('meta[name="dc.Identifier"]') ||
           super.extractDoi();
  }

  /**
   * Extract journal/conference name
   */
  protected extractJournalName(): string {
    return this.getMetaContent('meta[name="citation_journal_title"]') ||
           this.getMetaContent('meta[name="citation_conference_title"]') ||
           this.getMetaContent('meta[name="dc.Source"]') ||
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
 * ACM Digital Library integration
 */
export class ACMIntegration extends BaseSourceIntegration {
  readonly id = 'acm';
  readonly name = 'ACM Digital Library';

  // URL patterns for ACM articles
  readonly urlPatterns = [
    /dl\.acm\.org\/doi\/(10\.\d+\/\d+)/,
    /dl\.acm\.org\/doi\/abs\/(10\.\d+\/\d+)/,
    /dl\.acm\.org\/citation\.cfm\?id=(\d+)/,
  ];

  /**
   * Extract paper ID (DOI or citation ID) from URL
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
   * Create custom metadata extractor for ACM
   */
  protected createMetadataExtractor(document: Document): MetadataExtractor {
    return new ACMMetadataExtractor(document);
  }
}

// Export singleton instance
export const acmIntegration = new ACMIntegration();
