
from src.domain.faults import LiftPhase
from src.domain.models import Keypoint, Pose
from src.domain.phase_detector import PhaseDetector, PoseSignal


def pose_with(wrist_y: int, ankle_y: int, hip_y: int = 100, shoulder_y: int = 50,
              knee_y: int | None = None) -> Pose:
    """Build a pose where wrist/ankle/knee/hip/shoulder are at given y-coords.

    The knee defaults to ``hip_y + 40`` for backwards compatibility with the
    original test geometry (shoulder 50, hip 100, knee 140, ankle 300 — a
    250 px shoulder-to-ankle span).
    """
    if knee_y is None:
        knee_y = hip_y + 40
    return Pose([
        Keypoint("left_wrist", 100, wrist_y),
        Keypoint("right_wrist", 110, wrist_y),
        Keypoint("left_ankle", 100, ankle_y),
        Keypoint("right_ankle", 110, ankle_y),
        Keypoint("left_hip", 100, hip_y),
        Keypoint("right_hip", 110, hip_y),
        Keypoint("left_shoulder", 100, shoulder_y),
        Keypoint("right_shoulder", 110, shoulder_y),
        Keypoint("left_knee", 100, knee_y),
        Keypoint("right_knee", 110, knee_y),
    ])


def tall_pose(wrist_y: int, hip_y: int = 500, shoulder_y: int = 300) -> Pose:
    """A body filmed twice as close: 600 px shoulder-to-ankle span
    (shoulder 300, hip 500, knee 700, ankle 900)."""
    return pose_with(
        wrist_y, ankle_y=900, hip_y=hip_y, shoulder_y=shoulder_y, knee_y=700
    )


class TestPoseSignal:
    def test_extracts_average_wrist_height(self):
        pose = pose_with(wrist_y=200, ankle_y=300)
        signal = PoseSignal.from_pose(pose)
        assert signal.wrist_y == 200

    def test_extracts_average_ankle_height(self):
        pose = pose_with(wrist_y=200, ankle_y=300)
        signal = PoseSignal.from_pose(pose)
        assert signal.ankle_y == 300

    def test_extracts_average_knee_height(self):
        pose = pose_with(wrist_y=200, ankle_y=300, hip_y=100)
        signal = PoseSignal.from_pose(pose)
        assert signal.knee_y == 140  # pose_with places knees at hip_y + 40

    def test_returns_none_for_signal_when_keypoints_missing(self):
        pose = Pose([Keypoint("nose", 0, 0)])
        signal = PoseSignal.from_pose(pose)
        assert signal.wrist_y is None
        assert signal.ankle_y is None
        assert signal.knee_y is None

    def test_incomplete_without_knees(self):
        pose = pose_with(wrist_y=200, ankle_y=300)
        without_knees = Pose([
            kp for kp in pose.keypoints if "knee" not in kp.name
        ])
        assert PoseSignal.from_pose(without_knees).is_complete is False


class TestPhaseDetector:
    def test_initial_state_is_idle(self):
        detector = PhaseDetector()
        assert detector.current_phase == LiftPhase.IDLE

    def test_idle_to_setup_when_wrist_at_or_below_knee(self):
        # A loaded bar sits at plate height, so a real lifter's wrists reach
        # knee level, never ankle level. Wrist y >= knee y (image coords:
        # lower = higher y) must be enough to arm the detector.
        detector = PhaseDetector()
        pose = pose_with(wrist_y=250, ankle_y=300)  # knee at 140, ankle at 300
        phase = detector.update(pose)
        assert phase == LiftPhase.SETUP

    def test_idle_to_setup_when_wrist_exactly_at_knee(self):
        detector = PhaseDetector()
        phase = detector.update(pose_with(wrist_y=140, ankle_y=300))
        assert phase == LiftPhase.SETUP

    def test_stays_idle_while_wrist_above_knee(self):
        # Standing with arms hanging puts the wrists near mid-thigh — above
        # the knee — which must not arm the detector.
        detector = PhaseDetector()
        phase = detector.update(pose_with(wrist_y=120, ankle_y=300))
        assert phase == LiftPhase.IDLE

    def test_setup_to_first_pull_when_wrist_starts_rising(self):
        detector = PhaseDetector()
        # establish setup
        detector.update(pose_with(wrist_y=300, ankle_y=300))
        # wrist rising rapidly (lower y = higher in image)
        phase = detector.update(pose_with(wrist_y=290, ankle_y=300))
        phase = detector.update(pose_with(wrist_y=275, ankle_y=300))
        assert phase == LiftPhase.FIRST_PULL

    def test_second_pull_to_catch_when_wrist_above_shoulder(self):
        detector = PhaseDetector()
        # walk through phases
        detector.update(pose_with(wrist_y=300, ankle_y=300))  # setup
        detector.update(pose_with(wrist_y=270, ankle_y=300))  # first_pull
        detector.update(pose_with(wrist_y=240, ankle_y=300))  # transition/second_pull
        detector.update(pose_with(wrist_y=200, ankle_y=300))
        # wrist now above shoulder (smaller y)
        phase = detector.update(pose_with(wrist_y=30, ankle_y=300, shoulder_y=50))
        assert phase == LiftPhase.CATCH

    def test_recovery_when_hip_rising_after_catch(self):
        detector = PhaseDetector()
        detector._phase = LiftPhase.CATCH
        # hip rising (smaller y after catch)
        pose = pose_with(wrist_y=30, ankle_y=300, shoulder_y=50, hip_y=180)
        detector.update(pose)
        pose = pose_with(wrist_y=30, ankle_y=300, shoulder_y=50, hip_y=120)
        phase = detector.update(pose)
        assert phase == LiftPhase.RECOVERY

    def test_skips_phase_change_when_pose_signal_incomplete(self):
        detector = PhaseDetector()
        detector.update(pose_with(wrist_y=300, ankle_y=300))  # setup
        # incomplete pose → keep current phase
        empty = Pose([Keypoint("nose", 0, 0)])
        phase = detector.update(empty)
        assert phase == LiftPhase.SETUP


