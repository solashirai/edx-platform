"""
Test scenarios for the crowdsource hinter xblock.
"""
import json
import itertools
import StringIO
from ddt import ddt, data
from copy import deepcopy

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase, mixed_store_config

from courseware.tests.helpers import LoginEnrollmentTestCase
from courseware.tests.factories import GlobalStaffFactory

from lms.djangoapps.lms_xblock.runtime import quote_slashes

MODULESTORE_CONFIG = mixed_store_config(settings.COMMON_TEST_DATA_ROOT, {}, include_xml=False)

@override_settings(MODULESTORE=MODULESTORE_CONFIG)
class TestCrowdsourceHinter(ModuleStoreTestCase, LoginEnrollmentTestCase):

    STUDENTS = [
        {'email': 'view@test.com', 'password': 'foo'},
        {'email': 'view2@test.com', 'password': 'foo'}
    ]
    XBLOCK_NAMES = ['crowdsource_hinter']

    def setUp(self):
        self.course = CourseFactory.create(
            display_name='Crowdsource_Hinter_Test_Course'
        )
        self.chapter = ItemFactory.create(
            parent=self.course, display_name='Overview'
        )
        self.section = ItemFactory.create(
            parent=self.chapter, display_name='Welcome'
        )
        self.unit = ItemFactory.create(
            parent=self.section, display_name='New Unit'
        )
        self.xblock = ItemFactory.create(
            parent=self.unit,
            category='crowdsourcehinter',
            display_name='crowdsource_hinter'
        )

        self.course_url = reverse(
            'courseware_section',
            kwargs={
                'course_id': self.course.id.to_deprecated_string(),
                'chapter': 'Overview',
                'section': 'Welcome',
            }
        )

        for idx, student in enumerate(self.STUDENTS):
            username = "u{}".format(idx)
            self.create_account(username, student['email'], student['password'])
            self.activate_user(student['email'])

        self.staff_user = GlobalStaffFactory()

    def get_handler_url(self, handler, xblock_name=None):
        """
        Get url for the specified xblock handler
        """
        if xblock_name is None:
            xblock_name = TestCrowdsourceHinter.XBLOCK_NAMES[0]
        return reverse('xblock_handler', kwargs={
            'course_id': self.course.id.to_deprecated_string(),
            'usage_id': quote_slashes(self.course.id.make_usage_key('crowdsourcehinter', xblock_name).to_deprecated_string()),
            'handler': handler,
            'suffix': ''
        })

    def enroll_student(self, email, password):
        """
        Student login and enroll for the course
        """
        self.login(email, password)
        self.enroll(self.course, verify=True)

    def enroll_staff(self, staff):
        """
        Staff login and enroll for the course
        """
        email = staff.email
        password = 'test'
        self.login(email, password)
        self.enroll(self.course, verify=True)

    def call_event(self, handler, resource, xblock_name=None):
        """
        Call a ajax event (add, edit, flag, etc.) by specifying the resource
        it takes
        """
        if xblock_name is None:
            xblock_name = TestCrowdsourceHinter.XBLOCK_NAMES[0]
        url = self.get_handler_url(handler, xblock_name)
        resp = self.client.post(url, json.dumps(resource), '')
        return json.loads(resp.content)

    def check_event_response_by_element(self, handler, resource, resp_key, resp_val, xblock_name=None):
        """
        Call the event specified by the handler with the resource, and check
        whether the element (resp_key) in response is as expected (resp_val)
        """
        if xblock_name is None:
           xblock_name = TestCrowdsourceHinter.XBLOCK_NAMES[0]
        resp = self.call_event(handler, resource, xblock_name)
        self.assertEqual(resp[resp_key], resp_val)
        self.assert_request_status_code(200, self.course_url)

class TestHinterFunctions(TestCrowdsourceHinter):

    def test_get_hint_with_no_hints(self):
        result = self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        expected = {'BestHint': 'Sorry, there are no hints for this answer.', 'StudentAnswer': 'incorrect answer 1'}
        self.assertEqual(result, expected)

    def test_add_new_hint(self):
        self.enroll_student(self.STUDENTS[0]['email'], self.STUDENTS[0]['password'])
        data = {'submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'}
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        result = self.call_event('add_new_hint', data)

    def test_get_hint(self):
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        self.call_event('add_new_hint', {'submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'})
        result = self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        expected = {'BestHint': 'new hint for answer 1', 'StudentAnswer': 'incorrect answer 1'}
        self.assertEqual(result, expected)

    def test_rate_hint_upvote(self):
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        self.call_event('add_new_hint', {'submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'})
        data = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1',
            'student_rating': 'upvote'
        }
        expected = {'rating': '1', 'hint': 'new hint for answer 1'}
        result = self.call_event('rate_hint', data)
        self.assertEqual(result, expected)

    def test_rate_hint_downvote(self):
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        self.call_event('add_new_hint', {'submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'})
        data = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1',
            'student_rating': 'downvote'
        }
        expected = {'rating': '-1', 'hint': 'new hint for answer 1'}
        result = self.call_event('rate_hint', data)
        self.assertEqual(result, expected)

    def test_report_hint(self):
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        self.call_event('add_new_hint', {'submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'})
        data = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1',
            'student_rating': 'report'
        }
        expected = {'rating': 'reported', 'hint': 'new hint for answer 1'}
        result = self.call_event('rate_hint', data)
        self.assertEqual(result, expected)

    def test_get_used_hint_answer_data(self):
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        self.call_event('get_used_hint_answer_data', "")
        self.call_event('add_new_hint', {'submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'})
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        result = self.call_event('get_used_hint_answer_data', "")
        expected = {'new hint for answer 1': 'incorrect answer 1'}
        self.assertEqual(result, expected)

    def test_dont_show_reported_hint(self):
        self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        self.call_event('add_new_hint', {'submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'})
        self.call_event('add_new_hint', {'submission': 'new hint for answer 1 to report', 'answer': 'incorrect answer 1'})
        data_upvote = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1 to report',
            'student_rating': 'upvote'
        }
        self.call_event('rate_hint', data_upvote)
        data_downvote = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1 to report',
            'student_rating': 'report'
        }
        self.call_event('rate_hint', data_downvote)
        result = self.call_event('get_hint', {'submittedanswer': 'incorrect answer 1'})
        expected = {'BestHint': 'new hint for answer 1', 'StudentAnswer': 'incorrect answer 1'}
        self.assertEqual(expected, result)
