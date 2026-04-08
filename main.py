import argparse
import sys

from src.weightlifter_detector import WeightlifterDetector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate input and detect the primary weightlifter.")
    parser.add_argument("video_path", help="Path to the input video file")
    parser.add_argument(
        "--output",
        default="output/weightlifter_detected.mp4",
        help="Path for output video (default: output/weightlifter_detected.mp4)",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "hog", "yolo"],
        default="auto",
        help="Detection backend: auto (default), hog, yolo",
    )
    parser.add_argument(
        "--yolo-model",
        default="yolov8n-pose.pt",
        help="YOLO model name/path used when backend is yolo or auto with ultralytics installed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    detector = WeightlifterDetector(
        args.video_path,
        args.output,
        backend=args.backend,
        yolo_model=args.yolo_model,
    )
    output_path = detector.process()
    print(f"Weightlifter detection video written to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
