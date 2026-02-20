import base64
import io
import csv
import numpy as np
import torch
from transformers import Sam3VideoModel, Sam3VideoProcessor
from accelerate import Accelerator
import cv2 as cv
import time
from transformers.video_utils import load_video
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Class to handle all SAM3 video segmentation logic
class Sam3VideoSegmenter:
    # Initialize the segmenter with model loading and processing device
    def __init__(self, model_id="facebook/sam3", target_size=512):
        if not torch.cuda.is_available():
            print("IMPORTANT: GPU not detected in this environment!")
            print("SAM 3 will be extremely slow or stuck on CPU and GUI can crash!!!!")
            
        self.device = Accelerator().device
        self.MODEL_ID = model_id
        self.DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        self.DTYPE = torch.bfloat16
        self.TARGET_SIZE = target_size

        print(f"Supported Architectures: {torch.cuda.get_arch_list()}")
        # Load model
        self.model = Sam3VideoModel.from_pretrained(self.MODEL_ID).to(
            self.DEVICE, dtype=self.DTYPE
        ).eval()
        self.processor = Sam3VideoProcessor.from_pretrained(self.MODEL_ID)
        print("Successfully loaded model.")
        
        self.video_frames = None
        self.video_frames_original_size = None
        self.inference_session = None
        self.mask_areas = []
    
    # Funtion to load video 
    def load_video(self, video_path):
        # load video frames and store original and resized
        self.video_frames_original_size, _ = load_video(video_path)
        video_frames, _ = load_video(video_path)
        resized_frames = []
        
        # Resize frames 
        for frame in video_frames:
            h, w = frame.shape[:2]
            scale = self.TARGET_SIZE / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv.resize(frame, (new_w, new_h), interpolation=cv.INTER_AREA)
            resized_frames.append(resized)

        self.video_frames = resized_frames

        # Initialize sam3 inference session with video frames
        self.inference_session = self.processor.init_video_session(
            video=self.video_frames,
            inference_device=self.device,
            dtype=torch.bfloat16,
        )

        print(type(self.video_frames))
        print(type(self.inference_session))

    # Function to add text prompt to sam3 session
    def add_text_prompt(self, text_prompt):
        self.processor.add_text_prompt(
            inference_session=self.inference_session,
            text=text_prompt,
        )

    # Function to process a single frame
    def showSingleFrame(self, frame_idx, return_frame_only=False):
        with torch.no_grad():
            # Run inference for the specified frame index
            model_outputs = self.model(
                inference_session=self.inference_session,
                frame_idx=frame_idx,
            )

            # Postprocess outputs to get masks
            processed_outputs = self.processor.postprocess_outputs(
                self.inference_session,
                model_outputs
            )

            # Store the processed outputs for this frame
            frame_output = processed_outputs
            
            # Get the original size frame for display
            frame = self.video_frames_original_size[frame_idx].copy()
            h, w = frame.shape[:2]

            # Check if any masks were detected and create overlay
            if len(frame_output["masks"]) > 0:
                raw_mask = frame_output["masks"][0].detach().cpu().numpy().astype("uint8") * 255
                
                mask_resized = cv.resize(raw_mask, (w, h), interpolation=cv.INTER_NEAREST)
                
                frame[mask_resized == 255] = [0, 255, 0]  
            else:
                print(f"No masks detected for frame {frame_idx}")
            
            # Return frame if requested; otherwise show the frame with cv2
            frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            if return_frame_only:
                return frame_rgb

            cv.imshow("High Res Mask", frame_rgb)
            cv.waitKey(0)
            cv.destroyAllWindows()
    
    # Function to run sam3 propagation across the entire video 
    def propagate_video(self, show_live=False, status_callback=None):
        if self.video_frames is None:
            raise ValueError("Load a video first.")

        self.mask_areas = []
        self.processed_frames = [] 
        self.mask_data_storage = [] 
        total_frames = len(self.video_frames)
        start_time = time.time()

        # Iterate through video 
        for i, model_outputs in enumerate(self.model.propagate_in_video_iterator(self.inference_session), 1):
            frame_idx = model_outputs.frame_idx
            processed_outputs = self.processor.postprocess_outputs(self.inference_session, model_outputs)
            
            # Use resized frame for display and calculation
            current_frame = self.video_frames[frame_idx].copy()
            h, w = current_frame.shape[:2]

            mask_area = 0
            
            # Default empty values for frames with no squirrel detected
            x_min, y_min, x_max, y_max = "", "", "", ""

            # Check if any mask was detected in this frame
            if processed_outputs["masks"].numel() > 0:
                # Extract binary mask
                mask = processed_outputs["masks"][0].detach().cpu().numpy().astype("uint8")
                
                # Calculate area of mask
                mask_area = int(np.sum(mask > 0))

                #Calculate BBox
                y_coords, x_coords = np.where(mask > 0)
                if len(x_coords) > 0:
                    x_min, x_max = int(np.min(x_coords)), int(np.max(x_coords))
                    y_min, y_max = int(np.min(y_coords)), int(np.max(y_coords))

                # Create overlay
                overlay = current_frame.copy()
                overlay[mask > 0] = [0, 255, 0]
                current_frame = cv.addWeighted(overlay, 0.5, current_frame, 0.5, 0)

            # Store frame and the metadata for the CSV
            self.mask_areas.append(mask_area)
            self.processed_frames.append(current_frame)
            self.mask_data_storage.append({
                "idx": frame_idx, 
                "w": w, 
                "h": h, 
                "x1": x_min, 
                "y1": y_min, 
                "x2": x_max, 
                "y2": y_max
            })

            # Show live video if enabled
            if show_live:
                cv.imshow("Segmented Video", current_frame)
                if cv.waitKey(1) & 0xFF == ord('q'):
                    break

            # Calculate and send status text to UI (first Bridge)
            elapsed = time.time() - start_time
            avg_per_frame = elapsed / i
            remaining_time = avg_per_frame * (total_frames - i)
            status_text = (
                f"Frame {i}/{total_frames} processed. "
                f"Elapsed: {elapsed:.1f}s, Remaining: {remaining_time:.1f}s"
            )
            
            if status_callback:
                status_callback(status_text)

        cv.destroyAllWindows()
        print("\nFinished processing all frames")
        return self.processed_frames
    
    # Function to generate graph image from mask area data and return base64 URL
    def generate_graph_image(self, chart_data):
        if not chart_data or len(chart_data) == 0:
            return None

        # Create graph
        fig, ax = plt.subplots(figsize=(14, 4), dpi=1000) 
        fig.patch.set_facecolor('#313244')
        ax.set_facecolor('#313244')
        ax.plot(chart_data, color="#f38ba8", linewidth=3, antialiased=True)
        ax.fill_between(range(len(chart_data)), chart_data, color="#f38ba8", alpha=0.15)
        ax.set_xlabel("Video Frame", color="#cdd6f4", fontsize=17, fontweight='bold', labelpad=12)
        ax.set_ylabel("Masked Pixels", color="#cdd6f4", fontsize=17, fontweight='bold', labelpad=12)
        ax.tick_params(axis='both', colors='#a6adc8', labelsize=15)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=8))

        for spine in ax.spines.values():
            spine.set_edgecolor('#45475a')
            spine.set_linewidth(2.0)

        ax.grid(True, linestyle=':', alpha=0.2, color="#cdd6f4")

        plt.tight_layout(pad=1.5)

        # Save graph to buffer and encode as base64 
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"
    
    # Function to export graph data to CSV
    def export_graph_csv(self, output_path):
        if not hasattr(self, "mask_areas") or not self.mask_areas:
            print("No data to export.")
            return False

        # writing CSV file with frame index and mask pixel area
        try:
            with open(output_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Frame", "Masked_Pixels"])
                for idx, area in enumerate(self.mask_areas):
                    writer.writerow([idx, area])
            print(f"CSV exported successfully to {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False

    # Function to export mask data (frame index, frame dimensions and bbox)to CSV
    def export_mask_csv(self, output_path):
        if not hasattr(self, "mask_data_storage") or not self.mask_data_storage:
            print("Error: No data to export. Please run 'Propagate Video' first.")
            return False

        # writing CSV with frame index, frame dimensions, and bbox
        try:
            with open(output_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["frame_idx", "width", "height", "x_min", "y_min", "x_max", "y_max"])
                for data in self.mask_data_storage:
                    writer.writerow([
                        data["idx"], 
                        data["w"], 
                        data["h"], 
                        data["x1"], 
                        data["y1"], 
                        data["x2"], 
                        data["y2"]
                    ])
            print(f"Successfully exported {len(self.mask_data_storage)} frames to {output_path}")
            return True
        except Exception as e:
            print(f"CSV Export Error: {e}")
            return False
        
    # Function to export processed video frames as MP4
    def export_video(self, frames, output_path, fps=30): # Add 'frames' here
        if not frames:
            print("Error: No frames provided for export.")
            return False

        # write video using cv2
        try:
            h, w = frames[0].shape[:2]
            
            fourcc = cv.VideoWriter_fourcc(*'mp4v')
            writer = cv.VideoWriter(output_path, fourcc, fps, (w, h))

            for frame in frames:
                writer.write(cv.cvtColor(frame, cv.COLOR_RGB2BGR))

            writer.release()
            print(f"Video exported successfully to {output_path}")
            return True
        
        except Exception as e:
            print(f"Failed to export video: {e}")
            return False
        