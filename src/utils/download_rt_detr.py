"""
Download and save RT-DETR model from HuggingFace
"""
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create model directory if it doesn't exist
model_dir = os.path.join("src", "models", "rtdetr")
os.makedirs(model_dir, exist_ok=True)

# Download and save model and processor
print("Downloading RT-DETR model...")
model = RTDetrV2ForObjectDetection.from_pretrained(
    "PekingU/rtdetr_v2_r18vd",
    token=os.getenv("HF_TOKEN")
)
processor = RTDetrImageProcessor.from_pretrained(
    "PekingU/rtdetr_v2_r18vd",
    token=os.getenv("HF_TOKEN")
)

print("Saving model to disk...")
model.save_pretrained(model_dir)
processor.save_pretrained(model_dir)

print(f"Model successfully saved to {model_dir}")
