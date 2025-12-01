// extension/source-integration/acl/index.ts
// ACL Anthology integration with custom metadata extractor

import { BaseSourceIntegration } from '../base-source';
import { MetadataExtractor } from '../metadata-extractor';
import { loguru } from '../../utils/logger';

const logger = loguru.getLogger('acl-integration');

/**
 * Custom metadata extractor for ACL Anthology pages
 */
class ACLMetadataExtractor extends MetadataExtractor {
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
           this.getMetaContent('meta[name="citation_date"]') ||
           super.extractPublishedDate();
  }

  /**
   * Extract DOI
   */
  protected extractDoi(): string {
    return this.getMetaContent('meta[name="citation_doi"]') || super.extractDoi();
  }

  /**
   * Extract conference name
   */
  protected extractJournalName(): string {
    return this.getMetaContent('meta[name="citation_conference_title"]') ||
           this.getMetaContent('meta[name="citation_journal_title"]') ||
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
 * ACL Anthology integration for computational linguistics papers
 */
export class ACLIntegration extends BaseSourceIntegration {
  readonly id = 'acl';
  readonly name = 'ACL Anthology';

  // URL patterns for ACL Anthology papers
  readonly urlPatterns = [
    /aclanthology\.org\/([A-Z0-9]+\.\d+-\d+)/,
    /aclweb\.org\/anthology\/([A-Z0-9]+\.\d+-\d+)/,
  ];

  /**
   * Extract paper ID from URL
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
   * Create custom metadata extractor for ACL
   */
  protected createMetadataExtractor(document: Document): MetadataExtractor {
    return new ACLMetadataExtractor(document);
  }
}

// Export singleton instance
export const aclIntegration = new ACLIntegration();
