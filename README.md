# Squirrel Detector

A desktop video segmentation application powered by SAM3 (Segment Anything Model 3).  
Built with PySide6 (Qt/QML) and Python, this application allows users to:

- Load a video
- Segment squirrels across frames
- Visualize mask area changes over time
- Export graph data (CSV)
- Export processed video with mask
- Export mask data

---

## Overview

Squirrel-App combines a modern QML-based UI with a Python backend that performs AI-based video segmentation.

---

---

## Project Structure
```bash
Squirrel-App/
│
├── UI/
│ ├── main.qml
│ └── assets/
│
├── splash.py
├── sam3_segmenter.py
├── main.py
├── requirements.txt
└── README.md
```

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/janbecker2/Squirrel-App.git
cd Squirrel-App
```
### 2. Install dependencies
```bash
# If you have an RTX 50-series GPU or SAM3 does not run on your GPU, install the compatible PyTorch build first:
pip install --pre --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128

# Then install the remaining dependencies:
pip install -r requirements.txt
```

### 4. Set up Hugging Face Authentication
Create a .env file in the root directory and add your Hugging Face API token:
```bash
HF_TOKEN="your_hugginface_api_key"
```
The application will automatically authenticate with Hugging Face when it starts.

You can generate a token here:
https://huggingface.co/settings/tokens

Note: Make sure you have requested and been granted access to the required model repository before generating your token.

### 5. Run the application
```bash
python main.py
```
