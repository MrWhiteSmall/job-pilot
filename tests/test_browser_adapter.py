"""Checks that browser uncertainty cannot turn into a false success."""
import unittest
from unittest.mock import Mock

from browser_adapter import BossBrowser


class BrowserSafetyTests(unittest.TestCase):
    def make_browser(self, page):
        browser = object.__new__(BossBrowser)
        context = Mock()
        context.new_page.return_value = page
        browser._context = Mock(return_value=context)
        browser._check = Mock(return_value='AI应用开发工程师 任职要求 Python')
        return browser

    def test_foreign_url_is_never_opened(self):
        browser = object.__new__(BossBrowser)
        browser._context = Mock(side_effect=AssertionError('must not open browser'))
        for url in ['https://evil.example/job_detail/abc.html',
                    'https://www.zhipin.com.evil.example/job_detail/abc.html',
                    'http://www.zhipin.com/job_detail/abc.html']:
            self.assertEqual(browser._submit({'url': url}, '')['status'], 'blocked')
        browser._context.assert_not_called()

    def test_existing_contact_is_not_clicked_again(self):
        page = Mock()
        page.get_by_text.return_value.count.return_value = 1
        browser = self.make_browser(page)
        result = browser._submit({'url': 'https://www.zhipin.com/job_detail/abc.html', 'title': 'AI应用开发工程师'}, '')
        self.assertEqual(result['status'], 'blocked')
        page.get_by_role.assert_not_called()

    def test_changed_company_or_salary_blocks_contact(self):
        for changed in [{'company': '另一家公司'}, {'salary': '20-30K'}]:
            page = Mock()
            browser = self.make_browser(page)
            job = {'url': 'https://www.zhipin.com/job_detail/abc.html', 'title': 'AI应用开发工程师', **changed}
            self.assertEqual(browser._submit(job, '')['status'], 'blocked')
            page.get_by_role.assert_not_called()

    def test_click_timeout_is_uncertain_not_failed_or_sent(self):
        page = Mock()
        page.get_by_text.return_value.count.return_value = 0
        button = page.get_by_role.return_value
        button.count.return_value = 1
        button.is_visible.return_value = True
        button.click.side_effect = TimeoutError('click result unknown')
        browser = self.make_browser(page)
        result = browser._submit({'url': 'https://www.zhipin.com/job_detail/abc.html', 'title': 'AI应用开发工程师'}, '')
        self.assertEqual(result['status'], 'uncertain')
        button.click.assert_called_once()
        page.close.assert_not_called()  # Keep the page for manual inspection.


if __name__ == '__main__':
    unittest.main()
