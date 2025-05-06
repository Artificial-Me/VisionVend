"""
capture.py
Handles camera capture, background subtraction, mask cleaning, and hand polygon detection for dual-camera auto-labeling.
"""
import cv2
import mediapipe as mp
import numpy as np
from skimage import morphology
from pathlib import Path
import asyncio
import logging

from VisionVend.config import config as CFG

AUTO = CFG["training"]["autolabel"]

mp_hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

def hand_polygons(rgb):
    """Returns list of np.ndarray polygons (N,2) in pixel coords for each detected hand."""
    h, w, _ = rgb.shape
    results = mp_hands.process(rgb)
    polys = []
    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            pts = [(lm.x * w, lm.y * h) for lm in hand.landmark]
            polys.append(np.array(pts, dtype=np.int32))
    return polys

async def capture_frames(cam_id, frame_queue, stop_event, log_queue=None):
    cap = cv2.VideoCapture(cam_id, cv2.CAP_V4L2)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    back = cv2.createBackgroundSubtractorMOG2(AUTO.get("history", 400), AUTO.get("varThreshold", 40), False)
    
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            if log_queue:
                await log_queue.put({"level": "error", "msg": f"Camera {cam_id} failed to read frame."})
            break
        mask = back.apply(frame)
        mask = morphology.remove_small_objects(mask.astype(bool), 100).astype('uint8')*255
        hand_polys = hand_polygons(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        for poly in hand_polys:
            cv2.fillPoly(mask, [poly], 0)
        await frame_queue.put((frame, mask, hand_polys, W, H))
        await asyncio.sleep(0.01)
    cap.release()
    if log_queue:
        await log_queue.put({"level": "info", "msg": f"Camera {cam_id} released."})

# Optionally, add a calibration function here for future expansion.
