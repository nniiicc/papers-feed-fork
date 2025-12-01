#!/usr/bin/env python3
# tests/test_canonical_ids.py
"""
Test canonical ID extraction - run locally to verify deduplication logic.
Production code is in scripts/zotero_sync.py
"""

import re
import hashlib

def extract_arxiv_id(data: dict) -> str | None:
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

def normalize_doi(doi: str) -> str | None:
    # normalize DOI to lowercase, strip prefixes
    if not doi:
        return None
    doi = doi.strip().lower()
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    if doi.startswith('doi:'):
        doi = doi[4:]
    return doi if doi else None

def generate_title_hash(title: str, first_author: str) -> str:
    # fallback ID from title+author hash
    normalized = f"{title.lower().strip()}|{first_author.lower().strip()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

def get_canonical_id(paper_data: dict) -> tuple[str, str]:
    # priority: arxiv > doi > title_hash
    arxiv_id = paper_data.get('arxivId') or extract_arxiv_id(paper_data)
    if arxiv_id:
        return ('arxiv', arxiv_id)
    
    doi = normalize_doi(paper_data.get('doi') or paper_data.get('DOI', ''))
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
        return ('hash', generate_title_hash(title, first_author))
    
    return ('key', paper_data.get('key', 'unknown'))


# Test cases
test_cases = [
    {
        "name": "arxiv paper via URL",
        "data": {
            "title": "Attention Is All You Need",
            "url": "https://arxiv.org/abs/1706.03762",
            "authors": ["Ashish Vaswani", "Noam Shazeer"]
        }
    },
    {
        "name": "arxiv paper via extra field",
        "data": {
            "title": "Attention Is All You Need",
            "extra": "arXiv: 1706.03762 [cs.CL]",
            "authors": ["Ashish Vaswani", "Noam Shazeer"]
        }
    },
    {
        "name": "Paper with DOI only",
        "data": {
            "title": "Some Journal Article",
            "DOI": "10.1234/example.2024.001",
            "authors": [{"firstName": "Jane", "lastName": "Smith"}]
        }
    },
    {
        "name": "Paper with DOI URL",
        "data": {
            "title": "Another Article",
            "doi": "https://doi.org/10.5555/test.123",
            "authors": ["John Doe"]
        }
    },
    {
        "name": "Paper without identifiers (uses hash)",
        "data": {
            "title": "A Paper Without DOI or ArXiv",
            "authors": ["Alice Johnson", "Bob Williams"]
        }
    },
    {
        "name": "Same paper, slightly different title (hash differs!)",
        "data": {
            "title": "A Paper Without DOI or Arxiv",  # lowercase arxiv
            "authors": ["Alice Johnson", "Bob Williams"]
        }
    },
]

if __name__ == '__main__':
    print("Canonical ID Extraction Test\n" + "="*50 + "\n")
    
    for case in test_cases:
        id_type, id_value = get_canonical_id(case['data'])
        canonical = f"{id_type}:{id_value}"
        
        print(f"Test: {case['name']}")
        print(f"  Title: {case['data'].get('title', 'N/A')[:50]}")
        print(f"  Canonical ID: {canonical}")
        print()
    
    print("\n" + "="*50)
    print("Note: The first two arxiv cases produce the SAME canonical ID,")
    print("demonstrating that papers from different sources will match.")
    print("\nThe title-hash cases also match because we normalize to lowercase.")
    print("However, title hashes are still fragile for other variations")
    print("(typos, subtitles, etc.) - this is why DOI/arxiv are preferred.")
