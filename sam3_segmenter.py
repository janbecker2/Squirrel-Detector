import numpy as np
import torch
from transformers import Sam3VideoModel, Sam3VideoProcessor
from accelerate import Accelerator
import cv2 as cv
import time
from PySide6.QtGui import QImage
from transformers.video_utils import load_video


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
        
    def load_video(self, video_path):
        # Load video
        video_frames_original_size, _ = load_video(video_path)
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

        output = {frame_idx: processed_outputs}
        frame_output = output[frame_idx]

        frame = self.video_frames[frame_idx].copy()  # start with original frame

        # check if any masks exist
        if len(frame_output["masks"]) > 0:
            # apply the first mask
            mask = frame_output["masks"][0].detach().cpu().numpy().astype("uint8") * 255
            frame[mask == 255] = [0, 255, 0]  # overlay mask in green
        else:
            print(f"No masks detected for frame {frame_idx}")
            
        if return_frame_only:
            return frame

        # display the frame (with or without mask)
        cv.imshow("Mask", frame)
        cv.waitKey(0)
        cv.destroyAllWindows()

    def showWholeVideo(self, output_path=None):
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

            cv.imshow("Segmented Video", frame)
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

    def get_frame_with_mask(self, frame_idx):
        model_outputs = self.model(
            inference_session=self.inference_session,
            frame_idx=frame_idx,
        )

        processed_outputs = self.processor.postprocess_outputs(
            self.inference_session,
            model_outputs
        )

        frame = self.video_frames[frame_idx].copy()

        if processed_outputs["masks"].numel() > 0:
            mask = processed_outputs["masks"][0].detach().cpu().numpy().astype("uint8")

            overlay = frame.copy()
            overlay[mask == 1] = [0, 255, 0]
            alpha = 0.5
            frame = cv.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # BGR → RGB
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        h, w, ch = frame.shape
        bytes_per_line = ch * w

        q_image = QImage(
            frame.data,
            w,
            h,
            bytes_per_line,
            QImage.Format_RGB888
        )

        return q_image.copy()  # VERY IMPORTANT (memory safety)


