// extension/source-integration/registry.ts
// Central registry for all source integrations

import { SourceIntegration } from './types';
import { arxivIntegration } from './arxiv';
import { openReviewIntegration } from './openreview';
import { natureIntegration } from './nature';
import { pnasIntegration } from './pnas';
import { scienceDirectIntegration } from './sciencedirect';
import { springerIntegration } from './springer';
import { ieeeIntegration } from './ieee';
import { acmIntegration } from './acm';
import { aclIntegration } from './acl';
import { neuripsIntegration } from './neurips';
import { cvfIntegration } from './cvf';
import { wileyIntegration } from './wiley';
import { plosIntegration } from './plos';
import { bioRxivIntegration } from './biorxiv';
import { medRxivIntegration } from './medrxiv';
import { ssrnIntegration } from './ssrn';
import { semanticScholarIntegration } from './semanticscholar';
import { miscIntegration } from './misc';

export const sourceIntegrations: SourceIntegration[] = [
  arxivIntegration,
  openReviewIntegration,
  natureIntegration,
  pnasIntegration,
  scienceDirectIntegration,
  springerIntegration,
  ieeeIntegration,
  acmIntegration,
  aclIntegration,
  neuripsIntegration,
  cvfIntegration,
  wileyIntegration,
  plosIntegration,
  bioRxivIntegration,
  medRxivIntegration,
  ssrnIntegration,
  semanticScholarIntegration,
  miscIntegration,
];

/*     *     *     *     */

export function getAllIntegrations(): SourceIntegration[] {
  return sourceIntegrations;
}

export function getIntegrationById(id: string): SourceIntegration | undefined {
  return sourceIntegrations.find(integration => integration.id === id);
}

export function getAllContentScriptMatches(): string[] {
  return sourceIntegrations.flatMap(integration => integration.contentScriptMatches);
}