class TestTransitionPhase:
    """First pull ends when the bar (wrist proxy) passes the knee; the lifter
    is then in the transition (double knee bend) until the bar nears the
    shoulders and the second pull begins."""

    def _detector_in_first_pull(self) -> PhaseDetector:
        detector = PhaseDetector()
        detector.update(pose_with(wrist_y=300, ankle_y=300))  # setup
        detector.update(pose_with(wrist_y=270, ankle_y=300))  # first_pull
        return detector

    def test_stays_in_first_pull_while_wrist_below_knee(self):
        detector = self._detector_in_first_pull()
        # knee at hip_y + 40 = 140; wrist 200 still below the knee
        phase = detector.update(pose_with(wrist_y=200, ankle_y=300))
        assert phase == LiftPhase.FIRST_PULL

    def test_transition_when_wrist_passes_knee(self):
        detector = self._detector_in_first_pull()
        # wrist above knee (140) but not yet near the shoulders (50 + 50)
        phase = detector.update(pose_with(wrist_y=120, ankle_y=300))
        assert phase == LiftPhase.TRANSITION

    def test_transition_to_second_pull_when_wrist_nears_shoulder(self):
        detector = self._detector_in_first_pull()
        detector.update(pose_with(wrist_y=120, ankle_y=300))  # transition
        phase = detector.update(pose_with(wrist_y=80, ankle_y=300))
        assert phase == LiftPhase.SECOND_PULL


class TestBodyScaleInvariance:
    """Thresholds are fractions of the shoulder-to-ankle span, so the detector
    behaves identically whether the lifter fills the frame or stands far from
    the camera. `tall_pose` is the same body at a 600 px span (vs the 250 px
    span of `pose_with`); every gate must scale with it."""

    def _tall_detector_in_transition(self) -> PhaseDetector:
        detector = PhaseDetector()
        detector.update(tall_pose(wrist_y=900))  # setup (wrist below knee 700)
        detector.update(tall_pose(wrist_y=850))  # first_pull
        detector.update(tall_pose(wrist_y=650))  # transition (above knee 700)
        return detector

    def test_second_pull_gate_scales_with_body_span(self):
        detector = self._tall_detector_in_transition()
        assert detector.current_phase == LiftPhase.TRANSITION
        # Wrist 90 px below the shoulder: past a 50 px absolute gate, but
        # within 1/6 of the 600 px span (100 px) — the second pull has begun.
        phase = detector.update(tall_pose(wrist_y=390))
        assert phase == LiftPhase.SECOND_PULL

    def test_setup_rise_gate_scales_with_body_span(self):
        detector = PhaseDetector()
        detector.update(tall_pose(wrist_y=900))  # setup
        # An 8 px wobble is under 1/60 of the 600 px span (10 px): still setup.
        phase = detector.update(tall_pose(wrist_y=892))
        assert phase == LiftPhase.SETUP

    def test_setup_rise_gate_triggers_on_proportional_rise(self):
        detector = PhaseDetector()
        detector.update(tall_pose(wrist_y=900))  # setup
        phase = detector.update(tall_pose(wrist_y=888))  # 12 px >= 10 px
        assert phase == LiftPhase.FIRST_PULL

    def _tall_cnj_detector_in_recovery(self) -> PhaseDetector:
        detector = PhaseDetector(lift="clean_and_jerk")
        detector._phase = LiftPhase.RECOVERY
        detector.update(tall_pose(wrist_y=310))  # standing tall, bar racked
        return detector

    def test_rack_proximity_scales_with_body_span(self):
        detector = self._tall_cnj_detector_in_recovery()
        # Hips descend with the wrist 40 px below the shoulder: outside a
        # 25 px absolute band, inside 1/12 of the 600 px span (50 px).
        phase = detector.update(tall_pose(wrist_y=350, hip_y=510, shoulder_y=310))
        assert phase == LiftPhase.JERK_DIP

    def test_overhead_clearance_scales_with_body_span(self):
        detector = self._tall_cnj_detector_in_recovery()
        detector.update(tall_pose(wrist_y=350, hip_y=510, shoulder_y=310))  # dip
        # Wrist only 60 px above the shoulder: past a 40 px absolute gate but
        # under 2/15 of the 600 px span (80 px) — not clearly overhead yet.
        assert detector.update(tall_pose(wrist_y=250, hip_y=510, shoulder_y=310)) \
            == LiftPhase.JERK_DIP
        # 90 px clearance is past the scaled gate: the jerk catch.
        assert detector.update(tall_pose(wrist_y=220, hip_y=510, shoulder_y=310)) \
            == LiftPhase.JERK_CATCH

    def test_degenerate_span_keeps_current_phase(self):
        detector = PhaseDetector()
        detector.update(pose_with(wrist_y=300, ankle_y=300))  # setup
        # Shoulder at/below ankle is a garbage detection, not a lift signal.
        collapsed = pose_with(wrist_y=300, ankle_y=300, shoulder_y=300, hip_y=300,
                              knee_y=300)
        phase = detector.update(collapsed)
        assert phase == LiftPhase.SETUP


