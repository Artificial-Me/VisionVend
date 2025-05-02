"""
tracker.py
Handles BYTETracker tracking, bounding box refinement (hand-aware), augmentation, and saving labeled data.
"""
import cv2
import numpy as np
import uuid
import json
import time
from pathlib import Path
from ultralytics.trackers.byte_tracker import BYTETracker
from VisionVend.config import config as CFG

AUTO = CFG["training"]["autolabel"]
DATA  = Path(CFG["training"]["dataset_path"])
IMG_D = DATA / "images"
LBL_D = DATA / "labels"
IMG_D.mkdir(parents=True, exist_ok=True)
LBL_D.mkdir(parents=True, exist_ok=True)

def ensure_class_id(sku: str) -> int:
    f = DATA / "classes.json"
    cls = json.loads(f.read_text()) if f.exists() else {}
    if sku not in cls:
        cls[sku] = len(cls)
        f.write_text(json.dumps(cls, indent=2))
    return cls[sku]

def shrink_box(box, hand_polys, thr):
    x1, y1, x2, y2 = map(int, box)
    best_iou = 0
    offending_side = None
    for poly in hand_polys:
        hp_x1, hp_y1 = poly.min(0)
        hp_x2, hp_y2 = poly.max(0)
        inter_x1, inter_y1 = max(x1, hp_x1), max(y1, hp_y1)
        inter_x2, inter_y2 = min(x2, hp_x2), min(y2, hp_y2)
        if inter_x1 < inter_x2 and inter_y1 < inter_y2:
            inter = (inter_x2-inter_x1)*(inter_y2-inter_y1)
            iou = inter / ((x2-x1)*(y2-y1) + 1e-9)
            if iou > best_iou:
                best_iou = iou
                # decide which edge overlaps most
                if abs(inter_x2 - x2) < 5: offending_side = 'right'
                elif abs(inter_x1 - x1) < 5: offending_side = 'left'
                elif abs(inter_y2 - y2) < 5: offending_side = 'bottom'
                else: offending_side = 'top'
    if best_iou < thr:
        return [x1, y1, x2, y2]  # good
    dx = int(0.15 * (x2 - x1))
    dy = int(0.15 * (y2 - y1))
    if offending_side == 'right':  x2 -= dx
    if offending_side == 'left':   x1 += dx
    if offending_side == 'bottom': y2 -= dy
    if offending_side == 'top':    y1 += dy
    return [x1, y1, x2, y2]

def normalise(bb, W, H):
    x1, y1, x2, y2 = bb
    xc = (x1 + x2) / 2 / W
    yc = (y1 + y2) / 2 / H
    bw = (x2 - x1) / W
    bh = (y2 - y1) / H
    return xc, yc, bw, bh

async def track_and_save(cam_id, frame_queue, stop_event, sku, log_queue=None):
    class_id = ensure_class_id(sku)
    tracker = BYTETracker(dict(track_thresh=0.2, match_thresh=0.8, buffer=30, frame_rate=30))
    stable = {}
    saved = 0
    while not stop_event.is_set():
        try:
            frame, mask, hand_polys, W, H = await asyncio.wait_for(frame_queue.get(), timeout=2.0)
        except asyncio.TimeoutError:
            if log_queue:
                await log_queue.put({"level": "warning", "msg": f"Camera {cam_id} frame queue timeout."})
            break
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dets = []
        for c in cnts:
            area = cv2.contourArea(c)
            if not (AUTO["min_area"] < area < AUTO["max_area"] * W * H):
                continue
            x, y, w, h = cv2.boundingRect(c)
            dets.append([x, y, x + w, y + h, 1.0])
        if not dets:
            tracker.update(np.empty((0, 5)), (H, W), (H, W))
            continue
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
                if log_queue:
                    await log_queue.put({"level": "info", "msg": f"Saved frame for track {tid} cam {cam_id}"})
        await asyncio.sleep(0.01)
    if log_queue:
        await log_queue.put({"level": "info", "msg": f"Camera {cam_id} saved {saved} frames."})
    return saved
