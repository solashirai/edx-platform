import json
import logging

from django.http import Http404
from django.test.utils import override_settings
from django.test.client import Client, RequestFactory
from xmodule.modulestore.tests.factories import CourseFactory
from student.tests.factories import UserFactory, CourseEnrollmentFactory
from edxmako.tests import mako_middleware_process_request
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from django.core.urlresolvers import reverse
from util.testing import UrlResetMixin
from django_comment_client.tests.unicode import UnicodeTestMixin
from django_comment_client.tests.utils import CohortedContentTestCase
from django_comment_client.forum import views

from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
from nose.tools import assert_true  # pylint: disable=E0611
from mock import patch, Mock, ANY, call

from course_groups.models import CourseUserGroup

log = logging.getLogger(__name__)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class ViewsExceptionTestCase(UrlResetMixin, ModuleStoreTestCase):

    @patch.dict("django.conf.settings.FEATURES", {"ENABLE_DISCUSSION_SERVICE": True})
    def setUp(self):

        # Patching the ENABLE_DISCUSSION_SERVICE value affects the contents of urls.py,
        # so we need to call super.setUp() which reloads urls.py (because
        # of the UrlResetMixin)
        super(ViewsExceptionTestCase, self).setUp()

        # create a course
        self.course = CourseFactory.create(org='MITx', course='999',
                                           display_name='Robot Super Course')

        # Patch the comment client user save method so it does not try
        # to create a new cc user when creating a django user
        with patch('student.models.cc.User.save'):
            uname = 'student'
            email = 'student@edx.org'
            password = 'test'

            # Create the student
            self.student = UserFactory(username=uname, password=password, email=email)

            # Enroll the student in the course
            CourseEnrollmentFactory(user=self.student, course_id=self.course.id)

            # Log the student in
            self.client = Client()
            assert_true(self.client.login(username=uname, password=password))

    @patch('student.models.cc.User.from_django_user')
    @patch('student.models.cc.User.active_threads')
    def test_user_profile_exception(self, mock_threads, mock_from_django_user):

        # Mock the code that makes the HTTP requests to the cs_comment_service app
        # for the profiled user's active threads
        mock_threads.return_value = [], 1, 1

        # Mock the code that makes the HTTP request to the cs_comment_service app
        # that gets the current user's info
        mock_from_django_user.return_value = Mock()

        url = reverse('django_comment_client.forum.views.user_profile',
                      kwargs={'course_id': self.course.id.to_deprecated_string(), 'user_id': '12345'})  # There is no user 12345
        self.response = self.client.get(url)
        self.assertEqual(self.response.status_code, 404)

    @patch('student.models.cc.User.from_django_user')
    @patch('student.models.cc.User.subscribed_threads')
    def test_user_followed_threads_exception(self, mock_threads, mock_from_django_user):

        # Mock the code that makes the HTTP requests to the cs_comment_service app
        # for the profiled user's active threads
        mock_threads.return_value = [], 1, 1

        # Mock the code that makes the HTTP request to the cs_comment_service app
        # that gets the current user's info
        mock_from_django_user.return_value = Mock()

        url = reverse('django_comment_client.forum.views.followed_threads',
                      kwargs={'course_id': self.course.id.to_deprecated_string(), 'user_id': '12345'})  # There is no user 12345
        self.response = self.client.get(url)
        self.assertEqual(self.response.status_code, 404)


def make_mock_thread_data(text, thread_id, include_children, group_id=None, group_name=None):
    thread_data = {
        "id": thread_id,
        "type": "thread",
        "title": text,
        "body": text,
        "commentable_id": "dummy_commentable_id",
        "resp_total": 42,
        "resp_skip": 25,
        "resp_limit": 5,
    }
    if group_id is not None:
        thread_data['group_id'] = group_id
        thread_data['group_name'] = group_name
    if include_children:
        thread_data["children"] = [{
            "id": "dummy_comment_id",
            "type": "comment",
            "body": text,
        }]
    return thread_data


def make_mock_request_impl(text, thread_id="dummy_thread_id", group_id=None):
    def mock_request_impl(*args, **kwargs):
        url = args[1]
        data = None
        if url.endswith("threads"):
            data = {
                "collection": [make_mock_thread_data(text, thread_id, False, group_id=group_id)]
            }
        elif thread_id and url.endswith(thread_id):
            data = make_mock_thread_data(text, thread_id, True, group_id=group_id)
        elif "/users/" in url:
            data = {
                "default_sort_key": "date",
                "upvoted_ids": [],
                "downvoted_ids": [],
                "subscribed_thread_ids": [],
            }
            # comments service adds these attributes when course_id param is present
            if kwargs.get('params', {}).get('course_id'):
                data.update({
                    "threads_count": 1,
                    "comments_count": 2
                })
        if data:
            return Mock(status_code=200, text=json.dumps(data), json=Mock(return_value=data))
        return Mock(status_code=404)
    return mock_request_impl


