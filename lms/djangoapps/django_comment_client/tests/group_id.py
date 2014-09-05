class GroupIdTestMixin(object):
    """
    Provides test cases to verify that views pass the correct `group_id` to
    the comments service.
    """
    @staticmethod
    def _data_or_params_cs_request(mock_request):
        if mock_request.call_args[0][0] == "get":
            return mock_request.call_args[1]["params"]
        elif mock_request.call_args[0][0] == "post":
            return mock_request.call_args[1]["data"]

    def _assert_comments_service_called_with_group_id(self, mock_request, group_id):
        self.assertTrue(mock_request.called)
        self.assertEqual(self._data_or_params_cs_request(mock_request)["group_id"], group_id)

    def _assert_comments_service_called_without_group_id(self, mock_request):
        self.assertTrue(mock_request.called)
        self.assertNotIn("group_id", self._data_or_params_cs_request(mock_request))

    def test_cohorted_topic_student_without_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "cohorted_topic", None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_cohorted_topic_student_none_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "cohorted_topic", "", mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_cohorted_topic_student_with_own_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "cohorted_topic", self.student_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_cohorted_topic_student_with_other_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "cohorted_topic", self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_cohorted_topic_moderator_without_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "cohorted_topic", None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_cohorted_topic_moderator_none_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "cohorted_topic", "", mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_cohorted_topic_moderator_with_own_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "cohorted_topic", self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.moderator_cohort.id)

    def test_cohorted_topic_moderator_with_other_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "cohorted_topic", self.student_cohort.id, mock_request)
        self._assert_comments_service_called_with_group_id(mock_request, self.student_cohort.id)

    def test_cohorted_topic_moderator_with_invalid_group_id(self, mock_request):
        invalid_id = self.student_cohort.id + self.moderator_cohort.id
        self._assert_view_returns_error(
            lambda: self.call_view_with_group_id(
                self.moderator,
                "cohorted_topic",
                invalid_id,
                mock_request
            )
        )

    def test_non_cohorted_topic_student_without_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "non_cohorted_topic", None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_student_none_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "non_cohorted_topic", None, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_student_with_own_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "non_cohorted_topic", self.student_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_student_with_other_group_id(self, mock_request):
        self.call_view_with_group_id(self.student, "non_cohorted_topic", self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_moderator_without_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "non_cohorted_topic", None, mock_request, pass_group_id=False)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_moderator_none_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "non_cohorted_topic", None, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_moderator_with_own_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "non_cohorted_topic", self.moderator_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_moderator_with_other_group_id(self, mock_request):
        self.call_view_with_group_id(self.moderator, "non_cohorted_topic", self.student_cohort.id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)

    def test_non_cohorted_topic_moderator_with_invalid_group_id(self, mock_request):
        invalid_id = self.student_cohort.id + self.moderator_cohort.id
        self.call_view_with_group_id(self.moderator, "non_cohorted_topic", invalid_id, mock_request)
        self._assert_comments_service_called_without_group_id(mock_request)
