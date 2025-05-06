# restock_and_train_pipeline_v2.py
import os
import cv2
import time
import json
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path
try:
    from ruamel.yaml import YAML
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
except ImportError:
    import yaml # PyYAML as fallback

import easyocr # OCR library

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
class PipelineConfig:
    def __init__(self, dfine_repo_path, base_data_dir="vending_data"):
        self.BASE_DATA_DIR = Path(base_data_dir)
        self.RAW_VIDEO_DIR = self.BASE_DATA_DIR / "raw_restock_videos"
        self.FRAMES_DIR = self.BASE_DATA_DIR / "training_frames" # Extracted frames for annotation
        
        # Temporary directory for a single training run, structured for D-FINE
        self.TEMP_TRAINING_SESSION_DIR = self.BASE_DATA_DIR / "temp_training_session"
        self.TEMP_IMAGES_TRAIN_DIR = self.TEMP_TRAINING_SESSION_DIR / "images" / "train"
        self.TEMP_ANNOTATIONS_DIR = self.TEMP_TRAINING_SESSION_DIR / "annotations"
        
        self.MODEL_OUTPUT_DIR = self.BASE_DATA_DIR / "trained_models" # Where final models are stored
        
        self.DFINE_REPO_PATH = Path(dfine_repo_path)
        if not (self.DFINE_REPO_PATH / "train.py").exists():
            raise FileNotFoundError(f"D-FINE train.py not found in {self.DFINE_REPO_PATH}")

        # --- D-FINE/DEIM Specific Configs ---
        # These will be created dynamically
        self.DFINE_CUSTOM_DATASET_CONFIG_NAME = "custom_vending_dataset_config.yml"
        self.DFINE_CUSTOM_MODEL_CONFIG_NAME = "dfine_hgnetv2_n_vending_custom.yml" # Example using 'n' model
        self.DFINE_MODEL_VARIANT = "n" # D-FINE model size (e.g., n, s, m, l, x)

        # --- Product SKUs (Ideally loaded from an external source like your Google Sheet) ---
        self.KNOWN_PRODUCT_SKUS = sorted([
            "coke_can", "pepsi_can", "sprite_can", 
            "lays_classic_chips", "doritos_nacho_chips",
            "snickers_bar", "mars_bar"
            # Add all your product SKUs here, normalized (lowercase, underscores)
        ])
        self.category_to_id = {sku: i for i, sku in enumerate(self.KNOWN_PRODUCT_SKUS)}
        self.num_classes = len(self.KNOWN_PRODUCT_SKUS)

        # --- OCR and Annotation ---
        self.OCR_CONFIDENCE_THRESHOLD = 0.4
        self.BBOX_EXPANSION_FACTOR = 1.5 # Heuristic to expand OCR text box to product box

        # --- Training ---
        self.TRAIN_USE_AMP = True
        self.TRAIN_SEED = 0
        self.TRAIN_NPROC_PER_NODE = 1 # Adjust based on your GPU availability (e.g., 4 for 4 GPUs)
        self.TRAIN_MASTER_PORT = "7778" # Ensure this port is free

        self._create_dirs()

    def _create_dirs(self):
        for path_attr in dir(self):
            if path_attr.endswith("_DIR") or path_attr.endswith("_PATH"):
                path_val = getattr(self, path_attr)
                if isinstance(path_val, Path) and "_CONFIG_" not in path_attr and "REPO" not in path_attr : # Don't create repo/config file paths
                    path_val.mkdir(parents=True, exist_ok=True)
        logging.info("Required directories created/ensured.")

# --- OCR Initialization ---
try:
    ocr_reader = easyocr.Reader(['en'], gpu=True) # Try to use GPU
    logging.info("EasyOCR initialized with GPU support.")
except Exception:
    ocr_reader = easyocr.Reader(['en'], gpu=False)
    logging.info("EasyOCR initialized with CPU support (GPU not available or error).")


