import os
from dotenv import load_dotenv
from trackers import SORTTracker
import supervision as sv
from urllib.request import urlretrieve
from huggingface_hub import login


def load_env_and_login():
    load_dotenv()
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        raise RuntimeError("HUGGINGFACE_TOKEN not found in environment variables.")
    login(token=hf_token)


def download_sample_videos(video_urls):
    for url in video_urls:
        filename = os.path.basename(url)
        if not os.path.exists(filename):
            print(f"Downloading {filename}...")
            urlretrieve(url, filename)


import torch
import supervision as sv
from trackers import SORTTracker
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor


def load_env_and_login():
    load_dotenv()
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        raise RuntimeError("HUGGINGFACE_TOKEN not found in environment variables.")
    login(token=hf_token)

def download_sample_videos(video_urls):
    for url in video_urls:
        filename = os.path.basename(url)
        if not os.path.exists(filename):
            print(f"Downloading {filename}...")
            urlretrieve(url, filename)


def main():
    load_env_and_login()
    VIDEO_URLS = [
        "https://storage.googleapis.com/com-roboflow-marketing/supervision/video-examples/bikes-1280x720-1.mp4",
        "https://storage.googleapis.com/com-roboflow-marketing/supervision/video-examples/bikes-1280x720-2.mp4",
    ]
    download_sample_videos(VIDEO_URLS)
    tracker = SORTTracker()
    image_processor = RTDetrImageProcessor.from_pretrained("PekingU/rtdetr_v2_r18vd")
    model = RTDetrV2ForObjectDetection.from_pretrained("PekingU/rtdetr_v2_r18vd")
    annotator = sv.LabelAnnotator(text_position=sv.Position.CENTER)

    def callback(frame, _):
        inputs = image_processor(images=frame, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)

        h, w, _ = frame.shape
        results = image_processor.post_process_object_detection(
            outputs,
            target_sizes=torch.tensor([(h, w)]),
            threshold=0.5
        )[0]

        detections = sv.Detections.from_transformers(
            transformers_results=results,
            id2label=model.config.id2label
        )

        detections = tracker.update(detections)
        return annotator.annotate(frame, detections, labels=detections.tracker_id)

    sv.process_video(
        source_path="bikes-1280x720-1.mp4",
        target_path="bikes-1280x720-1-result.mp4",
        callback=callback,
    )


if __name__ == "__main__":
    main()