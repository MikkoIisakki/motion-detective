import os
import pytest
import sys
import logging
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from input_validator import InputValidator

# Define the custom formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

# Configure the logging
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# Define test video paths
VALID_VIDEO_PATH = "data/sample_video.mp4"
INVALID_VIDEO_PATH = "data/non_existent.mp4"
INVALID_FILE_PATH = "data/text_file.txt"

# content of test_class_demo.py
class TestInputValidator:
    @pytest.fixture(scope="function")
    def mock_video_file(self):
        logger.info("mock_video_file")
        os.makedirs("tests", exist_ok=True)
        file_path = "tests/sample_video.mp4"
        with open(file_path, "wb") as f:
            f.write(os.urandom(1024))  # Create a dummy file
        yield file_path
        logger.info("Removing mock video file")
        os.remove(file_path)  # Cleanup after all tests in the class

    def test_file_exists(self, mock_video_file):
        logger.info("test_file_exists")
        validator = InputValidator(mock_video_file)
        assert validator.file_exists() == True

    def test_file_does_not_exist(self):
        logger.info("IN")
        validator = InputValidator("tests/non_existent.mp4")
        assert validator.file_exists() == False

    def test_is_file(self, mock_video_file):
        logger.info("test_is_file")
        validator = InputValidator(mock_video_file)
        assert validator.is_file() == True

    def test_is_not_a_file(self):
        logger.info("test_is_not_a_file")
        os.makedirs("tests", exist_ok=True)
        validator = InputValidator("tests")
        assert validator.is_file() == False

    def test_is_readable(self):
        validator = InputValidator(VALID_VIDEO_PATH)
        assert validator.is_readable() == True

    def test_is_not_readable(self):
        """Test a non-readable file."""
        os.makedirs("tests", exist_ok=True)
        path = "tests/unreadable.mp4"
        with open(path, "wb") as f:
            f.write(os.urandom(1024))

        try:
            os.chmod(path, 0o000)
            validator = InputValidator(path)
            assert validator.is_readable() == False
        finally:
            os.chmod(path, 0o644)
            os.remove(path)

    @patch("input_validator.mimetypes.guess_type", return_value=("video/mp4", None))
    def test_has_valid_mime_type(self, _mock_mime, mock_video_file):
        validator = InputValidator(mock_video_file)
        assert validator.has_valid_mime_type() == True

    @patch("input_validator.mimetypes.guess_type", return_value=("text/plain", None))
    def test_invalid_mime_type(self, _mock_mime):
        validator = InputValidator(INVALID_FILE_PATH)
        assert validator.has_valid_mime_type() == False

    @patch("input_validator.cv2.VideoCapture")
    def test_is_valid_video_file(self, mock_cv2, mock_video_file):
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_cv2.return_value = mock_capture

        validator = InputValidator(mock_video_file)
        assert validator.is_valid_video_file() == True

    @patch("input_validator.cv2.VideoCapture")
    def test_invalid_video_file(self, mock_cv2):
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = False
        mock_cv2.return_value = mock_capture

        validator = InputValidator(INVALID_VIDEO_PATH)
        assert validator.is_valid_video_file() == False

    @patch.object(InputValidator, "file_exists", return_value=True)
    @patch.object(InputValidator, "is_file", return_value=True)
    @patch.object(InputValidator, "is_readable", return_value=True)
    @patch.object(InputValidator, "has_valid_mime_type", return_value=True)
    @patch.object(InputValidator, "is_valid_video_file", return_value=True)
    def test_validate_passes(self, _mock1, _mock2, _mock3, _mock4, _mock5, mock_video_file):
        validator = InputValidator(mock_video_file)
        assert validator.validate() == True

    @patch.object(InputValidator, "file_exists", return_value=False)
    def test_validate_fails(self, _mock1):
        validator = InputValidator(INVALID_VIDEO_PATH)
        assert validator.validate() == False
