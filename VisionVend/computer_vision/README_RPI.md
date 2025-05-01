# BiRefNet on Raspberry Pi

## Prerequisites

1. **Recommended OS**: 64-bit Raspberry Pi OS (Bullseye or later)
2. **Python Version**: Python 3.9+ (recommended)

## Installation Steps

### 1. Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Build Dependencies
```bash
sudo apt install -y build-essential cmake libpython3-dev python3-dev
sudo apt install -y libopenblas-dev libopenjp2-7 libavcodec-dev libavformat-dev libswscale-dev
```

### 3. Create Virtual Environment
```bash
python3 -m venv birefnet_env
source birefnet_env/bin/activate
```

### 4. Install PyTorch (64-bit OS)
```bash
pip install torch torchvision --extra-index-url https://torch.csail.mit.edu/whl/cpu/
```

### 5. Install Project Dependencies
```bash
pip install -r requirements_rpi.txt
```

## Running the Script
```bash
python rpi_birefnet_inference.py
```

## Performance Notes
- Inference will be significantly slower compared to GPU
- Recommended input image size: 384x384
- Monitor RAM usage during processing

## Troubleshooting
- Ensure you're using a 64-bit OS
- Check Python and pip versions
- Verify all dependencies are correctly installed
