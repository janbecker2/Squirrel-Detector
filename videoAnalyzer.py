import cv2 as cv
import numpy as np

class VideoAnalyzer:
    def __init__(self, scale=0.5, history=500, threshold=32):
        self.scale = scale
        # Initialize the background subtractor once
        self.backSub = cv.createBackgroundSubtractorMOG2(
            history=history, 
            varThreshold=threshold
        )

    def process_video(self, video_path, on_frame=None):
        cap = cv.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open {video_path}")
            return []

        differences = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Apply scaling
            if self.scale != 1.0:
                frame = cv.resize(frame, (0, 0), fx=self.scale, fy=self.scale)

            # Apply background subtraction
            fg_mask = self.backSub.apply(frame)
            
            # Count motion pixels (white pixels in mask)
            pixel_count = int(np.sum(fg_mask > 0))

            # Skip first 5 frames to let MOG2 stabilize
            if frame_count >= 5:
                differences.append(pixel_count)

                # Emit live frame data if callback provided
                if on_frame:
                    on_frame(frame_count, pixel_count)

            frame_count += 1

        cap.release()
        return differences