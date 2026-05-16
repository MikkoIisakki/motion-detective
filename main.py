import argparse
import sys

from src.adapters.file_validator import FileVideoValidator
from src.adapters.opencv_video import OpenCVVideoReader, OpenCVVideoWriter
from src.adapters.overlay_renderer import OverlayRenderer
from src.adapters.yolo_detector import YoloPoseDetector
from src.adapters.yolo_pose_estimator import YoloPoseEstimator
from src.cli.commands import (
    AnalyzeCommand,
    LiftsCommand,
    PhasesCommand,
    RulesCommand,
    ValidateCommand,
)
from src.domain.keypoint_smoother import KeypointSmoother
from src.domain.knowledge_base import KnowledgeBase
from src.domain.phase_detector import PhaseDetector
from src.use_cases.analyze_lift import AnalyzeLift
from src.use_cases.analyze_video import AnalyzeVideo


def _smoothing_alpha(value: str) -> float:
    try:
        alpha = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number in [0, 1]") from exc
    if not 0.0 <= alpha <= 1.0:
        raise argparse.ArgumentTypeError("must be in [0, 1]")
    return alpha


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md.sh",
        description="Olympic weightlifting video analysis — pose detection, phase tracking, fault classification.",
        epilog="Examples:\n"
               "  ./md.sh analyze data/lift.mp4 --lift snatch\n"
               "  ./md.sh lifts\n"
               "  ./md.sh phases snatch\n"
               "  ./md.sh rules snatch first_pull\n"
               "  ./md.sh validate data/lift.mp4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # analyze
    analyze = sub.add_parser("analyze", help="Run the full analysis pipeline on a video")
    analyze.add_argument("video_path", help="Path to the input video file")
    analyze.add_argument("--output", default="output/annotated.mp4", help="Output video path (default: output/annotated.mp4)")
    analyze.add_argument("--lift", default="snatch", choices=["snatch", "clean_and_jerk"], help="Lift type (default: snatch)")
    analyze.add_argument("--yolo-model", default="yolov8n-pose.pt", help="YOLO model path (default: yolov8n-pose.pt)")
    analyze.add_argument("--knowledge-base", default="config/knowledge_base.yml", help="Path to fault rules YAML")
    analyze.add_argument("--report-json", default=None, help="Path to JSON session report (default: based on --output)")
    analyze.add_argument("--report-summary", default=None, help="Path to text session summary (default: based on --output)")
    analyze.add_argument("--smoothing", type=_smoothing_alpha, default=0.5, help="Keypoint smoothing factor in [0,1]; 1.0 disables smoothing (default: 0.5)")

    # lifts
    lifts = sub.add_parser("lifts", help="List supported lifts in the knowledge base")
    lifts.add_argument("--knowledge-base", default="config/knowledge_base.yml")

    # phases
    phases = sub.add_parser("phases", help="List phases defined for a given lift")
    phases.add_argument("lift", help="Lift name (e.g. snatch, clean_and_jerk)")
    phases.add_argument("--knowledge-base", default="config/knowledge_base.yml")

    # rules
    rules = sub.add_parser("rules", help="Show fault rules for a specific lift and phase")
    rules.add_argument("lift", help="Lift name")
    rules.add_argument("phase", help="Phase name (e.g. setup, first_pull, catch)")
    rules.add_argument("--knowledge-base", default="config/knowledge_base.yml")

    # validate
    validate = sub.add_parser("validate", help="Validate a video file (path, mime type, openable)")
    validate.add_argument("video_path", help="Path to the video file to validate")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "analyze":
        kb = KnowledgeBase.from_file(args.knowledge_base)
        analyzer = AnalyzeLift(knowledge_base=kb, phase_detector=PhaseDetector(), lift=args.lift)
        output_base = args.output.rsplit(".", 1)[0]
        report_json = args.report_json or f"{output_base}_report.json"
        report_summary = args.report_summary or f"{output_base}_summary.txt"
        smoother = KeypointSmoother(alpha=args.smoothing) if args.smoothing < 1.0 else None
        use_case = AnalyzeVideo(
            validator=FileVideoValidator(),
            reader=OpenCVVideoReader(),
            writer=OpenCVVideoWriter(),
            detector=YoloPoseDetector(yolo_model=args.yolo_model),
            pose_estimator=YoloPoseEstimator(yolo_model=args.yolo_model),
            renderer=OverlayRenderer(),
            analyzer=analyzer,
            smoother=smoother,
            report_json_path=report_json,
            report_summary_path=report_summary,
        )
        return AnalyzeCommand(use_case=use_case, input_path=args.video_path, output_path=args.output, out=sys.stdout).run()

    if args.command == "lifts":
        return LiftsCommand(kb=KnowledgeBase.from_file(args.knowledge_base), out=sys.stdout).run()

    if args.command == "phases":
        return PhasesCommand(kb=KnowledgeBase.from_file(args.knowledge_base), lift=args.lift, out=sys.stdout).run()

    if args.command == "rules":
        return RulesCommand(
            kb=KnowledgeBase.from_file(args.knowledge_base),
            lift=args.lift,
            phase=args.phase,
            out=sys.stdout,
        ).run()

    if args.command == "validate":
        return ValidateCommand(video_path=args.video_path, out=sys.stdout).run()

    return 1


if __name__ == "__main__":
    sys.exit(main())
