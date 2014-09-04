from django.test.client import RequestFactory
from django.test.utils import override_settings

from course_groups.models import CourseUserGroup
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
from django_comment_client import base
from django_comment_common.models import Role
from django_comment_common.utils import seed_permissions_roles
from mock import patch
from student.tests.factories import CourseEnrollmentFactory, UserFactory
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class CohortedContentTestCase(ModuleStoreTestCase):
    """
    Sets up a course with a student, a moderator and their cohorts.
    """
    @patch.dict("django.conf.settings.FEATURES", {"ENABLE_DISCUSSION_SERVICE": True})
    def setUp(self):
        super(CohortedContentTestCase, self).setUp()

        self.course = CourseFactory.create(
            discussion_topics={
                "cohorted topic": {"id": "cohorted_topic"},
                "non-cohorted topic": {"id": "non_cohorted_topic"},
            },
            cohort_config={
                "cohorted": True,
                "cohorted_discussions": ["cohorted_topic"]
            }
        )
        self.student_cohort = CourseUserGroup.objects.create(
            name="student_cohort",
            course_id=self.course.id,
            group_type=CourseUserGroup.COHORT
        )
        self.moderator_cohort = CourseUserGroup.objects.create(
            name="moderator_cohort",
            course_id=self.course.id,
            group_type=CourseUserGroup.COHORT
        )

        seed_permissions_roles(self.course.id)
        self.student = UserFactory.create()
        self.moderator = UserFactory.create()
        CourseEnrollmentFactory(user=self.student, course_id=self.course.id)
        CourseEnrollmentFactory(user=self.moderator, course_id=self.course.id)
        self.moderator.roles.add(Role.objects.get(name="Moderator", course_id=self.course.id))
        self.student_cohort.users.add(self.student)
        self.moderator_cohort.users.add(self.moderator)

    def _create_thread(
            self,
            user,
            commentable_id,
            mock_request,
            group_id,
            pass_group_id=True,
            expected_status_code=200
    ):
        mock_request.return_value.status_code = 200
        request_data = {"body": "body", "title": "title", "thread_type": "discussion"}
        if pass_group_id:
            request_data["group_id"] = group_id
        request = RequestFactory().post("dummy_url", request_data)
        request.user = user
        request.view_name = "create_thread"

        response = base.views.create_thread(
            request,
            course_id=self.course.id.to_deprecated_string(),
            commentable_id=commentable_id
        )
        self.assertEqual(response.status_code, expected_status_code)

    def _assert_comments_service_called_with_group_id(self, mock_request, group_id):
        self.assertTrue(mock_request.called)
        if mock_request.call_args[0][0] == "get":
            self.assertEqual(mock_request.call_args[1]["params"]["group_id"], group_id)
        elif mock_request.call_args[0][0] == "post":
            self.assertEqual(mock_request.call_args[1]["data"]["group_id"], group_id)


    def _assert_comments_service_called_without_group_id(self, mock_request):
        self.assertTrue(mock_request.called)
        self.assertNotIn("group_id", mock_request.call_args[1]["data"])
