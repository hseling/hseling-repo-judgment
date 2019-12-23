import unittest

import hseling_api_judgment


class HSELing_API_JudgmentTestCase(unittest.TestCase):

    def setUp(self):
        self.app = hseling_api_judgment.app.test_client()

    def test_index(self):
        rv = self.app.get('/healthz')
        self.assertIn('Application Judgment', rv.data.decode())


if __name__ == '__main__':
    unittest.main()