def capture_restock_video(config: PipelineConfig, duration_sec=30, device_index=0):
    """Captures video during restocking."""
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        logging.error("Error: Cannot open camera.")
        return None

    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Using mp4v for wider compatibility
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_filename = config.RAW_VIDEO_DIR / f"restock_{timestamp}.mp4"
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 30 
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(str(video_filename), fourcc, fps, (width, height))
    
    logging.info(f"Recording to {video_filename} for {duration_sec} seconds...")
    start_time = time.time()
    while (time.time() - start_time) < duration_sec:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        # cv2.imshow('Restocking - Press Q to stop early', frame) # Uncomment for live view
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #    break
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    logging.info(f"Video saved: {video_filename}")
    return video_filename

def extract_frames_from_video(video_path: Path, config: PipelineConfig, frame_interval=30):
    """Extracts frames from video and saves them to FRAMES_DIR."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logging.error(f"Error: Cannot open video {video_path}")
        return []

    # Clear existing frames from this video's potential previous extraction in FRAMES_DIR
    # to avoid mixing if script is re-run on same video.
    # A more robust approach might be session-specific frame folders.
    video_basename = video_path.stem
    for old_frame in config.FRAMES_DIR.glob(f"{video_basename}_frame_*.jpg"):
        old_frame.unlink()

    frame_count = 0
    saved_frame_count = 0
    extracted_frame_paths = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            frame_filename = config.FRAMES_DIR / f"{video_basename}_frame_{saved_frame_count:04d}.jpg"
            cv2.imwrite(str(frame_filename), frame)
            extracted_frame_paths.append(frame_filename)
            saved_frame_count += 1
        frame_count += 1
    
    cap.release()
    logging.info(f"Extracted {saved_frame_count} frames to {config.FRAMES_DIR} from {video_path.name}")
    return extracted_frame_paths

def ocr_and_pseudo_annotate_product(image_path: Path, config: PipelineConfig):
    """
    Performs OCR. For each detected text, tries to match it to a KNOWN_PRODUCT_SKU.
    If matched, heuristically expands the text bounding box to a pseudo product bounding box.
    Returns: list of { "sku": str, "product_bbox": [xmin, ymin, xmax, ymax], "ocr_text": str }
    """
    try:
        image = cv2.imread(str(image_path))
        height, width, _ = image.shape
        results = ocr_reader.readtext(image, detail=1) # detail=1 for bbox, text, conf
        
        product_annotations = []
        for (bbox_points, text, prob) in results:
            if prob < config.OCR_CONFIDENCE_THRESHOLD:
                continue

            normalized_text = text.strip().lower().replace(" ", "_")
            matched_sku = None
            
            # Try to find the SKU in the OCR'd text
            for sku in config.KNOWN_PRODUCT_SKUS:
                if sku in normalized_text or normalized_text in sku: # Simple matching
                    matched_sku = sku
                    break
            
            if not matched_sku:
                # Attempt more fuzzy matching or log as "unrecognized_text"
                # For now, we skip if no clear SKU match based on simple substring
                logging.warning(f"OCR text '{text}' (normalized: '{normalized_text}') on {image_path.name} did not directly match any known SKUs.")
                continue

            # Text bounding box (min/max coordinates)
            all_x = [p[0] for p in bbox_points]
            all_y = [p[1] for p in bbox_points]
            text_xmin, text_ymin = min(all_x), min(all_y)
            text_xmax, text_ymax = max(all_x), max(all_y)
            
            text_center_x = (text_xmin + text_xmax) / 2
            text_center_y = (text_ymin + text_ymax) / 2
            text_w = text_xmax - text_xmin
            text_h = text_ymax - text_ymin

            # Heuristic: Expand text bbox to pseudo product bbox
            # This is a major simplification. A real system needs proper annotation tools.
            prod_w = text_w * config.BBOX_EXPANSION_FACTOR
            prod_h = text_h * config.BBOX_EXPANSION_FACTOR * 2 # Assume products are taller than text
            
            prod_xmin = max(0, int(text_center_x - prod_w / 2))
            prod_ymin = max(0, int(text_center_y - prod_h / 2))
            prod_xmax = min(width, int(text_center_x + prod_w / 2))
            prod_ymax = min(height, int(text_center_y + prod_h / 2))

            if prod_xmin < prod_xmax and prod_ymin < prod_ymax: # Valid box
                product_annotations.append({
                    "sku": matched_sku,
                    "product_bbox": [prod_xmin, prod_ymin, prod_xmax, prod_ymax],
                    "ocr_text": text
                })
        return product_annotations
    except Exception as e:
        logging.error(f"OCR/Annotation Error on {image_path.name}: {e}")
        return []

def interactive_annotation_step(image_paths: list, config: PipelineConfig):
    """
    Simulates an interactive step where an operator confirms/corrects OCR-based annotations.
    For this script, it will:
    1. Run `ocr_and_pseudo_annotate_product` for each image.
    2. Ask for simple command-line confirmation for each proposed annotation.
    3. Collect confirmed annotations.
    Returns: dict {image_path_str: [{"sku": str, "product_bbox": [x,y,w,h]}]}
    """
    logging.info("--- Starting Interactive Annotation Step (Simulated) ---")
    final_annotations_map = {}

    for img_path in image_paths:
        logging.info(f"\nProcessing image: {img_path.name}")
        # Display image (optional, requires GUI environment)
        # temp_img = cv2.imread(str(img_path))
        # cv2.imshow(f"Annotate: {img_path.name}", temp_img)
        # cv2.waitKey(100) # Give time for window to show

        proposed_annotations = ocr_and_pseudo_annotate_product(img_path, config)
        if not proposed_annotations:
            logging.warning(f"No annotations proposed for {img_path.name}.")
            continue

        confirmed_img_annotations = []
        for idx, ann in enumerate(proposed_annotations):
            print(f"  Proposed Annotation {idx+1}/{len(proposed_annotations)} for {img_path.name}:")
            print(f"    SKU (from OCR text '{ann['ocr_text']}'): {ann['sku']}")
            print(f"    Product BBox (heuristic): {ann['product_bbox']}")
            
            # In a real GUI, user would draw/adjust box here.
            # For CLI:
            user_input = input("    Confirm? (y/n/s(kip image)): ").strip().lower()
            if user_input == 'y':
                # Convert bbox from [xmin, ymin, xmax, ymax] to COCO [xmin, ymin, width, height]
                xmin, ymin, xmax, ymax = ann['product_bbox']
                width = xmax - xmin
                height = ymax - ymin
                if width > 0 and height > 0:
                    confirmed_img_annotations.append({
                        "sku": ann['sku'],
                        "bbox_coco": [xmin, ymin, width, height]
                    })
                else:
                    logging.warning("Skipping annotation with zero width/height.")
            elif user_input == 's':
                logging.info(f"Skipping remaining annotations for {img_path.name}.")
                break 
            else: # 'n' or anything else
                logging.info("Annotation rejected by user.")
        
        if confirmed_img_annotations:
            # Store relative path for COCO file_name field
            # D-FINE expects image paths relative to its specified img_folder
            relative_img_path = Path("train") / img_path.name
            final_annotations_map[str(relative_img_path)] = confirmed_img_annotations
        
        # cv2.destroyAllWindows() # If displaying images

    logging.info("--- Interactive Annotation Step Finished ---")
    return final_annotations_map

def convert_to_coco_format(confirmed_annotations_map: dict, config: PipelineConfig, output_json_path: Path):
    """
    Converts confirmed annotations to COCO JSON format.
    `confirmed_annotations_map`: {relative_image_path_str: [{"sku": str, "bbox_coco": [x,y,w,h]}]}
    """
    coco_output = {
        "images": [],
        "annotations": [],
        "categories": [{"id": config.category_to_id[sku], "name": sku, "supercategory": "product"} 
                       for sku in config.KNOWN_PRODUCT_SKUS]
    }
    annotation_id_counter = 1
    image_id_counter = 0

    for relative_img_path_str, anns_for_img in confirmed_annotations_map.items():
        # Full path to image in the temp training image directory
        full_img_path = config.TEMP_IMAGES_TRAIN_DIR / Path(relative_img_path_str).name # Ensure it's just the name under train/
        
        if not full_img_path.exists():
            logging.warning(f"Image {full_img_path} referenced in annotations not found. Skipping.")
            continue

        try:
            image = cv2.imread(str(full_img_path))
            height, width, _ = image.shape
        except Exception as e:
            logging.error(f"Could not read image {full_img_path}: {e}. Skipping.")
            continue
        
        current_image_id = image_id_counter
        coco_output["images"].append({
            "id": current_image_id,
            "file_name": relative_img_path_str, # Relative path as used by D-FINE
            "width": width,
            "height": height
        })
        image_id_counter += 1

        for ann_data in anns_for_img:
            sku = ann_data["sku"]
            if sku not in config.category_to_id:
                logging.warning(f"SKU '{sku}' in annotation for {relative_img_path_str} is not in KNOWN_PRODUCT_SKUS. Skipping.")
                continue
            
            category_id = config.category_to_id[sku]
            bbox_coco = ann_data["bbox_coco"] # [x,y,w,h]

            coco_output["annotations"].append({
                "id": annotation_id_counter,
                "image_id": current_image_id,
                "category_id": category_id,
                "bbox": bbox_coco,
                "area": bbox_coco[2] * bbox_coco[3], # width * height
                "iscrowd": 0,
                "segmentation": [] # Optional: add segmentation if available
            })
            annotation_id_counter += 1
    
    with open(output_json_path, 'w') as f:
        json.dump(coco_output, f, indent=4)
    logging.info(f"COCO annotation file created: {output_json_path} with {len(coco_output['images'])} images and {len(coco_output['annotations'])} annotations.")

def create_dfine_dataset_config(config: PipelineConfig):
    """Creates the custom_detection.yml for D-FINE."""
    dataset_config_path = config.TEMP_TRAINING_SESSION_DIR / config.DFINE_CUSTOM_DATASET_CONFIG_NAME
    
    # D-FINE expects paths relative to its own root or absolute paths.
    # Here we use absolute paths for clarity when generating the config.
    img_folder_abs = str(config.TEMP_IMAGES_TRAIN_DIR.parent.resolve()) # This should be TEMP_IMAGES_DIR
    ann_file_abs_train = str((config.TEMP_ANNOTATIONS_DIR / "instances_train.json").resolve())

    config_content = {
        "task": "detection",
        "evaluator": {"type": "CocoEvaluator", "iou_types": ['bbox']},
        "num_classes": config.num_classes,
        "remap_mscoco_category": False, # Crucial for custom datasets
        "train_dataloader": {
            "type": "DataLoader", # This structure might vary slightly based on D-FINE version
            "dataset": {
                "type": "CocoDetection",
                "img_folder": img_folder_abs, # Path to parent of 'train' dir
                "ann_file": ann_file_abs_train,
                "return_masks": False,
                "transforms": {"type": "Compose", "ops": "~"} # Keep default transforms
            },
            "shuffle": True,
            "num_workers": 4, # Adjust as needed
            "drop_last": True,
            "collate_fn": {"type": "BatchImageCollateFunction"}
        },
        # Add val_dataloader if you create a validation set
        "val_dataloader": None # Or configure similarly if you have val data
    }

    with open(dataset_config_path, 'w') as f:
        if isinstance(yaml, YAML): # ruamel.yaml
            yaml.dump(config_content, f)
        else: # PyYAML
            yaml.dump(config_content, f, sort_keys=False)
            
    logging.info(f"D-FINE dataset config created: {dataset_config_path}")
    return dataset_config_path

def create_dfine_model_config(config: PipelineConfig, dataset_config_rel_path: str):
    """
    Creates the main model config file for D-FINE (e.g., dfine_hgnetv2_n_custom.yml).
    This often includes the dataset config and other model-specific settings.
    """
    model_config_path = config.TEMP_TRAINING_SESSION_DIR / config.DFINE_CUSTOM_MODEL_CONFIG_NAME
    
    # This is a simplified example. Actual D-FINE model configs can be complex and import other YAMLs.
    # We assume a structure that includes the dataset config path.
    # The base model config (e.g., for hgnetv2_n) would be in the D-FINE repo.
    # Here, we're creating a *new* top-level config that points to our custom dataset.
    
    # Path to the dataset config, relative to the D-FINE repo's 'configs' directory,
    # or make it an absolute path if D-FINE handles that.
    # For simplicity, let's assume D-FINE can take the dataset config path from the main model config.
    # This structure is based on how RT-DETR (related project) often structures includes.
    # D-FINE's structure might be slightly different. Check its `configs/dfine/dfine_hgnetv2_*.yml` files.

    # If D-FINE model configs directly embed dataset loader info:
    base_model_config_content = f"""
