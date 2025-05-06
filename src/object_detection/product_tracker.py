import os
from dotenv import load_dotenv
from trackers import SORTTracker, DeepSORTTracker
import supervision as sv
import torch
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor
import cv2
from typing import Literal, Optional, Dict, Any
from dataclasses import dataclass
import time
import numpy as np

@dataclass
class TrackerConfig:
    """Configuration for object tracker"""
    tracker_type: Literal["sort", "deepsort"] = "sort"
    max_age: int = 1
    min_hits: int = 3
    iou_threshold: float = 0.3
    appearance_threshold: float = 0.5
    max_cosine_distance: float = 0.2
    nn_budget: Optional[int] = None

@dataclass
class DetectionConfig:
    """Configuration for object detection"""
    model_name: str = "PekingU/rtdetr_v2_r18vd"
    detection_threshold: float = 0.5

@dataclass
class VisualizationConfig:
    """Configuration for visualization"""
    show_confidence: bool = False
    show_class: bool = True
    show_trajectories: bool = False
    trajectory_length: int = 30

class ProductTracker:
    """Main product tracking class with modular components"""
    
    def __init__(self, tracker_config: TrackerConfig, 
                 detection_config: DetectionConfig,
                 vis_config: VisualizationConfig):
        """Initialize tracker with configurations"""
        self.tracker_config = tracker_config
        self.detection_config = detection_config
        self.vis_config = vis_config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.metrics = {
            'processing_time': 0,
            'objects_tracked': 0,
            'fps': 0
        }
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize tracker, model and annotators"""
        # Initialize tracker
        if self.tracker_config.tracker_type == "sort":
            self.tracker = SORTTracker(
                max_age=self.tracker_config.max_age,
                min_hits=self.tracker_config.min_hits,
                iou_threshold=self.tracker_config.iou_threshold
            )
        else:
            self.tracker = DeepSORTTracker(
                max_age=self.tracker_config.max_age,
                min_hits=self.tracker_config.min_hits,
                iou_threshold=self.tracker_config.iou_threshold,
                appearance_threshold=self.tracker_config.appearance_threshold,
                max_cosine_distance=self.tracker_config.max_cosine_distance,
                nn_budget=self.tracker_config.nn_budget
            )
        
        # Initialize detector
        self.image_processor = RTDetrImageProcessor.from_pretrained(
            self.detection_config.model_name)
        self.model = RTDetrV2ForObjectDetection.from_pretrained(
            self.detection_config.model_name).to(self.device)
        
        # Initialize annotators
        self.annotators = []
        self.box_annotator = sv.BoxAnnotator()
        self.annotators.append(self.box_annotator)
        
        if self.vis_config.show_trajectories:
            self.trace_annotator = sv.TraceAnnotator(
                position=sv.Position.CENTER,
                trace_length=self.vis_config.trajectory_length
            )
            self.annotators.append(self.trace_annotator)
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a single frame and return annotated result"""
        # Detection
        inputs = self.image_processor(images=frame, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)

        h, w, _ = frame.shape
        results = self.image_processor.post_process_object_detection(
            outputs,
            target_sizes=torch.tensor([(h, w)]),
            threshold=self.detection_config.detection_threshold
        )[0]

        detections = sv.Detections.from_transformers(
            transformers_results=results,
            id2label=self.model.config.id2label
        )

        # Tracking
        detections = self.tracker.update(detections)
        self.metrics['objects_tracked'] = len(detections)
        
        # Annotation
        labels = []
        for tracker_id, class_id, confidence in zip(
            detections.tracker_id,
            detections.class_id,
            detections.confidence
        ):
            label_parts = [f"#{tracker_id}"]
            if self.vis_config.show_class:
                label_parts.append(self.model.config.id2label[class_id])
            if self.vis_config.show_confidence:
                label_parts.append(f"{confidence:.2f}")
            labels.append(" ".join(label_parts))
        
        annotated_frame = frame.copy()
        for annotator in self.annotators:
            annotated_frame = annotator.annotate(
                scene=annotated_frame,
                detections=detections,
                labels=labels if isinstance(annotator, sv.BoxAnnotator) else None
            )
            
        return annotated_frame
    
    def process_video(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process video file and return metrics"""
        start_time = time.time()
        frame_count = 0
        
        def callback(frame: np.ndarray, _: int) -> np.ndarray:
            nonlocal frame_count
            frame_count += 1
            return self.process_frame(frame)
        
        sv.process_video(
            source_path=input_path,
            target_path=output_path,
            callback=callback
        )
        
        # Calculate metrics
        self.metrics['processing_time'] = time.time() - start_time
        self.metrics['fps'] = frame_count / self.metrics['processing_time']
        
        return self.metrics

# Helper functions for backward compatibility
def load_env_and_login():
    load_dotenv()
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        raise RuntimeError("HUGGINGFACE_TOKEN not found in environment variables.")
    login(token=hf_token)

def main(**kwargs):
    """Main entry point with backward compatible interface"""
    load_env_and_login()
    
    # Create configurations from kwargs
    tracker_config = TrackerConfig(
        tracker_type=kwargs.get('tracker_type', 'sort'),
        max_age=kwargs.get('max_age', 1),
        min_hits=kwargs.get('min_hits', 3),
        iou_threshold=kwargs.get('iou_threshold', 0.3),
        appearance_threshold=kwargs.get('appearance_threshold', 0.5),
        max_cosine_distance=kwargs.get('max_cosine_distance', 0.2),
        nn_budget=kwargs.get('nn_budget', None)
    )
    
    detection_config = DetectionConfig(
        model_name=kwargs.get('model_name', 'PekingU/rtdetr_v2_r18vd'),
        detection_threshold=kwargs.get('detection_threshold', 0.5)
    )
    
    vis_config = VisualizationConfig(
        show_confidence=kwargs.get('show_confidence', False),
        show_class=kwargs.get('show_class', True),
        show_trajectories=kwargs.get('show_trajectories', False),
        trajectory_length=kwargs.get('trajectory_length', 30)
    )
    
    # Initialize and run tracker
    tracker = ProductTracker(tracker_config, detection_config, vis_config)
    
    input_path = kwargs.get('input_path')
    output_dir = kwargs.get('output_dir', os.path.join(os.path.dirname(__file__), "output"))
    os.makedirs(output_dir, exist_ok=True)
    
    if not input_path:
        input_path = os.path.join(os.path.dirname(__file__), "input", "bikes-1280x720-1.mp4")
    
    source_filename = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{source_filename}_result.mp4")
    
    metrics = tracker.process_video(input_path, output_path)
    return metrics

if __name__ == "__main__":
    main()