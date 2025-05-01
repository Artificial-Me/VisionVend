import os
import time
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import cv2

class BiRefNetInference:
    def __init__(self, model_name='BiRefNet', device='cpu'):
        """
        Initialize BiRefNet model for Raspberry Pi inference.
        
        Args:
            model_name (str): Name of the model variant
            device (str): Computation device ('cpu' for Raspberry Pi)
        """
        print(f"Initializing BiRefNet on {device}...")
        
        # Ensure reproducibility and consistent performance
        torch.manual_seed(42)
        
        # Load model
        self.model = torch.hub.load('ZhengPeng7/BiRefNet', model_name, pretrained=True, trust_repo=True)
        self.model.to(device)
        self.model.eval()
        
        # Device configuration
        self.device = device
        
        # Image transformation pipeline
        self.transform = transforms.Compose([
            transforms.Resize((384, 384)),  # Balanced size for RPi
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        print("BiRefNet model initialized successfully.")

    def preprocess_image(self, image_path):
        """
        Preprocess input image for model inference.
        
        Args:
            image_path (str): Path to input image
        
        Returns:
            torch.Tensor: Preprocessed image tensor
            tuple: Original image size
        """
        try:
            # Use PIL for initial loading to preserve color space
            original_image = Image.open(image_path).convert('RGB')
            original_size = original_image.size
            
            # Apply transformations
            input_tensor = self.transform(original_image).unsqueeze(0)
            
            return input_tensor, original_size
        
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return None, None

    def run_inference(self, input_tensor):
        """
        Run model inference on preprocessed image.
        
        Args:
            input_tensor (torch.Tensor): Preprocessed image tensor
        
        Returns:
            torch.Tensor: Saliency/segmentation map
        """
        try:
            start_time = time.time()
            
            with torch.no_grad():
                outputs = self.model(input_tensor)
                # Assuming the last output is the primary saliency map
                saliency_map = outputs[-1].sigmoid()
            
            inference_time = time.time() - start_time
            print(f"Inference completed in {inference_time:.2f} seconds")
            
            return saliency_map
        
        except Exception as e:
            print(f"Inference error: {e}")
            return None

    def postprocess_output(self, saliency_map, original_size):
        """
        Convert saliency map to a processable format.
        
        Args:
            saliency_map (torch.Tensor): Raw saliency map
            original_size (tuple): Original image dimensions
        
        Returns:
            numpy.ndarray: Processed saliency mask
        """
        try:
            # Remove batch dimension and convert to numpy
            saliency_np = saliency_map.squeeze().cpu().numpy()
            
            # Normalize to 0-255 range
            saliency_np = (saliency_np * 255).astype(np.uint8)
            
            # Resize to original image size
            saliency_resized = cv2.resize(saliency_np, original_size[::-1], 
                                           interpolation=cv2.INTER_LINEAR)
            
            return saliency_resized
        
        except Exception as e:
            print(f"Postprocessing error: {e}")
            return None

    def process_image(self, input_image_path, output_mask_path=None):
        """
        Complete pipeline: preprocess, inference, and postprocess.
        
        Args:
            input_image_path (str): Path to input image
            output_mask_path (str, optional): Path to save output mask
        
        Returns:
            numpy.ndarray: Processed saliency mask
        """
        # Preprocess
        input_tensor, original_size = self.preprocess_image(input_image_path)
        
        if input_tensor is None:
            return None
        
        # Inference
        saliency_map = self.run_inference(input_tensor)
        
        if saliency_map is None:
            return None
        
        # Postprocess
        mask = self.postprocess_output(saliency_map, original_size)
        
        # Save mask if path provided
        if output_mask_path and mask is not None:
            cv2.imwrite(output_mask_path, mask)
            print(f"Mask saved to {output_mask_path}")
        
        return mask

def main():
    # Example usage
    input_image = 'input.jpg'
    output_mask = 'output_mask.png'
    
    # Initialize BiRefNet for Raspberry Pi (CPU)
    birefnet = BiRefNetInference(device='cpu')
    
    # Process image
    birefnet.process_image(input_image, output_mask)

if __name__ == "__main__":
    main()