include: 
  - ../dataset/{config.DFINE_CUSTOM_DATASET_CONFIG_NAME} # Path relative to this model config's location IF D-FINE resolves it this way
  # Or provide absolute path to dataset_config_file if D-FINE supports it.
  # - {str((config.TEMP_TRAINING_SESSION_DIR / config.DFINE_CUSTOM_DATASET_CONFIG_NAME).resolve())}

# Inherit from a base model config if possible (e.g., for hgnetv2 backbone)
# This part is highly dependent on D-FINE's config system.
# Example: You might copy configs/dfine/dfine_hgnetv2_n_coco.yml
# and change the dataset part and num_classes.

# Minimal overrides (ensure num_classes is set if not in dataset_config):
num_classes: {config.num_classes} 

# Add other necessary parameters expected by D-FINE for this model variant (n, s, m, l, x)
# e.g., optimizer, lr_scheduler, epochs etc. These are often in includes.
# For a simple custom run, we might just need the dataset include and num_classes if
# other defaults are acceptable from a base D-FINE config for COCO which we are adapting.

# To make this runnable, we need to define the full structure expected by train.py
# This often involves copying a standard model config (like for COCO) and modifying it.
# For now, let's assume a very simple structure that train.py might accept IF it can
# find base settings elsewhere or if the dataset config contains enough.

