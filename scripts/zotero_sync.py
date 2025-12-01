#!/usr/bin/env python3
# scripts/zotero_sync.py
"""
Syncs Zotero library to papers-feed GitHub issues.
Handles deduplication via canonical IDs (arxiv, DOI, or title hash).
"""

import os
import re
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional
import requests
from loguru import logger

try:
    from pyzotero import zotero
except ImportError:
    logger.error("Install pyzotero: pip install pyzotero")
    raise


class PapersFeedSync:
    def __init__(self):
        self.library_id = os.environ['ZOTERO_LIBRARY_ID']
        self.api_key = os.environ['ZOTERO_API_KEY']
        self.gh_token = os.environ['GITHUB_TOKEN']
        self.repo = os.environ.get('GITHUB_REPOSITORY', '')
        
        self.zot = zotero.Zotero(self.library_id, 'user', self.api_key)
        self.gh_headers = {"Authorization": f"token {self.gh_token}"}
        
        self._issues_cache = None
        self._canonical_map = None
        
        self.version_file = '.zotero_sync_version'

    def get_last_sync_version(self) -> Optional[int]:
        """Get the last synced Zotero library version from repo."""
        url = f"https://api.github.com/repos/{self.repo}/contents/{self.version_file}"
        resp = requests.get(url, headers=self.gh_headers)
        if resp.status_code == 200:
            import base64
            content = base64.b64decode(resp.json()['content']).decode('utf-8')
            try:
                return int(content.strip())
            except ValueError:
                return None
        return None

    def save_sync_version(self, version: int) -> bool:
        """Save the current Zotero library version to repo."""
        import base64
        url = f"https://api.github.com/repos/{self.repo}/contents/{self.version_file}"
        
        resp = requests.get(url, headers=self.gh_headers)
        sha = resp.json().get('sha') if resp.status_code == 200 else None
        
        content = base64.b64encode(str(version).encode()).decode()
        payload = {
            "message": f"Update Zotero sync version to {version}",
            "content": content,
        }
        if sha:
            payload["sha"] = sha
        
        resp = requests.put(url, headers=self.gh_headers, json=payload)
        return resp.status_code in [200, 201]

    def get_current_library_version(self) -> int:
        """Get current Zotero library version."""
        return self.zot.last_modified_version()

    def _extract_arxiv_id(self, data: dict) -> Optional[str]:
        # extract arxiv ID from url or extra field
        url = data.get('url', '') or ''
        
        arxiv_patterns = [
            r'arxiv\.org/abs/(\d{4}\.\d{4,5})',
            r'arxiv\.org/pdf/(\d{4}\.\d{4,5})',
            r'arxiv:(\d{4}\.\d{4,5})',
        ]
        
        for pattern in arxiv_patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1).split('v')[0]
        
        extra = data.get('extra', '') or ''
        match = re.search(r'arXiv[:\s]+(\d{4}\.\d{4,5})', extra, re.IGNORECASE)
        if match:
            return match.group(1).split('v')[0]
        
        return None

    def _normalize_doi(self, doi: str) -> Optional[str]:
        # normalize DOI to lowercase, strip prefixes
        if not doi:
            return None
        doi = doi.strip().lower()
        doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
        if doi.startswith('doi:'):
            doi = doi[4:]
        return doi if doi else None

    def _generate_title_hash(self, title: str, first_author: str) -> str:
        # fallback ID from title+author hash
        normalized = f"{title.lower().strip()}|{first_author.lower().strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _get_canonical_id(self, paper_data: dict) -> tuple[str, str]:
        # priority: arxiv > doi > title_hash
        arxiv_id = paper_data.get('arxivId') or self._extract_arxiv_id(paper_data)
        if arxiv_id:
            return ('arxiv', arxiv_id)
        
        doi = self._normalize_doi(paper_data.get('doi') or paper_data.get('DOI', ''))
        if doi:
            return ('doi', doi)
        
        title = paper_data.get('title', '')
        authors = paper_data.get('authors', [])
        first_author = ''
        if authors:
            if isinstance(authors[0], dict):
                first_author = authors[0].get('lastName', '')
            else:
                first_author = str(authors[0]).split()[-1]
        
        if title:
            return ('hash', self._generate_title_hash(title, first_author))
        
        return ('key', paper_data.get('key', paper_data.get('paperId', 'unknown')))

    def get_existing_issues(self) -> dict:
        # fetch all paper issues, build canonical ID map
        if self._canonical_map is not None:
            return self._canonical_map
        
        url = f"https://api.github.com/repos/{self.repo}/issues"
        params = {"labels": "stored-object", "state": "all", "per_page": 100}
        
        self._issues_cache = []
        self._canonical_map = {}
        
        while url:
            resp = requests.get(url, headers=self.gh_headers, params=params)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch issues: {resp.status_code}")
                break
                
            issues = resp.json()
            for issue in issues:
                self._issues_cache.append(issue)
                
                try:
                    body = json.loads(issue.get('body', '{}'))
                except json.JSONDecodeError:
                    continue
                
                id_type, id_value = self._get_canonical_id(body)
                canonical_key = f"{id_type}:{id_value}"
                
                self._canonical_map[canonical_key] = {
                    'issue_number': issue['number'],
                    'issue_url': issue['html_url'],
                    'source': body.get('sourceId', 'unknown'),
                    'body': body,
                    'labels': [l['name'] for l in issue.get('labels', [])]
                }
            
            url = resp.links.get('next', {}).get('url')
            params = {}

        logger.info(f"Loaded {len(self._canonical_map)} existing papers")
        return self._canonical_map

    def create_issue(self, paper_data: dict, source: str = 'zotero') -> bool:
        # create GitHub issue for paper with labels
        url = f"https://api.github.com/repos/{self.repo}/issues"

        id_type, id_value = self._get_canonical_id(paper_data)
        uid = f"paper:{id_type}.{id_value}"

        labels = [
            f"UID:{uid}",
            "gh-store",
            "stored-object",
            f"source:{source}",
            f"id-type:{id_type}"
        ]

        for tag in paper_data.get('tags', [])[:5]:
            safe_tag = re.sub(r'[^\w\s-]', '', str(tag))[:50]
            if safe_tag:
                labels.append(f"tag:{safe_tag}")

        if paper_data.get('itemType'):
            labels.append(f"type:{paper_data['itemType']}")

        payload = {
            "title": f"Stored Object: {uid}",
            "body": json.dumps(paper_data, indent=2, default=str),
            "labels": labels
        }

        # Retry logic with rate limit handling
        max_retries = 3
        for attempt in range(max_retries):
            resp = requests.post(url, headers=self.gh_headers, json=payload)
            if resp.status_code == 201:
                return True
            elif self._handle_rate_limit(resp):
                continue
            else:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to create issue after {max_retries} attempts: {resp.status_code}")
                return False
        return False

    def update_issue(self, issue_number: int, paper_data: dict,
                     merge_strategy: str = 'enrich') -> bool:
        # update existing issue, merge strategies: enrich | zotero_priority | extension_priority
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}"

        # Retry logic with rate limit handling for GET
        max_retries = 3
        for attempt in range(max_retries):
            resp = requests.get(url, headers=self.gh_headers)
            if resp.status_code == 200:
                break
            elif self._handle_rate_limit(resp):
                continue
            else:
                logger.error(f"Failed to fetch issue {issue_number}: {resp.status_code}")
                return False

        if resp.status_code != 200:
            return False

        issue = resp.json()
        try:
            existing_data = json.loads(issue.get('body', '{}'))
        except json.JSONDecodeError:
            existing_data = {}

        if merge_strategy == 'enrich':
            merged = {**paper_data, **existing_data}
            for key, value in paper_data.items():
                if not existing_data.get(key):
                    merged[key] = value
        elif merge_strategy == 'zotero_priority':
            merged = {**existing_data, **paper_data}
        else:
            merged = {**paper_data, **existing_data}

        merged['sources'] = list(set(
            existing_data.get('sources', [existing_data.get('sourceId', 'unknown')]) +
            [paper_data.get('sourceId', 'zotero')]
        ))
        merged['lastUpdated'] = datetime.now().isoformat()

        existing_labels = [l['name'] for l in issue.get('labels', [])]
        new_source_label = f"source:{paper_data.get('sourceId', 'zotero')}"
        if new_source_label not in existing_labels:
            existing_labels.append(new_source_label)

        payload = {
            "body": json.dumps(merged, indent=2, default=str),
            "labels": existing_labels
        }

        # Retry logic with rate limit handling for PATCH
        for attempt in range(max_retries):
            resp = requests.patch(url, headers=self.gh_headers, json=payload)
            if resp.status_code == 200:
                return True
            elif self._handle_rate_limit(resp):
                continue
            else:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to update issue {issue_number} after {max_retries} attempts: {resp.status_code}")
                return False
        return False

    def transform_zotero_item(self, item: dict) -> dict:
        # transform Zotero item to papers-feed format
        data = item['data']
        
        authors = []
        for creator in data.get('creators', []):
            if creator.get('creatorType') in ['author', 'contributor']:
                name = f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
                if name:
                    authors.append(name)
        
        arxiv_id = self._extract_arxiv_id(data)
        
        return {
            "sourceId": "zotero",
            "paperId": data['key'],
            "key": data['key'],
            "itemType": data.get('itemType'),
            "title": data.get('title', ''),
            "authors": authors,
            "url": data.get('url', ''),
            "doi": data.get('DOI', ''),
            "arxivId": arxiv_id,
            "dateAdded": data.get('dateAdded'),
            "dateModified": data.get('dateModified'),
            "publicationTitle": data.get('publicationTitle', ''),
            "conferenceName": data.get('conferenceName', ''),
            "proceedingsTitle": data.get('proceedingsTitle', ''),
            "abstractNote": (data.get('abstractNote', '') or '')[:1000],
            "tags": [t['tag'] for t in data.get('tags', [])],
            "collections": data.get('collections', []),
            "extra": data.get('extra', ''),
            "zoteroLink": f"zotero://select/items/{data['key']}"
        }

    def sync_zotero_items(self,
                          days: int = 14,
                          collection_name: Optional[str] = None,
                          update_existing: bool = True) -> dict:
        # sync Zotero items from last N days
        existing = self.get_existing_issues()
        
        if collection_name:
            collections = self.zot.collections()
            target = next(
                (c for c in collections if c['data']['name'] == collection_name),
                None
            )
            if not target:
                logger.error(f"Collection '{collection_name}' not found")
                return {"error": "collection not found"}
            items = self.zot.collection_items(target['key'])
        else:
            items = self.zot.everything(
                self.zot.items(
                    sort='dateModified',
                    direction='desc',
                    itemType='-attachment -note -annotation'
                )
            )
        
        cutoff = datetime.now() - timedelta(days=days)
        
        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        for item in items:
            data = item['data']
            
            if data.get('itemType') in ['attachment', 'note', 'annotation']:
                continue
            
            try:
                modified = datetime.fromisoformat(
                    data['dateModified'].replace('Z', '+00:00')
                ).replace(tzinfo=None)
                if modified < cutoff:
                    stats['skipped'] += 1
                    continue
            except (KeyError, ValueError):
                pass
            
            paper_data = self.transform_zotero_item(item)
            id_type, id_value = self._get_canonical_id(paper_data)
            canonical_key = f"{id_type}:{id_value}"
            
            if canonical_key in existing:
                if update_existing:
                    existing_info = existing[canonical_key]
                    if 'zotero' not in existing_info['source']:
                        if self.update_issue(existing_info['issue_number'], paper_data):
                            stats['updated'] += 1
                            logger.success(f"Updated: {paper_data['title'][:50]}...")
                        else:
                            stats['errors'] += 1
                    else:
                        stats['skipped'] += 1
                else:
                    stats['skipped'] += 1
            else:
                if self.create_issue(paper_data, source='zotero'):
                    stats['created'] += 1
                    logger.success(f"Created: {paper_data['title'][:50]}...")
                    existing[canonical_key] = {'source': 'zotero'}
                else:
                    stats['errors'] += 1

        return stats

    def get_collection_names(self) -> list[str]:
        collections = self.zot.collections()
        return [c['data']['name'] for c in collections]

    def _handle_rate_limit(self, resp: requests.Response) -> bool:
        # handle GitHub API rate limits with retry
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return True
        elif resp.status_code == 403 and 'rate limit' in resp.text.lower():
            logger.warning("Rate limit detected. Waiting 60 seconds...")
            time.sleep(60)
            return True
        return False

    def sync_incremental(self,
                         collection_name: Optional[str] = None,
                         update_existing: bool = True,
                         initialize: bool = False) -> dict:
        # incremental sync - only items changed since last sync
        current_version = self.get_current_library_version()
        last_version = self.get_last_sync_version()

        if initialize:
            logger.info(f"Initializing sync marker at library version {current_version}")
            logger.info("No historical items will be synced.")
            self.save_sync_version(current_version)
            return {"initialized": True, "version": current_version}

        if last_version is None:
            logger.warning("No previous sync found. Run with --init to start fresh,")
            logger.warning("or use --days N to do an initial historical sync.")
            return {"error": "no_previous_sync"}

        if last_version >= current_version:
            logger.info(f"Already up to date (version {current_version})")
            return {"up_to_date": True, "version": current_version}

        logger.info(f"Syncing changes: version {last_version} → {current_version}")
        
        existing = self.get_existing_issues()
        
        items = self.zot.items(since=last_version, itemType='-attachment -note -annotation')
        
        if collection_name:
            collections = self.zot.collections()
            target = next(
                (c for c in collections if c['data']['name'] == collection_name),
                None
            )
            if target:
                collection_key = target['key']
                items = [i for i in items if collection_key in i['data'].get('collections', [])]
        
        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        for item in items:
            data = item['data']
            
            if data.get('itemType') in ['attachment', 'note', 'annotation']:
                continue
            
            paper_data = self.transform_zotero_item(item)
            id_type, id_value = self._get_canonical_id(paper_data)
            canonical_key = f"{id_type}:{id_value}"
            
            if canonical_key in existing:
                if update_existing:
                    existing_info = existing[canonical_key]
                    if self.update_issue(existing_info['issue_number'], paper_data):
                        stats['updated'] += 1
                        logger.success(f"Updated: {paper_data['title'][:50]}...")
                    else:
                        stats['errors'] += 1
                else:
                    stats['skipped'] += 1
            else:
                if self.create_issue(paper_data, source='zotero'):
                    stats['created'] += 1
                    logger.success(f"Created: {paper_data['title'][:50]}...")
                    existing[canonical_key] = {'source': 'zotero'}
                else:
                    stats['errors'] += 1

        self.save_sync_version(current_version)
        stats['version'] = current_version
        
        return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync Zotero to papers-feed')
    parser.add_argument('--days', type=int, default=None,
                        help='Sync items modified in last N days (historical mode)')
    parser.add_argument('--collection', type=str, default=None,
                        help='Only sync from this collection')
    parser.add_argument('--no-update', action='store_true',
                        help='Do not update existing items')
    parser.add_argument('--list-collections', action='store_true',
                        help='List available collections and exit')
    parser.add_argument('--incremental', action='store_true',
                        help='Only sync items changed since last sync')
    parser.add_argument('--init', action='store_true',
                        help='Initialize sync marker at current version (no historical sync)')
    
    args = parser.parse_args()
    
    syncer = PapersFeedSync()

    if args.list_collections:
        logger.info("Available collections:")
        for name in syncer.get_collection_names():
            logger.info(f"  - {name}")
        return

    if args.init:
        logger.info("Initializing Zotero sync from current point...")
        stats = syncer.sync_incremental(initialize=True)
        logger.info(f"Sync marker set to version {stats.get('version')}")
        logger.info("Future syncs with --incremental will only capture new items.")
        return

    if args.incremental:
        logger.info("Running incremental sync...")
        if args.collection:
            logger.info(f"Filtering to collection: {args.collection}")
        
        stats = syncer.sync_incremental(
            collection_name=args.collection,
            update_existing=not args.no_update
        )

        if stats.get('error'):
            logger.error(f"Error: {stats['error']}")
            logger.info("Run with --init to start syncing from now, or")
            logger.info("use --days N for initial historical sync.")
            return

        if stats.get('initialized'):
            return

        if stats.get('up_to_date'):
            logger.info("No new items to sync.")
            return
    else:
        days = args.days if args.days is not None else 14
        logger.info(f"Syncing Zotero items from last {days} days...")
        if args.collection:
            logger.info(f"Filtering to collection: {args.collection}")
        
        stats = syncer.sync_zotero_items(
            days=days,
            collection_name=args.collection,
            update_existing=not args.no_update
        )

    logger.info("Sync complete:")
    logger.info(f"  Created: {stats.get('created', 0)}")
    logger.info(f"  Updated: {stats.get('updated', 0)}")
    logger.info(f"  Skipped: {stats.get('skipped', 0)}")
    logger.info(f"  Errors:  {stats.get('errors', 0)}")
    if stats.get('version'):
        logger.info(f"  Version: {stats['version']}")


if __name__ == '__main__':
    main()
