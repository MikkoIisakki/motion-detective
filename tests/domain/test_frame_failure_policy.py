import pytest

from src.domain.frame_failure_policy import (
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ExcessiveFrameFailuresError,
    FrameFailure,
    FrameFailurePolicy,
)


class TestFrameFailureRecording:
    def test_starts_with_no_failures(self):
        assert FrameFailurePolicy().failures == []

    def test_records_frame_index_and_error_message(self):
        policy = FrameFailurePolicy()
        policy.record_failure(3, RuntimeError("estimator exploded"))

        assert policy.failures == [FrameFailure(frame_index=3, error="estimator exploded")]

    def test_records_error_type_when_message_is_empty(self):
        policy = FrameFailurePolicy()
        policy.record_failure(0, RuntimeError())

        assert policy.failures == [FrameFailure(frame_index=0, error="RuntimeError")]


class TestConsecutiveFailureLimit:
    def test_failures_up_to_limit_do_not_abort(self):
        policy = FrameFailurePolicy(max_consecutive_failures=3)
        for index in range(3):
            policy.record_failure(index, RuntimeError("boom"))

        assert len(policy.failures) == 3

    def test_exceeding_limit_raises(self):
        policy = FrameFailurePolicy(max_consecutive_failures=3)
        for index in range(3):
            policy.record_failure(index, RuntimeError("boom"))

        with pytest.raises(ExcessiveFrameFailuresError, match="3 consecutive"):
            policy.record_failure(3, RuntimeError("boom"))

    def test_success_resets_the_consecutive_count(self):
        policy = FrameFailurePolicy(max_consecutive_failures=2)
        policy.record_failure(0, RuntimeError("boom"))
        policy.record_failure(1, RuntimeError("boom"))
        policy.record_success()
        policy.record_failure(3, RuntimeError("boom"))
        policy.record_failure(4, RuntimeError("boom"))

        assert len(policy.failures) == 4

    def test_non_consecutive_failures_are_all_recorded(self):
        policy = FrameFailurePolicy(max_consecutive_failures=1)
        for index in range(5):
            policy.record_failure(index * 2, RuntimeError("boom"))
            policy.record_success()

        assert len(policy.failures) == 5

    def test_default_limit_is_sane(self):
        assert DEFAULT_MAX_CONSECUTIVE_FAILURES == 5
        policy = FrameFailurePolicy()
        for index in range(DEFAULT_MAX_CONSECUTIVE_FAILURES):
            policy.record_failure(index, RuntimeError("boom"))
        with pytest.raises(ExcessiveFrameFailuresError):
            policy.record_failure(DEFAULT_MAX_CONSECUTIVE_FAILURES, RuntimeError("boom"))

    def test_rejects_non_positive_limit(self):
        with pytest.raises(ValueError, match="max_consecutive_failures"):
            FrameFailurePolicy(max_consecutive_failures=0)
