import base64
import io
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

        
    def propagate_video1(self, output_path=None):
        writer = None
        if output_path is not None:
            h, w = self.video_frames[0].shape[:2]
            writer = cv.VideoWriter(
                output_path,
                cv.VideoWriter_fourcc(*"mp4v"),
                30,
                (w, h)
            )

        total_frames = len(self.video_frames)
        start_time = time.time()

        for i, model_outputs in enumerate(
                self.model.propagate_in_video_iterator(self.inference_session), 1):

            frame_idx = model_outputs.frame_idx

            processed_outputs = self.processor.postprocess_outputs(
                self.inference_session,
                model_outputs
            )

            frame = self.video_frames[frame_idx].copy()

            if processed_outputs["masks"].numel() > 0:
                mask = processed_outputs["masks"][0].detach().cpu().numpy().astype("uint8") * 255

                overlay = frame.copy()
                overlay[mask == 255] = [0, 255, 0]
                alpha = 0.5
                frame = cv.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

            if cv.waitKey(1) & 0xFF == ord('q'):
                break

            if writer is not None:
                writer.write(frame)

            elapsed = time.time() - start_time
            avg_per_frame = elapsed / i
            remaining_time = avg_per_frame * (total_frames - i)
            print(
                f"Frame {i}/{total_frames} processed. "
                f"Elapsed: {elapsed:.1f}s, "
                f"Estimated remaining: {remaining_time:.1f}s",
                end="\r"
            )

        cv.destroyAllWindows()
        if writer is not None:
            writer.release()

        print("\nFinished processing all frames")
    
    def propagate_video(self, show_live=False, status_callback=None): # Add status_callback
        if self.video_frames is None:
            raise ValueError("Load a video first.")

        self.mask_areas = []
        processed_frames = []
        total_frames = len(self.video_frames)
        start_time = time.time()

        for i, model_outputs in enumerate(self.model.propagate_in_video_iterator(self.inference_session), 1):
            frame_idx = model_outputs.frame_idx
            processed_outputs = self.processor.postprocess_outputs(self.inference_session, model_outputs)
            frame = self.video_frames[frame_idx].copy()

            mask_area = 0
            if processed_outputs["masks"].numel() > 0:
                mask = processed_outputs["masks"][0].detach().cpu().numpy().astype("uint8") * 255
                mask_area = np.sum(mask > 0)

                overlay = frame.copy()
                overlay[mask == 255] = [0, 255, 0]
                alpha = 0.5
                frame = cv.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

            self.mask_areas.append(mask_area)
            processed_frames.append(frame)

            if show_live:
                cv.imshow("Segmented Video", frame)
                if cv.waitKey(1) & 0xFF == ord('q'):
                    break

            elapsed = time.time() - start_time
            avg_per_frame = elapsed / i
            remaining_time = avg_per_frame * (total_frames - i)
            
            # --- Keep your original print logic ---
            status_text = (
                f"Frame {i}/{total_frames} processed. "
                f"Elapsed: {elapsed:.1f}s, "
                f"Remaining: {remaining_time:.1f}s"
            )
            print(status_text, end="\r")

            # --- New: Send the same text to the UI callback ---
            if status_callback:
                status_callback(status_text)

        cv.destroyAllWindows()
        print("\nFinished processing all frames")
        return processed_frames
    
    

    def export_video(self, frames, output_path, fps=30):
        if not frames:
            raise ValueError("No frames to export")
        h, w = frames[0].shape[:2]
        writer = cv.VideoWriter(
            output_path,
            cv.VideoWriter_fourcc(*"mp4v"),
            fps,
            (w, h)
        )
        for frame in frames:
            writer.write(frame)
        writer.release()
        print(f"Video exported to {output_path}")

    def generate_graph(self):
        if not hasattr(self, "mask_areas") or not self.mask_areas:
            return [], 0.0

        data = self.mask_areas
        max_val = max(data) if data else 1.0
        return data, max_val
    
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

    def export_graph_csv(self, output_path):
        """Exports the mask_areas data to a CSV file."""
        if not hasattr(self, "mask_areas") or not self.mask_areas:
            print("No data to export.")
            return False

        try:
            import csv
            with open(output_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                # Header
                writer.writerow(["Frame", "Masked_Pixels"])
                # Data
                for idx, area in enumerate(self.mask_areas):
                    writer.writerow([idx, area])
            print(f"CSV exported successfully to {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False

