

# -*- coding: utf-8 -*-
from bok_choy.page_object import PageObject


class GitHubSearchPage(PageObject):
    """
    GitHub's search page
    """

    url = 'http://localhost:8000/courses/edX/DemoX/Demo_Course/courseware/Introduction/Subsection/'

    def is_browser_on_page(self):

        self.browser.find_element_by_id('email').send_keys('staff@example.com')
        self.browser.find_element_by_id('password').send_keys('edx')
        self.browser.find_element_by_id('submit').click()

        self.browser.implicitly_wait(30)

        return len(self.browser.find_elements_by_class_name('crowdsourcehinter_block')) > 0