# A more robust way:
# 1. Copy an existing D-FINE model config (e.g., configs/dfine/dfine_hgnetv2_n_coco.yml)
# 2. Programmatically modify its 'num_classes' and the path to the 'dataset' config or its contents.
# This script will create a minimal one, assuming D-FINE's train.py is flexible or defaults exist.

model:
  type: Dfine # Or whatever the top-level model class is called in D-FINE
  backbone: # ... (details depend on D-FINE's config structure)
  neck: # ...
  head: # ...

optimizer: # Copied from a typical D-FINE config
  type: AdamW
  params:
    - params: '^(?=.*backbone)(?!.*norm|bn).*$'
      lr: 0.000025 
    - params: '^(?=.*(?:encoder|decoder))(?=.*(?:norm|bn)).*$'
      weight_decay: 0.
  lr: 0.00025 
  betas: [0.9, 0.999]
  weight_decay: 0.0001

lr_scheduler: # Copied from a typical D-FINE config
  type: CosineDecayWithWarmup
  learning_rate: 0.00025 # Should match optimizer.lr
  min_lr: 0.0000025
  warmup_steps: 500
  total_steps: 10000 # Total training steps/epochs. ADJUST THIS!

epochs: 50 # Example, adjust
log_period: 50 # Log every 50 iterations
save_dir: "output" # D-FINE will save models here, relative to its execution dir or this path.
# We will later copy the best model from D-FINE's save_dir.
    """
    # Note: The above is a highly simplified model config.
    # You MUST adapt this to match the actual structure and requirements of the D-FINE version you are using.
    # The best approach is to take an existing D-FINE config (e.g., for COCO with the 'n' model)
    # and programmatically update only the necessary parts (dataset path, num_classes).

    with open(model_config_path, 'w') as f:
        f.write(base_model_config_content) # Writing as string due to complex include/YAML features
        # If using ruamel.yaml for this, you'd need to handle includes more carefully.

    logging.info(f"D-FINE model config (simplified) created: {model_config_path}")
    return model_config_path


def run_dfine_training(config: PipelineConfig, model_config_file: Path, fine_tune_checkpoint: Path = None):
    """Executes the D-FINE training script using torchrun."""
    dfine_train_script = config.DFINE_REPO_PATH / "train.py"
    
    cmd = [
        "torchrun",
        f"--master_port={config.TRAIN_MASTER_PORT}",
        f"--nproc_per_node={config.TRAIN_NPROC_PER_NODE}",
        str(dfine_train_script),
        "-c", str(model_config_file.resolve()), # Absolute path to the model config
    ]
    if config.TRAIN_USE_AMP:
        cmd.append("--use-amp")
    if config.TRAIN_SEED is not None:
        cmd.extend(["--seed", str(config.TRAIN_SEED)])
    
    if fine_tune_checkpoint and fine_tune_checkpoint.exists():
        cmd.extend(["-t", str(fine_tune_checkpoint.resolve())]) # -t for tuning/transfer learning
        logging.info(f"Fine-tuning from checkpoint: {fine_tune_checkpoint}")
    else:
        logging.info("Training from scratch (or D-FINE's default pretrains if configured).")

    logging.info(f"Starting D-FINE training. Executing: \n{' '.join(cmd)}")
    
    try:
        # D-FINE's train.py likely saves models to an 'output' or 'work_dir'
        # specified in its config or by default. We need to find it.
        # Execute from D-FINE_REPO_PATH so relative paths in configs work as expected by D-FINE
        process = subprocess.Popen(cmd, cwd=str(config.DFINE_REPO_PATH), 
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Stream output
        for line in iter(process.stdout.readline, ''):
            print(line, end='') # Print D-FINE's output in real-time
        
        process.wait() # Wait for training to complete
        
        if process.returncode == 0:
            logging.info("D-FINE training process completed successfully.")
            # Find the output directory (often 'output' or 'work_dir' inside DFINE_REPO_PATH, or as specified in config)
            # This needs to align with what's in the D-FINE model_config's 'save_dir'
            dfine_output_dir = config.DFINE_REPO_PATH / "output" # Assuming this is the default
            # If model_config has a different save_dir, parse it.
            # For simplicity, we assume "output".
            
            # Find the latest .pth file (model checkpoint)
            trained_models = list(dfine_output_dir.glob("**/*.pth"))
            if not trained_models:
                logging.warning(f"No .pth model files found in D-FINE output directory: {dfine_output_dir}")
                return None
            
            latest_model = max(trained_models, key=lambda p: p.stat().st_mtime)
            logging.info(f"Latest trained model found: {latest_model}")
            
            # Copy to our central model directory
            final_model_name = f"{config.DFINE_CUSTOM_MODEL_CONFIG_NAME.split('.')[0]}_{datetime.now().strftime('%Y%m%d%H%M')}.pth"
            destination_model_path = config.MODEL_OUTPUT_DIR / final_model_name
            shutil.copy(latest_model, destination_model_path)
            logging.info(f"Trained model copied to: {destination_model_path}")
            return destination_model_path
        else:
            logging.error(f"D-FINE training process failed with return code {process.returncode}.")
            return None

    except FileNotFoundError:
        logging.error(f"torchrun or D-FINE train.py not found. Ensure paths are correct and environment is set up.")
        return None
    except Exception as e:
        logging.error(f"An error occurred during D-FINE training: {e}")
        return None

def main_pipeline(config: PipelineConfig, mode="full_retrain"): # mode can be "full_retrain" or "collect_annotate_only"
    """Main pipeline for restocking, annotating, and training."""
    logging.info("=== Starting 'Restock-and-Train' Pipeline V2 ===")

    # --- 1. Cleanup and Prepare Training Session Directory ---
    if config.TEMP_TRAINING_SESSION_DIR.exists():
        logging.info(f"Cleaning up old temporary training session data: {config.TEMP_TRAINING_SESSION_DIR}")
        shutil.rmtree(config.TEMP_TRAINING_SESSION_DIR)
    config.TEMP_TRAINING_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    config.TEMP_IMAGES_TRAIN_DIR.mkdir(parents=True, exist_ok=True)
    config.TEMP_ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

    # --- 2. Data Acquisition (Video or Pre-existing Frames) ---
    # For this example, let's assume we work with pre-existing frames in config.FRAMES_DIR
    # To use video capture:
    # video_file = capture_restock_video(config, duration_sec=20)
    # if not video_file: return
    # image_paths_for_annotation = extract_frames_from_video(video_file, config, frame_interval=10)
    
    # Using pre-existing frames for demonstration:
    # Copy some sample images to config.FRAMES_DIR before running if you don't capture video.
    # e.g., shutil.copy("path/to/my_product_image.jpg", config.FRAMES_DIR / "my_product_image.jpg")
    image_paths_for_annotation = list(config.FRAMES_DIR.glob("*.jpg")) + list(config.FRAMES_DIR.glob("*.png"))
    if not image_paths_for_annotation:
        logging.error(f"No images found in {config.FRAMES_DIR} for annotation. Please add some or capture video.")
        return
    logging.info(f"Found {len(image_paths_for_annotation)} images for annotation in {config.FRAMES_DIR}")

    # Copy selected frames to the temporary training image directory
    for img_path in image_paths_for_annotation:
        shutil.copy(img_path, config.TEMP_IMAGES_TRAIN_DIR / img_path.name)
    
    # --- 3. Interactive Annotation ---
    # The paths passed to interactive_annotation_step should be those in TEMP_IMAGES_TRAIN_DIR
    # to ensure relative paths in COCO are correct.
    temp_image_paths_for_annotation = [config.TEMP_IMAGES_TRAIN_DIR / p.name for p in image_paths_for_annotation]
    confirmed_annotations = interactive_annotation_step(temp_image_paths_for_annotation, config)
    
    if not confirmed_annotations:
        logging.error("No annotations were confirmed. Cannot proceed with training.")
        return

    # --- 4. Convert Annotations to COCO Format ---
    coco_json_path = config.TEMP_ANNOTATIONS_DIR / "instances_train.json"
    convert_to_coco_format(confirmed_annotations, config, coco_json_path)

    if mode == "collect_annotate_only":
        logging.info("Mode is 'collect_annotate_only'. Training will be skipped.")
        logging.info(f"Annotated data prepared in: {config.TEMP_TRAINING_SESSION_DIR}")
        return

    # --- 5. Prepare D-FINE Configuration Files ---
    dataset_config_file = create_dfine_dataset_config(config)
    # The path to dataset_config_file needs to be correctly referenced in model_config_file
    # This depends on D-FINE's include logic (relative to model_config or repo's config dir)
    # For simplicity, we'll assume the model config will be in TEMP_TRAINING_SESSION_DIR
    # and can reference the dataset config also in TEMP_TRAINING_SESSION_DIR.
    model_config_file = create_dfine_model_config(config, dataset_config_file.name)

    # --- 6. Run D-FINE Training ---
    # Optionally, find the latest existing model to fine-tune from
    existing_models = list(config.MODEL_OUTPUT_DIR.glob("*.pth"))
    fine_tune_from = None
    if existing_models:
        fine_tune_from = max(existing_models, key=lambda p: p.stat().st_mtime)
        logging.info(f"Found existing model to potentially fine-tune from: {fine_tune_from}")
    
    trained_model_path = run_dfine_training(config, model_config_file, fine_tune_checkpoint=fine_tune_from)

    if trained_model_path and trained_model_path.exists():
        logging.info(f"=== Pipeline Completed Successfully. Trained model at: {trained_model_path} ===")
    else:
        logging.error("=== Pipeline Failed. See logs for details. ===")


if __name__ == "__main__":
    # IMPORTANT: Replace with the actual path to your cloned D-FINE (or DEIM) repository
    DFINE_REPO_PATH = "/path/to/your/D-FINE" # e.g., "/home/user/projects/D-FINE"
    
    if DFINE_REPO_PATH == "/path/to/your/D-FINE":
        print("ERROR: Please update DFINE_REPO_PATH in the __main__ block of the script.")
    else:
        pipeline_config = PipelineConfig(dfine_repo_path=DFINE_REPO_PATH, base_data_dir="my_vending_machine_data")
        
        # Before running:
        # 1. Ensure DFINE_REPO_PATH is correct.
        # 2. Place some sample product images (e.g., coke.jpg, chips.jpg) into 
        #    "my_vending_machine_data/training_frames/" for the script to find.
        # 3. Update `pipeline_config.KNOWN_PRODUCT_SKUS` with your actual product SKUs.
        # 4. Review the D-FINE model config creation part to ensure it matches your D-FINE version's requirements.
        
        main_pipeline(pipeline_config)
        # To only collect and annotate data without training:
        # main_pipeline(pipeline_config, mode="collect_annotate_only")