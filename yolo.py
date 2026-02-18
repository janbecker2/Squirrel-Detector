from ultralytics import YOLO
import cv2 as cv
class YoloDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def detect(self, frame):
        results = self.model(frame)
        return results
model = YOLO(r"squirrel_model2/weights/squirrelrightclasses.pt")
