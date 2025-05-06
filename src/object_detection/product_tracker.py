import os
from dotenv import load_dotenv
from trackers import SORTTracker
import supervision as sv
from urllib.request import urlretrieve
from huggingface_hub import login
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


def main(input_path=None, output_dir=None):
    """Run the product tracker with direct parameters instead of CLI args"""
    load_env_and_login()
    
    # Check for GPU availability
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    tracker = SORTTracker()
    image_processor = RTDetrImageProcessor.from_pretrained("PekingU/rtdetr_v2_r18vd")
    model = RTDetrV2ForObjectDetection.from_pretrained("PekingU/rtdetr_v2_r18vd").to(device)
    annotator = sv.LabelAnnotator(text_position=sv.Position.CENTER)

    def callback(frame, _):
        inputs = image_processor(images=frame, return_tensors="pt").to(device)
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

    output_dir = output_dir if output_dir else os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    source_path = input_path if input_path else os.path.join(os.path.dirname(__file__), "input", "bikes-1280x720-1.mp4")
    source_filename = os.path.splitext(os.path.basename(source_path))[0]
    target_path = os.path.join(output_dir, f"{source_filename}_result.mp4")
    sv.process_video(
        source_path=source_path,
        target_path=target_path,
        callback=callback,
    )


if __name__ == "__main__":
    main()