class StringEndsWithMatcher(object):
    def __init__(self, suffix):
        self.suffix = suffix

    def __eq__(self, other):
        return other.endswith(self.suffix)


class PartialDictMatcher(object):
    def __init__(self, expected_values):
        self.expected_values = expected_values

    def __eq__(self, other):
        return all([
            key in other and other[key] == value
            for key, value in self.expected_values.iteritems()
        ])


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
@patch('requests.request')
class SingleThreadTestCase(ModuleStoreTestCase):
    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory.create(user=self.student, course_id=self.course.id)

    def test_ajax(self, mock_request):
        text = "dummy content"
        thread_id = "test_thread_id"
        mock_request.side_effect = make_mock_request_impl(text, thread_id)

        request = RequestFactory().get(
            "dummy_url",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        request.user = self.student
        response = views.single_thread(
            request,
            self.course.id.to_deprecated_string(),
            "dummy_discussion_id",
            "test_thread_id"
        )

        self.assertEquals(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEquals(
            response_data["content"],
            make_mock_thread_data(text, thread_id, True)
        )
        mock_request.assert_called_with(
            "get",
            StringEndsWithMatcher(thread_id), # url
            data=None,
            params=PartialDictMatcher({"mark_as_read": True, "user_id": 1, "recursive": True}),
            headers=ANY,
            timeout=ANY
        )

    def test_skip_limit(self, mock_request):
        text = "dummy content"
        thread_id = "test_thread_id"
        response_skip = "45"
        response_limit = "15"
        mock_request.side_effect = make_mock_request_impl(text, thread_id)

        request = RequestFactory().get(
            "dummy_url",
            {"resp_skip": response_skip, "resp_limit": response_limit},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        request.user = self.student
        response = views.single_thread(
            request,
            self.course.id.to_deprecated_string(),
            "dummy_discussion_id",
            "test_thread_id"
        )
        self.assertEquals(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEquals(
            response_data["content"],
            make_mock_thread_data(text, thread_id, True)
        )
        mock_request.assert_called_with(
            "get",
            StringEndsWithMatcher(thread_id), # url
            data=None,
            params=PartialDictMatcher({
                "mark_as_read": True,
                "user_id": 1,
                "recursive": True,
                "resp_skip": response_skip,
                "resp_limit": response_limit,
            }),
            headers=ANY,
            timeout=ANY
        )

    def test_post(self, mock_request):
        request = RequestFactory().post("dummy_url")
        response = views.single_thread(
            request,
            self.course.id.to_deprecated_string(),
            "dummy_discussion_id",
            "dummy_thread_id"
        )
        self.assertEquals(response.status_code, 405)

    def test_not_found(self, mock_request):
        request = RequestFactory().get("dummy_url")
        request.user = self.student
        # Mock request to return 404 for thread request
        mock_request.side_effect = make_mock_request_impl("dummy", thread_id=None)
        self.assertRaises(
            Http404,
            views.single_thread,
            request,
            self.course.id.to_deprecated_string(),
            "test_discussion_id",
            "test_thread_id"
        )


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
@patch('requests.request')
class SingleCohortedThreadTestCase(ModuleStoreTestCase):
    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory.create(user=self.student, course_id=self.course.id)
        self.student_cohort = CourseUserGroup.objects.create(
            name="student_cohort",
            course_id=self.course.id,
            group_type=CourseUserGroup.COHORT
        )

    def _create_mock_cohorted_thread(self, mock_request):
        self.mock_text = "dummy content"
        self.mock_thread_id = "test_thread_id"
        mock_request.side_effect = make_mock_request_impl(
            self.mock_text, self.mock_thread_id,
            group_id=self.student_cohort.id
        )

    def test_ajax(self, mock_request):
        self._create_mock_cohorted_thread(mock_request)

        request = RequestFactory().get(
            "dummy_url",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        request.user = self.student
        response = views.single_thread(
            request,
            self.course.id.to_deprecated_string(),
            "dummy_discussion_id",
            self.mock_thread_id
        )

        self.assertEquals(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEquals(
            response_data["content"],
            make_mock_thread_data(
                self.mock_text, self.mock_thread_id, True,
                group_id=self.student_cohort.id,
                group_name=self.student_cohort.name,
            )
        )

    def test_html(self, mock_request):
        self._create_mock_cohorted_thread(mock_request)

        request = RequestFactory().get("dummy_url")
        request.user = self.student
        mako_middleware_process_request(request)
        response = views.single_thread(
            request,
            self.course.id.to_deprecated_string(),
            "dummy_discussion_id",
            self.mock_thread_id
        )

        self.assertEquals(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        html = response.content

        # Verify that the group name is correctly included in the HTML
        self.assertRegexpMatches(html, r'&quot;group_name&quot;: &quot;student_cohort&quot;')


class SingleThreadGroupIdMixin(object):
    """
    Mixin for testing `views.single_thread` with various group_ids.
    """
    def get_single_thread(
            self,
            user,
            commentable_id,
            group_id,
            mock_request,
            pass_group_id=True,
            expected_status_code=200
    ):
        text = "dummy content"
        thread_id = "test_thread_id"
        mock_request.side_effect = make_mock_request_impl(text, thread_id)

        request_data = {}
        if pass_group_id:
            request_data["group_id"] = group_id
        request = RequestFactory().get(
            "dummy_url",
            data=request_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        request.user = user
        response = views.single_thread(
            request,
            self.course.id.to_deprecated_string(),
            commentable_id,
            thread_id
        )

        self.assertEquals(response.status_code, expected_status_code)

    def get_cohorted_single_thread(self, user, group_id, mock_request, pass_group_id=True, expected_status_code=200):
        self.get_single_thread(user, "cohorted_topic", group_id, mock_request, pass_group_id, expected_status_code)

    def get_non_cohorted_single_thread(self, user, group_id, mock_request, pass_group_id=True, expected_status_code=200):
        self.get_single_thread(user, "non_cohorted_topic", group_id, mock_request, pass_group_id, expected_status_code)


@patch('lms.lib.comment_client.utils.requests.request')
class SingleCohortedThreadGroupIdTestCase(CohortedContentTestCase, SingleThreadGroupIdMixin):
    """
    Verify that `views.single_thread` properly passes `group_id` to the
    comments service in cohorted discussions.
    """
    def test_student_without_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.student, None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_student_none_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.student, "", mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_student_with_own_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.student, self.student_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_student_with_other_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.student, self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_moderator_without_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.moderator, None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_moderator_none_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.moderator, "", mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_moderator_with_own_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.moderator, self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.moderator_cohort.id)

    def test_moderator_with_other_group_id(self, mock_request):
        self.get_cohorted_single_thread(self.moderator, self.student_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_moderator_with_invalid_group_id(self, mock_request):
        invalid_id = self.student_cohort.id + self.moderator_cohort.id
        self.get_cohorted_single_thread(self.moderator, invalid_id, mock_request, expected_status_code=400)
        self.assertEqual(len(mock_request.mock_calls), 1)


@patch('lms.lib.comment_client.utils.requests.request')
class SingleNonCohortedThreadGroupIdTestCase(CohortedContentTestCase, SingleThreadGroupIdMixin):
    """
    Verify that `views.single_thread` properly passes `group_id` to the
    comments service in non-cohorted discussions.
    """
    def test_student_without_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.student, None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_student_none_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.student, None, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_student_with_own_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.student, self.student_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_student_with_other_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.student, self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_moderator_without_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.moderator, None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_moderator_none_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.moderator, None, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_moderator_with_own_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.moderator, self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_moderator_with_other_group_id(self, mock_request):
        self.get_non_cohorted_single_thread(self.moderator, self.student_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_moderator_with_invalid_group_id(self, mock_request):
        invalid_id = self.student_cohort.id + self.moderator_cohort.id
        self.get_non_cohorted_single_thread(self.moderator, invalid_id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
@patch('requests.request')
class UserProfileTestCase(ModuleStoreTestCase):

    TEST_THREAD_TEXT = 'userprofile-test-text'
    TEST_THREAD_ID = 'userprofile-test-thread-id'

    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        self.profiled_user = UserFactory.create()
        CourseEnrollmentFactory.create(user=self.student, course_id=self.course.id)

    def get_response(self, mock_request, params, **headers):
        mock_request.side_effect = make_mock_request_impl(self.TEST_THREAD_TEXT, self.TEST_THREAD_ID)
        request = RequestFactory().get("dummy_url", data=params, **headers)
        request.user = self.student

        mako_middleware_process_request(request)
        response = views.user_profile(
            request,
            self.course.id.to_deprecated_string(),
            self.profiled_user.id
        )
        mock_request.assert_any_call(
            "get",
            StringEndsWithMatcher('/users/{}/active_threads'.format(self.profiled_user.id)),
            data=None,
            params=PartialDictMatcher({
                "course_id": self.course.id.to_deprecated_string(),
                "page": params.get("page", 1),
                "per_page": views.THREADS_PER_PAGE
                }),
            headers=ANY,
            timeout=ANY
        )
        return response

    def check_html(self, mock_request, **params):
        response = self.get_response(mock_request, params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        html = response.content
        self.assertRegexpMatches(html, r'data-page="1"')
        self.assertRegexpMatches(html, r'data-num-pages="1"')
        self.assertRegexpMatches(html, r'<span>1</span> discussion started')
        self.assertRegexpMatches(html, r'<span>2</span> comments')
        self.assertRegexpMatches(html, r'&quot;id&quot;: &quot;{}&quot;'.format(self.TEST_THREAD_ID))
        self.assertRegexpMatches(html, r'&quot;title&quot;: &quot;{}&quot;'.format(self.TEST_THREAD_TEXT))
        self.assertRegexpMatches(html, r'&quot;body&quot;: &quot;{}&quot;'.format(self.TEST_THREAD_TEXT))
        self.assertRegexpMatches(html, r'&quot;username&quot;: &quot;{}&quot;'.format(self.student.username))

    def check_ajax(self, mock_request, **params):
        response = self.get_response(mock_request, params, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json; charset=utf-8')
        response_data = json.loads(response.content)
        self.assertEqual(
            sorted(response_data.keys()),
            ["annotated_content_info", "discussion_data", "num_pages", "page"]
            )
        self.assertEqual(len(response_data['discussion_data']), 1)
        self.assertEqual(response_data["page"], 1)
        self.assertEqual(response_data["num_pages"], 1)
        self.assertEqual(response_data['discussion_data'][0]['id'], self.TEST_THREAD_ID)
        self.assertEqual(response_data['discussion_data'][0]['title'], self.TEST_THREAD_TEXT)
        self.assertEqual(response_data['discussion_data'][0]['body'], self.TEST_THREAD_TEXT)

    def test_html(self, mock_request):
        self.check_html(mock_request)

    def test_html_p2(self, mock_request):
        self.check_html(mock_request, page="2")

    def test_ajax(self, mock_request):
        self.check_ajax(mock_request)

    def test_ajax_p2(self, mock_request):
        self.check_ajax(mock_request, page="2")

    def test_404_profiled_user(self, mock_request):
        request = RequestFactory().get("dummy_url")
        request.user = self.student
        with self.assertRaises(Http404):
            response = views.user_profile(
                request,
                self.course.id.to_deprecated_string(),
                -999
            )

    def test_404_course(self, mock_request):
        request = RequestFactory().get("dummy_url")
        request.user = self.student
        with self.assertRaises(Http404):
            response = views.user_profile(
                request,
                "non/existent/course",
                self.profiled_user.id
            )

    def test_post(self, mock_request):
        mock_request.side_effect = make_mock_request_impl(self.TEST_THREAD_TEXT, self.TEST_THREAD_ID)
        request = RequestFactory().post("dummy_url")
        request.user = self.student
        response = views.user_profile(
            request,
            self.course.id.to_deprecated_string(),
            self.profiled_user.id
        )
        self.assertEqual(response.status_code, 405)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
@patch('requests.request')
class CommentsServiceRequestHeadersTestCase(UrlResetMixin, ModuleStoreTestCase):
    @patch.dict("django.conf.settings.FEATURES", {"ENABLE_DISCUSSION_SERVICE": True})
    def setUp(self):
        username = "foo"
        password = "bar"

        # Invoke UrlResetMixin
        super(CommentsServiceRequestHeadersTestCase, self).setUp()
        self.course = CourseFactory.create()
        self.student = UserFactory.create(username=username, password=password)
        CourseEnrollmentFactory.create(user=self.student, course_id=self.course.id)
        self.assertTrue(
            self.client.login(username=username, password=password)
        )

    def assert_all_calls_have_header(self, mock_request, key, value):
        expected = call(
            ANY, # method
            ANY, # url
            data=ANY,
            params=ANY,
            headers=PartialDictMatcher({key: value}),
            timeout=ANY
        )
        for actual in mock_request.call_args_list:
            self.assertEqual(expected, actual)

    def test_accept_language(self, mock_request):
        lang = "eo"
        text = "dummy content"
        thread_id = "test_thread_id"
        mock_request.side_effect = make_mock_request_impl(text, thread_id)

        self.client.get(
            reverse(
                "django_comment_client.forum.views.single_thread",
                kwargs={
                    "course_id": self.course.id.to_deprecated_string(),
                    "discussion_id": "dummy",
                    "thread_id": thread_id,
                }
            ),
            HTTP_ACCEPT_LANGUAGE=lang,
        )
        self.assert_all_calls_have_header(mock_request, "Accept-Language", lang)

    @override_settings(COMMENTS_SERVICE_KEY="test_api_key")
    def test_api_key(self, mock_request):
        mock_request.side_effect = make_mock_request_impl("dummy", "dummy")

        self.client.get(
            reverse(
                "django_comment_client.forum.views.forum_form_discussion",
                kwargs={"course_id": self.course.id.to_deprecated_string()}
            ),
        )
        self.assert_all_calls_have_header(mock_request, "X-Edx-Api-Key", "test_api_key")


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class InlineDiscussionUnicodeTestCase(ModuleStoreTestCase, UnicodeTestMixin):
    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory(user=self.student, course_id=self.course.id)

    @patch('lms.lib.comment_client.utils.requests.request')
    def _test_unicode_data(self, text, mock_request):
        mock_request.side_effect = make_mock_request_impl(text)
        request = RequestFactory().get("dummy_url")
        request.user = self.student

        response = views.inline_discussion(request, self.course.id.to_deprecated_string(), "dummy_discussion_id")
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["discussion_data"][0]["title"], text)
        self.assertEqual(response_data["discussion_data"][0]["body"], text)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class ForumFormDiscussionUnicodeTestCase(ModuleStoreTestCase, UnicodeTestMixin):
    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory(user=self.student, course_id=self.course.id)

    @patch('lms.lib.comment_client.utils.requests.request')
    def _test_unicode_data(self, text, mock_request):
        mock_request.side_effect = make_mock_request_impl(text)
        request = RequestFactory().get("dummy_url")
        request.user = self.student
        request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest" # so request.is_ajax() == True

        response = views.forum_form_discussion(request, self.course.id.to_deprecated_string())
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["discussion_data"][0]["title"], text)
        self.assertEqual(response_data["discussion_data"][0]["body"], text)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class SingleThreadUnicodeTestCase(ModuleStoreTestCase, UnicodeTestMixin):
    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory(user=self.student, course_id=self.course.id)

    @patch('lms.lib.comment_client.utils.requests.request')
    def _test_unicode_data(self, text, mock_request):
        thread_id = "test_thread_id"
        mock_request.side_effect = make_mock_request_impl(text, thread_id)
        request = RequestFactory().get("dummy_url")
        request.user = self.student
        request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest" # so request.is_ajax() == True

        response = views.single_thread(request, self.course.id.to_deprecated_string(), "dummy_discussion_id", thread_id)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["content"]["title"], text)
        self.assertEqual(response_data["content"]["body"], text)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class UserProfileUnicodeTestCase(ModuleStoreTestCase, UnicodeTestMixin):
    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory(user=self.student, course_id=self.course.id)

    @patch('lms.lib.comment_client.utils.requests.request')
    def _test_unicode_data(self, text, mock_request):
        mock_request.side_effect = make_mock_request_impl(text)
        request = RequestFactory().get("dummy_url")
        request.user = self.student
        request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest" # so request.is_ajax() == True

        response = views.user_profile(request, self.course.id.to_deprecated_string(), str(self.student.id))
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["discussion_data"][0]["title"], text)
        self.assertEqual(response_data["discussion_data"][0]["body"], text)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class FollowedThreadsUnicodeTestCase(ModuleStoreTestCase, UnicodeTestMixin):
    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory(user=self.student, course_id=self.course.id)

    @patch('lms.lib.comment_client.utils.requests.request')
    def _test_unicode_data(self, text, mock_request):
        mock_request.side_effect = make_mock_request_impl(text)
        request = RequestFactory().get("dummy_url")
        request.user = self.student
        request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest" # so request.is_ajax() == True

        response = views.followed_threads(request, self.course.id.to_deprecated_string(), str(self.student.id))
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["discussion_data"][0]["title"], text)
        self.assertEqual(response_data["discussion_data"][0]["body"], text)
