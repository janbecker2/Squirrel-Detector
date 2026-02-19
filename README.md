# Squirrel Detector

A desktop video segmentation application powered by SAM3 (Segment Anything Model 3).  
Built with PySide6 (Qt/QML) and Python, this application allows users to:

- Load a video
- Segment an object (e.g., a squirrel) across frames
- Visualize mask area changes over time
- Export graph data (CSV)
- Export processed video with mask
- Export mask data

---

## Overview

Squirrel-App combines a modern QML-based UI with a Python backend that performs AI-based video segmentation.

---

## Features

- Frame-by-frame video viewer
- AI-based segmentation with propagation
- Automatic mask-area graph generation
- CSV export of graph data
- Processed video export
- Splash screen with animated transition
- Background threading for heavy AI tasks
- Live status updates during processing

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

## Requirements

- Python 3.10+
- PySide6
- torch
- torchvsion
- transformers
- accelerate
- opencv-python
- matplotlib
- numpy

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/janbecker2/Squirrel-App.git
cd Squirrel-App
```
### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
python main.py
```
