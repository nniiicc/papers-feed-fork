// extension/source-integration/ieee/index.ts
// IEEE Xplore integration with custom metadata extractor

import { BaseSourceIntegration } from '../base-source';
import { MetadataExtractor } from '../metadata-extractor';
import { loguru } from '../../utils/logger';

const logger = loguru.getLogger('ieee-integration');

/**
 * Custom metadata extractor for IEEE Xplore pages
 */
class IEEEMetadataExtractor extends MetadataExtractor {
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

    // Fallback to HTML extraction
    const authorElements = this.document.querySelectorAll('.authors-info .author span');
    if (authorElements.length > 0) {
      return Array.from(authorElements)
        .map(el => el.textContent?.trim())
        .filter(Boolean)
        .join(', ');
    }

    return super.extractAuthors();
  }

  /**
   * Extract abstract/description
   */
  protected extractDescription(): string {
    const metaDescription = this.getMetaContent('meta[name="description"]') ||
                            this.getMetaContent('meta[property="og:description"]');

    // IEEE often has abstract in a specific div
    if (!metaDescription) {
      const abstractDiv = this.document.querySelector('.abstract-text');
      if (abstractDiv) {
        return abstractDiv.textContent?.trim() || '';
      }
    }

    return metaDescription || super.extractDescription();
  }

  /**
   * Extract publication date
   */
  protected extractPublishedDate(): string {
    return this.getMetaContent('meta[name="citation_publication_date"]') ||
           this.getMetaContent('meta[name="citation_date"]') ||
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
   * Extract journal/conference name
   */
  protected extractJournalName(): string {
    return this.getMetaContent('meta[name="citation_journal_title"]') ||
           this.getMetaContent('meta[name="citation_conference_title"]') ||
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

    // IEEE-specific keyword extraction from HTML
    const keywordElements = this.document.querySelectorAll('.keywords .keyword');
    if (keywordElements.length > 0) {
      return Array.from(keywordElements)
        .map(el => el.textContent?.trim())
        .filter(Boolean) as string[];
    }

    return super.extractTags();
  }
}

/**
 * IEEE Xplore integration
 */
export class IEEEIntegration extends BaseSourceIntegration {
  readonly id = 'ieee';
  readonly name = 'IEEE Xplore';

  // URL patterns for IEEE articles
  readonly urlPatterns = [
    /ieeexplore\.ieee\.org\/document\/(\d+)/,
    /ieeexplore\.ieee\.org\/abstract\/document\/(\d+)/,
  ];

  /**
   * Extract paper ID (document number) from URL
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
   * Create custom metadata extractor for IEEE
   */
  protected createMetadataExtractor(document: Document): MetadataExtractor {
    return new IEEEMetadataExtractor(document);
  }
}

// Export singleton instance
export const ieeeIntegration = new IEEEIntegration();
