# motion-detective

`motion-detective` now includes a weightlifter detection baseline that:
- validates an input video,
- detects the primary weightlifter each frame (YOLO if configured, otherwise HOG + motion fallback),
- writes an output video with a weightlifter bounding box overlay.

## Run

```bash
cd motion-detective
./myenv/bin/python main.py data/sample_video.mp4 --output output/weightlifter_detected.mp4
```

YOLO backend:

```bash
cd motion-detective
./myenv/bin/python main.py data/sample_video.mp4 --backend yolo --yolo-model yolov8n-pose.pt --output output/weightlifter_detected.mp4
```

## How it works

- `src/input_validator.py`: file/path/mime/video validation.
- `src/weightlifter_detector.py`: weightlifter detection + video rendering.
- `main.py`: CLI entrypoint.

Current assumptions (good for MVP):
- mostly static camera.
- single primary person in frame.

## Tests

```bash
cd motion-detective
./myenv/bin/python -m pytest -q
```
