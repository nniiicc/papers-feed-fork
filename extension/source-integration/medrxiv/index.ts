// extension/source-integration/medrxiv/index.ts
// medRxiv integration with custom metadata extractor

import { BaseSourceIntegration } from '../base-source';
import { MetadataExtractor } from '../metadata-extractor';
import { loguru } from '../../utils/logger';

const logger = loguru.getLogger('medrxiv-integration');

/**
 * Custom metadata extractor for medRxiv pages
 */
class MedRxivMetadataExtractor extends MetadataExtractor {
  /**
   * Extract title using citation meta tags
   */
  protected extractTitle(): string {
    const metaTitle = this.getMetaContent('meta[name="citation_title"]') ||
                      this.getMetaContent('meta[property="og:title"]') ||
                      this.getMetaContent('meta[name="DC.Title"]');
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
    const metaDescription = this.getMetaContent('meta[name="citation_abstract"]') ||
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
           this.getMetaContent('meta[name="DC.Date"]') ||
           super.extractPublishedDate();
  }

  /**
   * Extract DOI
   */
  protected extractDoi(): string {
    return this.getMetaContent('meta[name="citation_doi"]') ||
           this.getMetaContent('meta[name="DC.Identifier"]') ||
           super.extractDoi();
  }

  /**
   * Extract journal/venue name
   */
  protected extractJournalName(): string {
    return this.getMetaContent('meta[name="citation_journal_title"]') ||
           'medRxiv' ||
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
 * medRxiv integration for medical preprints
 */
export class MedRxivIntegration extends BaseSourceIntegration {
  readonly id = 'medrxiv';
  readonly name = 'medRxiv';

  // URL patterns for medRxiv preprints
  readonly urlPatterns = [
    /medrxiv\.org\/content\/(10\.\d+\/[^v\s?]+)v?\d*/,
    /medrxiv\.org\/content\/early\/\d+\/\d+\/\d+\/(\d+)/,
  ];

  /**
   * Extract paper ID (DOI or early ID) from URL
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
   * Create custom metadata extractor for medRxiv
   */
  protected createMetadataExtractor(document: Document): MetadataExtractor {
    return new MedRxivMetadataExtractor(document);
  }
}

// Export singleton instance
export const medRxivIntegration = new MedRxivIntegration();
