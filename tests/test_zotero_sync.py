#!/usr/bin/env python3
# tests/test_zotero_sync.py
"""
Unit tests for Zotero sync. Run with: pytest tests/test_zotero_sync.py
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path to import zotero_sync
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from unittest.mock import Mock, patch, MagicMock


class TestCanonicalID:
    # test canonical ID extraction and normalization

    def setup_method(self):
        # mock PapersFeedSync without real credentials
        with patch.dict('os.environ', {
            'ZOTERO_LIBRARY_ID': 'test_lib',
            'ZOTERO_API_KEY': 'test_key',
            'GITHUB_TOKEN': 'test_token',
            'GITHUB_REPOSITORY': 'test/repo'
        }):
            from zotero_sync import PapersFeedSync
            self.syncer = PapersFeedSync()

    def test_extract_arxiv_id_from_url(self):
        data = {"url": "https://arxiv.org/abs/1706.03762"}
        arxiv_id = self.syncer._extract_arxiv_id(data)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_from_pdf_url(self):
        data = {"url": "https://arxiv.org/pdf/2024.12345.pdf"}
        arxiv_id = self.syncer._extract_arxiv_id(data)
        assert arxiv_id == "2024.12345"

    def test_extract_arxiv_id_from_extra_field(self):
        data = {
            "url": "",
            "extra": "arXiv: 1706.03762 [cs.CL]"
        }
        arxiv_id = self.syncer._extract_arxiv_id(data)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_strips_version(self):
        data = {"url": "https://arxiv.org/abs/1706.03762v2"}
        arxiv_id = self.syncer._extract_arxiv_id(data)
        assert arxiv_id == "1706.03762"

    def test_normalize_doi_from_url(self):
        doi = self.syncer._normalize_doi("https://doi.org/10.1234/example.2024.001")
        assert doi == "10.1234/example.2024.001"

    def test_normalize_doi_from_dx_url(self):
        doi = self.syncer._normalize_doi("https://dx.doi.org/10.1234/example")
        assert doi == "10.1234/example"

    def test_normalize_doi_with_prefix(self):
        doi = self.syncer._normalize_doi("doi:10.1234/example")
        assert doi == "10.1234/example"

    def test_normalize_doi_lowercase(self):
        doi = self.syncer._normalize_doi("10.1234/EXAMPLE")
        assert doi == "10.1234/example"

    def test_generate_title_hash_consistent(self):
        hash1 = self.syncer._generate_title_hash("Test Paper", "Smith")
        hash2 = self.syncer._generate_title_hash("Test Paper", "Smith")
        assert hash1 == hash2
        assert len(hash1) == 16  # Should be 16 hex characters

    def test_generate_title_hash_case_insensitive(self):
        hash1 = self.syncer._generate_title_hash("Test Paper", "Smith")
        hash2 = self.syncer._generate_title_hash("test paper", "smith")
        assert hash1 == hash2

    def test_get_canonical_id_prefers_arxiv(self):
        paper_data = {
            "arxivId": "1706.03762",
            "doi": "10.1234/example",
            "title": "Test Paper",
            "authors": ["Smith"]
        }
        id_type, id_value = self.syncer._get_canonical_id(paper_data)
        assert id_type == "arxiv"
        assert id_value == "1706.03762"

    def test_get_canonical_id_uses_doi_if_no_arxiv(self):
        paper_data = {
            "doi": "10.1234/example",
            "title": "Test Paper",
            "authors": ["Smith"]
        }
        id_type, id_value = self.syncer._get_canonical_id(paper_data)
        assert id_type == "doi"
        assert id_value == "10.1234/example"

    def test_get_canonical_id_falls_back_to_hash(self):
        paper_data = {
            "title": "Test Paper Without IDs",
            "authors": [{"firstName": "John", "lastName": "Smith"}]
        }
        id_type, id_value = self.syncer._get_canonical_id(paper_data)
        assert id_type == "hash"
        assert len(id_value) == 16

    def test_get_canonical_id_handles_author_formats(self):
        # Test with dict format
        paper1 = {
            "title": "Test",
            "authors": [{"firstName": "John", "lastName": "Doe"}]
        }
        id_type1, id_value1 = self.syncer._get_canonical_id(paper1)

        # Test with string format
        paper2 = {
            "title": "Test",
            "authors": ["John Doe"]
        }
        id_type2, id_value2 = self.syncer._get_canonical_id(paper2)

        assert id_type1 == "hash"
        assert id_type2 == "hash"
        assert id_value1 == id_value2  # Should produce same hash


class TestZoteroTransform:
    # test Zotero item transformation

    def setup_method(self):
        with patch.dict('os.environ', {
            'ZOTERO_LIBRARY_ID': 'test_lib',
            'ZOTERO_API_KEY': 'test_key',
            'GITHUB_TOKEN': 'test_token',
            'GITHUB_REPOSITORY': 'test/repo'
        }):
            from zotero_sync import PapersFeedSync
            self.syncer = PapersFeedSync()

    def test_transform_basic_item(self):
        zotero_item = {
            'data': {
                'key': 'ABC123',
                'itemType': 'journalArticle',
                'title': 'Test Paper',
                'creators': [
                    {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Doe'}
                ],
                'url': 'https://example.com/paper',
                'DOI': '10.1234/test',
                'dateAdded': '2024-01-01T00:00:00Z',
                'dateModified': '2024-01-02T00:00:00Z',
                'abstractNote': 'This is a test abstract.',
                'tags': [{'tag': 'machine learning'}, {'tag': 'AI'}],
                'collections': ['collection1'],
                'extra': ''
            }
        }

        result = self.syncer.transform_zotero_item(zotero_item)

        assert result['sourceId'] == 'zotero'
        assert result['paperId'] == 'ABC123'
        assert result['title'] == 'Test Paper'
        assert result['authors'] == ['John Doe']
        assert result['doi'] == '10.1234/test'
        assert result['itemType'] == 'journalArticle'
        assert result['tags'] == ['machine learning', 'AI']
        assert 'zoteroLink' in result

    def test_transform_with_arxiv(self):
        zotero_item = {
            'data': {
                'key': 'ABC123',
                'itemType': 'preprint',
                'title': 'arXiv Paper',
                'creators': [{'creatorType': 'author', 'firstName': 'Jane', 'lastName': 'Smith'}],
                'url': 'https://arxiv.org/abs/2024.12345',
                'DOI': '',
                'dateAdded': '2024-01-01T00:00:00Z',
                'dateModified': '2024-01-02T00:00:00Z',
                'abstractNote': 'Test abstract',
                'tags': [],
                'collections': [],
                'extra': ''
            }
        }

        result = self.syncer.transform_zotero_item(zotero_item)

        assert result['arxivId'] == '2024.12345'
        assert result['url'] == 'https://arxiv.org/abs/2024.12345'

    def test_transform_truncates_long_abstract(self):
        long_abstract = 'x' * 2000
        zotero_item = {
            'data': {
                'key': 'ABC123',
                'itemType': 'journalArticle',
                'title': 'Paper with Long Abstract',
                'creators': [],
                'url': '',
                'DOI': '',
                'dateAdded': '2024-01-01T00:00:00Z',
                'dateModified': '2024-01-02T00:00:00Z',
                'abstractNote': long_abstract,
                'tags': [],
                'collections': [],
                'extra': ''
            }
        }

        result = self.syncer.transform_zotero_item(zotero_item)

        assert len(result['abstractNote']) == 1000


class TestRateLimitHandling:
    # test rate limit handling

    def setup_method(self):
        with patch.dict('os.environ', {
            'ZOTERO_LIBRARY_ID': 'test_lib',
            'ZOTERO_API_KEY': 'test_key',
            'GITHUB_TOKEN': 'test_token',
            'GITHUB_REPOSITORY': 'test/repo'
        }):
            from zotero_sync import PapersFeedSync
            self.syncer = PapersFeedSync()

    @patch('time.sleep')
    def test_handle_rate_limit_429(self, mock_sleep):
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '30'}

        should_retry = self.syncer._handle_rate_limit(mock_response)

        assert should_retry is True
        mock_sleep.assert_called_once_with(30)

    @patch('time.sleep')
    def test_handle_rate_limit_403(self, mock_sleep):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = 'rate limit exceeded'

        should_retry = self.syncer._handle_rate_limit(mock_response)

        assert should_retry is True
        mock_sleep.assert_called_once_with(60)

    def test_handle_rate_limit_other_errors(self):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'not found'

        should_retry = self.syncer._handle_rate_limit(mock_response)

        assert should_retry is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
