"""
This test file will run through some XBlock test scenarios regarding the
recommender system
"""

import json
import itertools
import StringIO
from ddt import ddt, data
from copy import deepcopy

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from courseware.tests.helpers import LoginEnrollmentTestCase
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
from courseware.tests.factories import GlobalStaffFactory

from lms.lib.xblock.runtime import quote_slashes


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestHinter(ModuleStoreTestCase, LoginEnrollmentTestCase):
    """
    Check that Recommender state is saved properly.
    """
    STUDENT_INFO = [('view@test.com', 'foo'), ('view2@test.com', 'foo'), ('view3@test.com', 'foo')]

    def setUp(self):
        self.course = CourseFactory.create(
            display_name='Hinter_Test_Course'
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
            category='crowdxblock',
            display_name='crowdxblock'
        )
        self.xblock2 = ItemFactory.create(
            parent=self.unit,
            category='crowdxblock',
            display_name='crowdxblock_second'
        )

        self.xblock_names = ['crowdxblock', 'crowdxblock_second']

        self.course_url = reverse(
            'courseware_section',
            kwargs={
                'course_id': self.course.id.to_deprecated_string(),
                'chapter': 'Overview',
                'section': 'Welcome',
            }
        )

        # Create student accounts and activate them.
        for i, (email, password) in enumerate(self.STUDENT_INFO):
            username = "u{}".format(i)
            self.create_account(username, email, password)
            self.activate_user(email)

        self.staff_user = GlobalStaffFactory()

    def get_handler_url(self, handler, xblock_name='crowdxblock'):
        """
        Get url for the specified xblock handler
        """
        return reverse('xblock_handler', kwargs={
            'course_id': self.course.id.to_deprecated_string(),
            'usage_id': quote_slashes(self.course.id.make_usage_key('crowdxblock', xblock_name).to_deprecated_string()),
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

    def call_event(self, handler, event_data, xblock_name='crowdxblock'):
        """
        Call a ajax event (edit, flag) on a resource by providing data
        """
        url = self.get_handler_url(handler, xblock_name)
        resp = self.client.post(url, json.dumps(event_data), '')
        return json.loads(resp.content)

class Test_Hinter_Functions(TestHinter):

    def test_get_hint(self):
        '''
        This tests the hinter's "get_hint" function. the hint "hint" is already in the hinter for
        testing purposes, and the answer "answer" is used to test the hint.

        This test should be updated once I figure out how to directly add hints/answers to hint_database
        TODO once updated: ensure that student isn't shown flagged hints
        '''
        self.logout()
        self.enroll_student(self.STUDENT_INFO[0][0], self.STUDENT_INFO[0][1])
        resp = self.call_event(
            'get_hint', {
                'submittedanswer': 'answer'
            }
        )
        # call get_hint again to make sure the same hint isn't returned
        resp2 = self.call_event(
            'get_hint', {
                'submittedanswer': 'answer'
            }
        )
        self.assertEqual(resp['HintsToUse'], 'hint')
        self.assertNotEqual(resp2['HintsToUse'], 'hint')

    def test_feedback(self):
        '''
        This tests the feedback stage of the hinter. 
        Once I figure out how to add hints/answers directly:
            set up multiple hints/answers, set up Used
            check that each answer returns multiple hints
        '''
        self.assertEqual(1,1)

    def test_hint_submission(self):
        '''
        This tests the hinter's functions that store student-submitted hints, as well as
        check that students are provided the newly added hints.

        This test currently runs on the assumption that test_get_hint runs without error.
        This test should be updated to directly check the hint_database.
        '''
        self.logout()
        self.enroll_student(self.STUDENT_INFO[0][0], self.STUDENT_INFO[0][1])
        resp = self.call_event(
            'give_hint', {
                'submission': 'new_hint',
                'answer': 'answer'
            }
        )
        # get_hint for a new incorrect answer, to add into the hint_database
        resp2 = self.call_event(
            'get_hint', {
                'submittedanswer': 'new_answer'
            }
        )
        resp3 = self.call_event(
            'give_hint', {
                'submission': 'hint_for_new_answer',
                'answer': 'new_answer'
            }
        )
        # check that other students recieve these hints
        self.logout()
        self.enroll_student(self.STUDENT_INFO[1][0], self.STUDENT_INFO[1][1])
        resp4 = self.call_event(
            'get_hint', {
                'submittedanswer': 'answer'
            }
        )
        resp5 = self.call_event(
            'get_hint', {
                'submittedanswer': 'answer'
            }
        )
        resp6 = self.call_event(
            'get_hint', {
                'submittedanswer': 'new_answer'
            }
        )
        self.assertEqual(resp4['HintsToUse'], 'hint')
        self.assertEqual(resp5['HintsToUse'], 'new_hint')
        self.assertEqual(resp6['HintsToUse'], 'hint_for_new_answer')

    def test_rate_hint(self):
        """
        Tests student hint rating in the hinter. 
        Checks: upvote works, upvoting twice doesn't work, other students
        can see the change in rating, flagging works

        This test should be updated after learning how to properly set variables (such
        as hint_database's hints) to the hinter via this test
        """
        self.enroll_student(self.STUDENT_INFO[0][0], self.STUDENT_INFO[0][1])
        resp = self.call_event(
            'rate_hint', {
                'student_rating': 1,
                'value': 'hint',
                'answer': 'answer'
            }
        )
        resp2 = self.call_event(
            'rate_hint', {
                'student_rating': 1,
                'value': 'hint',
                'answer': 'answer'
            }
        )
        self.logout()
        self.enroll_student(self.STUDENT_INFO[1][0], self.STUDENT_INFO[1][1])
        resp3 = self.call_event(
            'rate_hint', {
                'student_rating': 1,
                'value': 'hint',
                'answer': 'answer'
            }
        )
        self.logout()
        self.enroll_student(self.STUDENT_INFO[2][0], self.STUDENT_INFO[2][1])
        resp4 = self.call_event(
            'rate_hint', {
                'student_rating': 0,
                'value': 'hint',
                'answer': 'answer'
            }
        )
        self.assertEqual(resp3['rating'], '7')
        self.assertEqual(resp['origdata'], 'answer')
        self.assertEqual(resp['rating'], '6')
        self.assertEqual(resp2['rating'], 'You have already voted on this hint!')
        self.assertEqual(resp4['rating'], 'thiswasflagged')
