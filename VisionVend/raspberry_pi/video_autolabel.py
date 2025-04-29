"""
video_autolabel.py
Auto-labels dataset frames from a video file (e.g. GoPro footage) for cross-platform (Windows, Mac, Linux) dataset creation.
Usage:
    python -m VisionVend.raspberry_pi.video_autolabel --sku cola --video path/to/video.mp4 --every 5
"""
import cv2
import argparse
import uuid
import json
from pathlib import Path
from VisionVend.raspberry_pi.tracker import ensure_class_id, shrink_box, normalise
from VisionVend.config import config as CFG
from ultralytics.trackers.byte_tracker import BYTETracker
from skimage import morphology
import mediapipe as mp
import numpy as np

AUTO = CFG["training"]["autolabel"]
DATA  = Path(CFG["training"]["dataset_path"])
IMG_D = DATA / "images"
LBL_D = DATA / "labels"
IMG_D.mkdir(parents=True, exist_ok=True)
LBL_D.mkdir(parents=True, exist_ok=True)

mp_hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

def hand_polygons(rgb):
    h, w, _ = rgb.shape
    results = mp_hands.process(rgb)
    polys = []
    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            pts = [(lm.x * w, lm.y * h) for lm in hand.landmark]
            polys.append(np.array(pts, dtype=np.int32))
    return polys

def main(sku, video_path, every=5, display=False):
    class_id = ensure_class_id(sku)
    cap = cv2.VideoCapture(video_path)
    tracker = BYTETracker(dict(track_thresh=0.2, match_thresh=0.8, buffer=30, frame_rate=30))
    frame_idx = 0
    stable = {}
    saved = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % every != 0:
            frame_idx += 1
            continue
        mask = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = cv2.GaussianBlur(mask, (5,5), 0)
        _, mask = cv2.threshold(mask, 30, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask = morphology.remove_small_objects(mask.astype(bool), 100).astype('uint8')*255
        hand_polys = hand_polygons(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        for poly in hand_polys:
            cv2.fillPoly(mask, [poly], 0)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dets = []
        H, W = frame.shape[:2]
        for c in cnts:
            area = cv2.contourArea(c)
            if not (AUTO["min_area"] < area < AUTO["max_area"] * W * H):
                continue
            x, y, w, h = cv2.boundingRect(c)
            dets.append([x, y, x + w, y + h, 1.0])
        if not dets:
            tracker.update(np.empty((0, 5)), (H, W), (H, W))
        for t in tracker.update(np.array(dets), (H, W), (H, W)):
            tid = int(t.track_id)
            bb = shrink_box(t.tlbr, hand_polys, AUTO["hand_iou_max"])
            stable[tid] = stable.get(tid, 0) + 1
            if stable[tid] == AUTO["stable_frames"]:
                uid = uuid.uuid4().hex
                cv2.imwrite(str(IMG_D / f"{uid}.jpg"), frame)
                xc, yc, bw, bh = normalise(bb, W, H)
                (LBL_D / f"{uid}.txt").write_text(f"{class_id} {xc:.5f} {yc:.5f} {bw:.5f} {bh:.5f}\n")
                if AUTO["save_aug"]:
                    img = cv2.flip(frame, 1)
                    uid2 = uuid.uuid4().hex
                    cv2.imwrite(str(IMG_D / f"{uid2}.jpg"), img)
                    (LBL_D / f"{uid2}.txt").write_text(f"{class_id} {1-xc:.5f} {yc:.5f} {bw:.5f} {bh:.5f}\n")
                saved += 1
        if display:
            cv2.imshow("auto-label", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        frame_idx += 1
    cap.release()
    cv2.destroyAllWindows()
    print(f"✅ Auto-labeled {saved} frames from {video_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sku", required=True, help="Product SKU")
    ap.add_argument("--video", required=True, help="Path to video file")
    ap.add_argument("--every", type=int, default=5, help="Process every Nth frame")
    ap.add_argument("--display", action="store_true", help="Show debug window")
    args = ap.parse_args()
    main(args.sku, args.video, args.every, args.display)
