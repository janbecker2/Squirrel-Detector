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

class Sam3VideoSegmenter:
    def __init__(self, model_id="facebook/sam3", target_size=512):
        print("Successfully imported libaries.")

        self.device = Accelerator().device
        self.MODEL_ID = model_id
        self.DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        self.DTYPE = torch.bfloat16
        self.TARGET_SIZE = target_size

        # Load model
        self.model = Sam3VideoModel.from_pretrained(self.MODEL_ID).to(
            self.DEVICE, dtype=self.DTYPE
        ).eval()
        self.processor = Sam3VideoProcessor.from_pretrained(self.MODEL_ID)
        print("Successfully loaded models.")
        
        self.video_frames = None
        self.video_frames_original_size = None
        self.inference_session = None
        self.mask_areas = []
    
    video_frames_original_size = None
    def load_video(self, video_path):
        # Load video
        self.video_frames_original_size, _ = load_video(video_path)
        video_frames, _ = load_video(video_path)

        resized_frames = []
        for frame in video_frames:
            h, w = frame.shape[:2]

            scale = self.TARGET_SIZE / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)

            resized = cv.resize(frame, (new_w, new_h), interpolation=cv.INTER_AREA)
            resized_frames.append(resized)

        self.video_frames = resized_frames

        # Initialize inference session
        self.inference_session = self.processor.init_video_session(
            video=self.video_frames,
            inference_device=self.device,
            dtype=torch.bfloat16,
        )

        print(type(self.video_frames))
        print(type(self.inference_session))

    def add_text_prompt(self, text_prompt):
        self.processor.add_text_prompt(
            inference_session=self.inference_session,
            text=text_prompt,
        )

    def showSingleFrame(self, frame_idx, return_frame_only=False):
        model_outputs = self.model(
            inference_session=self.inference_session,
            frame_idx=frame_idx,
        )

        processed_outputs = self.processor.postprocess_outputs(
            self.inference_session,
            model_outputs
        )

        frame_output = processed_outputs
        
        frame = self.video_frames_original_size[frame_idx].copy()
        h, w = frame.shape[:2]

        if len(frame_output["masks"]) > 0:
            raw_mask = frame_output["masks"][0].detach().cpu().numpy().astype("uint8") * 255
            
            mask_resized = cv.resize(raw_mask, (w, h), interpolation=cv.INTER_NEAREST)
            
            frame[mask_resized == 255] = [0, 255, 0]  # Green overlay
        else:
            print(f"No masks detected for frame {frame_idx}")
            
        if return_frame_only:
            frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            return frame_rgb

        cv.imshow("High Res Mask", frame)
        cv.waitKey(0)
        cv.destroyAllWindows()
    
    def propagate_video(self, show_live=False, status_callback=None):
        if self.video_frames is None:
            raise ValueError("Load a video first.")

        # Initialize storage containers
        self.mask_areas = []
        self.processed_frames = [] 
        self.mask_data_storage = [] # To store training coordinates
        
        total_frames = len(self.video_frames)
        start_time = time.time()

        # Iterate through the video using the SAM3 session
        for i, model_outputs in enumerate(self.model.propagate_in_video_iterator(self.inference_session), 1):
            frame_idx = model_outputs.frame_idx
            processed_outputs = self.processor.postprocess_outputs(self.inference_session, model_outputs)
            
            # Use the resized frame for calculations
            current_frame = self.video_frames[frame_idx].copy()
            h, w = current_frame.shape[:2]

            mask_area = 0
            x_str, y_str = "", "" # Default empty strings for frames with no squirrel

            # Check if any mask was detected in this frame
            if processed_outputs["masks"].numel() > 0:
                # Extract binary mask (0 or 1)
                mask = processed_outputs["masks"][0].detach().cpu().numpy().astype("uint8")
                
                # 1. Calculate Area (sum of all True/1 pixels)
                mask_area = int(np.sum(mask > 0))

                # 2. Extract Training Coordinates (X;Y)
                y_coords, x_coords = np.where(mask > 0)
                if len(x_coords) > 0:
                    x_str = ";".join(map(str, x_coords))
                    y_str = ";".join(map(str, y_coords))

                # 3. Create Visual Overlay for UI
                overlay = current_frame.copy()
                overlay[mask > 0] = [0, 255, 0] # Green tint
                current_frame = cv.addWeighted(overlay, 0.5, current_frame, 0.5, 0)

            # Store results in instance variables
            self.mask_areas.append(mask_area)
            self.processed_frames.append(current_frame)
            self.mask_data_storage.append({
                "idx": frame_idx, 
                "w": w, 
                "h": h, 
                "x": x_str, 
                "y": y_str
            })

            # Handle Live View (Optional)
            if show_live:
                cv.imshow("Segmented Video", current_frame)
                if cv.waitKey(1) & 0xFF == ord('q'):
                    break

            # Calculate and send status updates
            elapsed = time.time() - start_time
            avg_per_frame = elapsed / i
            remaining_time = avg_per_frame * (total_frames - i)
            
            status_text = (
                f"Frame {i}/{total_frames} processed. "
                f"Elapsed: {elapsed:.1f}s, "
                f"Remaining: {remaining_time:.1f}s"
            )
            
            if status_callback:
                status_callback(status_text)

        cv.destroyAllWindows()
        return self.processed_frames
    
    def generate_graph_image(self, chart_data):
        if not chart_data or len(chart_data) == 0:
            return None

        import matplotlib
        matplotlib.use('Agg') 
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker

        # 1. High DPI (160+) ensures the larger text stays crisp and doesn't pixelate
        fig, ax = plt.subplots(figsize=(14, 4), dpi=1000) 
        
        fig.patch.set_facecolor('#313244')
        ax.set_facecolor('#313244')

        ax.plot(chart_data, color="#f38ba8", linewidth=3, antialiased=True)
        ax.fill_between(range(len(chart_data)), chart_data, color="#f38ba8", alpha=0.15)

        # 2. BOLD and LARGE Labels
        # Increased fontsize to 14 for the main axis titles
        ax.set_xlabel("Video Frame", color="#cdd6f4", fontsize=17, fontweight='bold', labelpad=12)
        ax.set_ylabel("Masked Pixels", color="#cdd6f4", fontsize=17, fontweight='bold', labelpad=12)
        
        # 3. LARGE Tick Labels
        # Increased labelsize to 12 for the numbers on the axes
        ax.tick_params(axis='both', colors='#a6adc8', labelsize=15)
        
        # Use a clean locator to keep the larger numbers from overlapping
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=8))

        # 4. Thicker Spines to match the larger text weight
        for spine in ax.spines.values():
            spine.set_edgecolor('#45475a')
            spine.set_linewidth(2.0)

        ax.grid(True, linestyle=':', alpha=0.2, color="#cdd6f4")

        # 5. Added extra padding in tight_layout to accommodate larger fonts
        plt.tight_layout(pad=1.5)

        buf = io.BytesIO()
        # bbox_inches='tight' is critical here so the larger text doesn't get clipped
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"

    def export_mask_csv(self, output_path):
        """
        Saves the coordinates collected during propagation to a CSV.
        """
        if not hasattr(self, "mask_data_storage") or not self.mask_data_storage:
            print("No mask data found. Run propagate_video first.")
            return False

        try:
            with open(output_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                # Header compatible with typical ML training scripts
                writer.writerow(["frame_idx", "width", "height", "x_points", "y_points"])

                for data in self.mask_data_storage:
                    writer.writerow([data["idx"], data["w"], data["h"], data["x"], data["y"]])
            
            print(f"Exported {len(self.mask_data_storage)} frames to {output_path}")
            return True
        except Exception as e:
            print(f"CSV Export Error: {e}")
            return False