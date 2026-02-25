#!/usr/bin/env python3
"""Unit tests for the has_open_pr_for_issue function in assign.py."""

import unittest
from unittest.mock import MagicMock, patch

from assign import has_open_pr_for_issue


class TestHasOpenPrForIssue(unittest.TestCase):
    """Tests for has_open_pr_for_issue()."""

    def setUp(self):
        self.owner = "test-owner"
        self.repo = "test-repo"
        self.issue_number = 42
        self.headers = {
            "Authorization": "token fake-token",
            "Accept": "application/vnd.github.v3+json",
        }

    @patch("assign.requests")
    def test_pr_found_via_graphql(self, mock_requests):
        """GraphQL returns an open PR → should return (True, pr_number)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "repository": {
                    "issue": {
                        "timelineItems": {
                            "nodes": [
                                {
                                    "source": {
                                        "number": 99,
                                        "state": "OPEN",
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        mock_requests.post.return_value = mock_response

        result, pr_num = has_open_pr_for_issue(self.owner, self.repo, self.issue_number, self.headers)

        self.assertTrue(result)
        self.assertEqual(pr_num, 99)
        # REST search should NOT be called since GraphQL found it
        mock_requests.get.assert_not_called()

    @patch("assign.requests")
    def test_no_pr_found(self, mock_requests):
        """No PRs exist → should return (False, None)."""
        # GraphQL returns empty nodes
        mock_graphql_response = MagicMock()
        mock_graphql_response.status_code = 200
        mock_graphql_response.json.return_value = {"data": {"repository": {"issue": {"timelineItems": {"nodes": []}}}}}
        mock_requests.post.return_value = mock_graphql_response

        mock_rest_response = MagicMock()
        mock_rest_response.json.return_value = {"total_count": 0, "items": []}
        mock_requests.get.return_value = mock_rest_response

        result, pr_num = has_open_pr_for_issue(self.owner, self.repo, self.issue_number, self.headers)

        self.assertFalse(result)
        self.assertIsNone(pr_num)

    @patch("assign.requests")
    def test_graphql_fails_rest_finds_pr(self, mock_requests):
        """GraphQL raises an exception, REST fallback finds a PR → (True, pr_number)."""
        mock_requests.post.side_effect = Exception("GraphQL connection error")

        # REST finds a PR
        mock_rest_response = MagicMock()
        mock_rest_response.json.return_value = {
            "total_count": 1,
            "items": [{"number": 101}],
        }
        mock_requests.get.return_value = mock_rest_response

        result, pr_num = has_open_pr_for_issue(self.owner, self.repo, self.issue_number, self.headers)

        self.assertTrue(result)
        self.assertEqual(pr_num, 101)

    @patch("assign.requests")
    def test_closed_pr_ignored(self, mock_requests):
        """GraphQL returns a CLOSED PR → should be ignored, return (False, None)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "repository": {
                    "issue": {
                        "timelineItems": {
                            "nodes": [
                                {
                                    "source": {
                                        "number": 50,
                                        "state": "CLOSED",
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        mock_requests.post.return_value = mock_response

        # REST also returns no open PRs
        mock_rest_response = MagicMock()
        mock_rest_response.json.return_value = {"total_count": 0, "items": []}
        mock_requests.get.return_value = mock_rest_response

        result, pr_num = has_open_pr_for_issue(self.owner, self.repo, self.issue_number, self.headers)

        self.assertFalse(result)
        self.assertIsNone(pr_num)

    @patch("assign.requests")
    def test_merged_pr_ignored(self, mock_requests):
        """GraphQL returns a MERGED PR → should be ignored, return (False, None)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "repository": {
                    "issue": {
                        "timelineItems": {
                            "nodes": [
                                {
                                    "source": {
                                        "number": 60,
                                        "state": "MERGED",
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        mock_requests.post.return_value = mock_response

        # REST also returns no open PRs
        mock_rest_response = MagicMock()
        mock_rest_response.json.return_value = {"total_count": 0, "items": []}
        mock_requests.get.return_value = mock_rest_response

        result, pr_num = has_open_pr_for_issue(self.owner, self.repo, self.issue_number, self.headers)

        self.assertFalse(result)
        self.assertIsNone(pr_num)

    @patch("assign.requests")
    def test_both_fail_gracefully(self, mock_requests):
        """Both GraphQL and REST fail → return (False, None) without crashing."""
        mock_requests.post.side_effect = Exception("GraphQL connection error")
        mock_requests.get.side_effect = Exception("REST connection error")

        result, pr_num = has_open_pr_for_issue(self.owner, self.repo, self.issue_number, self.headers)

        self.assertFalse(result)
        self.assertIsNone(pr_num)


if __name__ == "__main__":
    unittest.main()
