import unittest
from unittest.mock import patch

import pandas as pd

from utilities import find_pr_files as find_pr_files_module


class FindPrFilesAuthTests(unittest.TestCase):
    def test_find_pr_files_uses_gh_auth_for_pull_listing(self):
        sample_snippets = pd.DataFrame([
            {
                "ref_file": "articles/foo.md",
                "from_file_dir": "articles",
                "from_file": "foo.md",
            }
        ])

        def fake_get_auth_response(url):
            if url.endswith("/pulls?state=closed&sort=updated&direction=desc"):
                return [
                    {"number": 123, "merged_at": "2099-01-01T00:00:00Z"}
                ]
            if url.endswith("/pulls/123/files?per_page=100"):
                return [{"filename": "articles/foo.md", "status": "modified"}]
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("requests.get", side_effect=AssertionError("requests.get should not be used for authenticated repo lookups")):
            with patch("utilities.gh_auth.get_auth_response", side_effect=fake_get_auth_response) as mock_get_auth_response:
                results = find_pr_files_module.find_pr_files("microsoft-foundry", "foundry-samples-pr", sample_snippets, 30)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["repo"], "foundry-samples-pr")
        self.assertEqual(results[0]["owner"], "microsoft-foundry")
        self.assertEqual(results[0]["PR"], 123)
        self.assertEqual(results[0]["Referenced In"], ["articles/foo.md"])
        self.assertGreaterEqual(mock_get_auth_response.call_count, 2)


if __name__ == "__main__":
    unittest.main()