class TestJerkPhases:
    """After the clean's recovery the lifter dips (hips descend, bar stays
    racked at the shoulders), drives the bar overhead into the jerk catch,
    and finally recovers standing."""

    def _cnj_detector_in_recovery(self) -> PhaseDetector:
        detector = PhaseDetector()
        detector.configure_for_lift("clean_and_jerk")
        detector._phase = LiftPhase.RECOVERY
        # standing tall, bar racked: wrist just below shoulder level
        detector.update(pose_with(wrist_y=55, ankle_y=300, hip_y=100, shoulder_y=50))
        return detector

    def test_recovery_to_jerk_dip_when_hips_descend_with_bar_racked(self):
        detector = self._cnj_detector_in_recovery()
        phase = detector.update(
            pose_with(wrist_y=65, ankle_y=300, hip_y=110, shoulder_y=60)
        )
        assert phase == LiftPhase.JERK_DIP

    def test_snatch_stays_in_recovery_when_hips_descend(self):
        detector = PhaseDetector()
        detector._phase = LiftPhase.RECOVERY
        detector.update(pose_with(wrist_y=55, ankle_y=300, hip_y=100, shoulder_y=50))
        phase = detector.update(
            pose_with(wrist_y=65, ankle_y=300, hip_y=110, shoulder_y=60)
        )
        assert phase == LiftPhase.RECOVERY

    def test_no_jerk_dip_when_bar_not_racked(self):
        detector = self._cnj_detector_in_recovery()
        # hips descend but the wrist has dropped well below the shoulders
        # (e.g. lowering the bar) → not a jerk dip
        phase = detector.update(
            pose_with(wrist_y=150, ankle_y=300, hip_y=110, shoulder_y=60)
        )
        assert phase == LiftPhase.RECOVERY

    def test_jerk_dip_to_jerk_catch_when_bar_overhead(self):
        detector = self._cnj_detector_in_recovery()
        detector.update(pose_with(wrist_y=65, ankle_y=300, hip_y=110, shoulder_y=60))
        phase = detector.update(
            pose_with(wrist_y=10, ankle_y=300, hip_y=115, shoulder_y=60)
        )
        assert phase == LiftPhase.JERK_CATCH

    def test_jerk_catch_to_recovery_when_hips_rise(self):
        detector = self._cnj_detector_in_recovery()
        detector.update(pose_with(wrist_y=65, ankle_y=300, hip_y=110, shoulder_y=60))
        detector.update(pose_with(wrist_y=10, ankle_y=300, hip_y=115, shoulder_y=60))
        phase = detector.update(
            pose_with(wrist_y=10, ankle_y=300, hip_y=90, shoulder_y=40)
        )
        assert phase == LiftPhase.RECOVERY

    def test_no_second_jerk_dip_after_jerk_completed(self):
        detector = self._cnj_detector_in_recovery()
        detector.update(pose_with(wrist_y=65, ankle_y=300, hip_y=110, shoulder_y=60))
        detector.update(pose_with(wrist_y=10, ankle_y=300, hip_y=115, shoulder_y=60))
        detector.update(pose_with(wrist_y=10, ankle_y=300, hip_y=90, shoulder_y=40))
        # hips descend again with wrist near shoulders (bar coming down)
        phase = detector.update(
            pose_with(wrist_y=45, ankle_y=300, hip_y=100, shoulder_y=40)
        )
        assert phase == LiftPhase.RECOVERY


