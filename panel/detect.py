"""Find people in a photo and draw boxes around them.

Right now this runs on the LAPTOP with OpenCV's built-in "HOG" people
detector. It needs no downloads, but it's basic: it finds whole standing
people best and misses people who are sitting, close-up, or partly hidden.

Later, once the AI HAT software (hailo-all) is installed on the Pi, the robot
will use a YOLO model on the Hailo chip instead, which is much better.
"""
import cv2
import numpy as np

METHOD_NAME = "OpenCV HOG on laptop (basic)"
_hog = None


def _get_hog():
    global _hog
    if _hog is None:
        _hog = cv2.HOGDescriptor()
        _hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    return _hog


def detect_people(image, min_score: float = 0.5):
    """Return a list of (x, y, w, h, score) boxes, in the original image's pixels."""
    # Work on a smaller copy: much faster, and HOG works fine at this size.
    scale = 640 / image.shape[1] if image.shape[1] > 640 else 1.0
    small = cv2.resize(image, None, fx=scale, fy=scale) if scale != 1.0 else image

    rects, scores = _get_hog().detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
    if len(rects) == 0:
        return []
    rects = [list(map(int, r)) for r in rects]
    scores = [float(s) for s in np.ravel(scores)]

    # Remove duplicate boxes on the same person ("non-maximum suppression").
    keep = cv2.dnn.NMSBoxes(rects, scores, min_score, 0.4)
    boxes = []
    for i in np.ravel(keep):
        x, y, w, h = rects[i]
        boxes.append((int(x / scale), int(y / scale), int(w / scale), int(h / scale), scores[i]))
    return boxes


def draw_boxes(image, boxes):
    for x, y, w, h, score in boxes:
        cv2.rectangle(image, (x, y), (x + w, y + h), (40, 200, 255), 3)
        label = f"person {score:.2f}"
        cv2.putText(image, label, (x + 4, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 200, 255), 2)
    return image
