import os
import cv2
import mimetypes
import logging

class InputValidator:
    def __init__(self, video_path):
        self.video_path = os.path.abspath(video_path)

    def file_exists(self):
        if not os.path.exists(self.video_path):
            logging.error(f"The file '{self.video_path}' does not exist.")
            return False
        return True

    def is_file(self):
        if not os.path.isfile(self.video_path):
            logging.error(f"'{self.video_path}' is not a file.")
            return False
        return True

    def is_readable(self):
        if not os.access(self.video_path, os.R_OK):
            logging.error(f"The file '{self.video_path}' is not readable.")
            return False
        return True

    def has_valid_mime_type(self):
        mime_type, _ = mimetypes.guess_type(self.video_path)
        if mime_type is None or not mime_type.startswith("video"):
            logging.error(f"'{self.video_path}' is not recognized as a valid video format.")
            return False
        return True

    def is_valid_video_file(self):
        """ Verify the video file is not corrupted using OpenCV. """
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                logging.error(f"'{self.video_path}' is not a valid or readable video file.")
                return False
            cap.release()
        except Exception as e:
            logging.error(f"An error occurred while validating the video file: {e}")
            return False
        return True

    def validate(self):
        """ Run all validation checks and return True only if all pass. """
        return (
            self.file_exists() and
            self.is_file() and
            self.is_readable() and
            self.has_valid_mime_type() and
            self.is_valid_video_file()
        )