class TestMultiRepReEntry:
    """From a terminal recovery (snatch recovery, or clean & jerk recovery
    after the jerk), lowering the bar below knee height while the hips
    descend back toward setup depth starts the next rep: the detector
    re-enters SETUP with per-rep state reset."""

    def _snatch_detector_in_recovery(self) -> PhaseDetector:
        detector = PhaseDetector()
        detector._phase = LiftPhase.RECOVERY
        # standing tall, bar overhead
        detector.update(pose_with(wrist_y=10, ankle_y=300, hip_y=100, shoulder_y=50))
        return detector

    def _cnj_detector_in_post_jerk_recovery(self) -> PhaseDetector:
        detector = PhaseDetector()
        detector.configure_for_lift("clean_and_jerk")
        detector._phase = LiftPhase.RECOVERY
        detector.update(pose_with(wrist_y=55, ankle_y=300, hip_y=100, shoulder_y=50))
        detector.update(pose_with(wrist_y=65, ankle_y=300, hip_y=110, shoulder_y=60))   # jerk dip
        detector.update(pose_with(wrist_y=10, ankle_y=300, hip_y=115, shoulder_y=60))   # jerk catch
        detector.update(pose_with(wrist_y=10, ankle_y=300, hip_y=90, shoulder_y=40))    # recovery
        return detector

    def test_snatch_recovery_reenters_setup_when_bar_below_knees_and_hips_descend(self):
        detector = self._snatch_detector_in_recovery()
        # bar lowered below knee height (knee = hip_y + 40) while hips drop
        phase = detector.update(pose_with(wrist_y=290, ankle_y=300, hip_y=180, shoulder_y=130))
        assert phase == LiftPhase.SETUP

    def test_snatch_recovery_stays_when_bar_below_knees_but_hips_static(self):
        detector = self._snatch_detector_in_recovery()
        # holding the bar low at standing height is not a new setup
        phase = detector.update(pose_with(wrist_y=290, ankle_y=300, hip_y=100, shoulder_y=50))
        assert phase == LiftPhase.RECOVERY

    def test_snatch_recovery_stays_when_hips_descend_but_bar_overhead(self):
        detector = self._snatch_detector_in_recovery()
        phase = detector.update(pose_with(wrist_y=10, ankle_y=300, hip_y=110, shoulder_y=55))
        assert phase == LiftPhase.RECOVERY

    def test_cnj_recovery_before_jerk_does_not_reenter_setup(self):
        detector = PhaseDetector()
        detector.configure_for_lift("clean_and_jerk")
        detector._phase = LiftPhase.RECOVERY
        detector.update(pose_with(wrist_y=55, ankle_y=300, hip_y=100, shoulder_y=50))
        # the clean's recovery is not terminal — the jerk is still pending
        phase = detector.update(pose_with(wrist_y=290, ankle_y=300, hip_y=180, shoulder_y=130))
        assert phase == LiftPhase.RECOVERY

    def test_cnj_post_jerk_recovery_reenters_setup(self):
        detector = self._cnj_detector_in_post_jerk_recovery()
        phase = detector.update(pose_with(wrist_y=290, ankle_y=300, hip_y=180, shoulder_y=130))
        assert phase == LiftPhase.SETUP

    def test_reentry_resets_jerk_state_so_the_next_rep_can_jerk_again(self):
        detector = self._cnj_detector_in_post_jerk_recovery()
        detector.update(pose_with(wrist_y=290, ankle_y=300, hip_y=180, shoulder_y=130))  # setup, rep 2
        # simulate the second clean arriving back at recovery
        detector._phase = LiftPhase.RECOVERY
        detector.update(pose_with(wrist_y=55, ankle_y=300, hip_y=100, shoulder_y=50))
        phase = detector.update(pose_with(wrist_y=65, ankle_y=300, hip_y=110, shoulder_y=60))
        assert phase == LiftPhase.JERK_DIP

    def test_second_rep_progresses_through_the_pull_phases(self):
        detector = self._snatch_detector_in_recovery()
        detector.update(pose_with(wrist_y=290, ankle_y=300, hip_y=180, shoulder_y=130))  # setup, rep 2
        assert detector.update(pose_with(wrist_y=280, ankle_y=300)) == LiftPhase.FIRST_PULL
        assert detector.update(pose_with(wrist_y=120, ankle_y=300)) == LiftPhase.TRANSITION
        assert detector.update(pose_with(wrist_y=80, ankle_y=300)) == LiftPhase.SECOND_PULL
