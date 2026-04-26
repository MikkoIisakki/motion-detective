import os
import stat
import pytest
from unittest.mock import patch

from src.adapters.file_validator import FileVideoValidator


@pytest.fixture()
def tmp_mp4(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"\x00" * 64)
    return str(f)


class TestFileVideoValidator:
    def setup_method(self):
        self.validator = FileVideoValidator()

    def test_raises_when_file_does_not_exist(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            self.validator.validate(str(tmp_path / "missing.mp4"))

    def test_raises_when_path_is_a_directory(self, tmp_path):
        with pytest.raises(ValueError, match="Not a file"):
            self.validator.validate(str(tmp_path))

    def test_raises_when_file_is_not_readable(self, tmp_mp4):
        os.chmod(tmp_mp4, 0o000)
        try:
            with pytest.raises(ValueError, match="not readable"):
                self.validator.validate(tmp_mp4)
        finally:
            os.chmod(tmp_mp4, stat.S_IRUSR | stat.S_IWUSR)

    def test_raises_when_mime_type_is_not_video(self, tmp_path):
        f = tmp_path / "document.txt"
        f.write_bytes(b"hello")
        with pytest.raises(ValueError, match="recognised video"):
            self.validator.validate(str(f))

    @patch("src.adapters.file_validator.cv2.VideoCapture")
    def test_raises_when_opencv_cannot_open_file(self, mock_cap, tmp_mp4):
        mock_cap.return_value.isOpened.return_value = False
        with pytest.raises(ValueError, match="OpenCV cannot open"):
            self.validator.validate(tmp_mp4)

    @patch("src.adapters.file_validator.cv2.VideoCapture")
    def test_passes_for_valid_video(self, mock_cap, tmp_mp4):
        mock_cap.return_value.isOpened.return_value = True
        self.validator.validate(tmp_mp4)  # should not raise
