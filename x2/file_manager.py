import os
import cv2
import numpy as np
from PIL import Image

class FileManager:
    def __init__(self):
        self.current_image_path = None

    def load_image(self, file_path):
        """画像を読み込む"""
        try:
            pil_img = Image.open(file_path)
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            self.current_image_path = file_path
            return image
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    def save_image(self, image, file_path, format="png"):
        """画像を保存"""
        try:
            if format in ["png", "jpg", "jpeg"]:
                img = image
                if len(img.shape) == 3 and img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                if img.dtype != np.uint8:
                    img = img.astype(np.uint8)
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img)
                if format == "png":
                    pil_img.save(file_path)
                else:
                    pil_img.save(file_path, format="JPEG", quality=95)
            else:
                cv2.imwrite(file_path, image)
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False

    def get_next_filename(self, base_folder, base_name, ext):
        """次のファイル名を生成"""
        idx = 1
        while True:
            candidate = f"{base_name}_{idx}.{ext}"
            candidate_path = os.path.join(base_folder, candidate)
            if not os.path.exists(candidate_path):
                return candidate
            idx += 1

    def move_original_file(self, original_path, target_folder):
        """オリジナルファイルを移動"""
        try:
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)
            original_filename = os.path.basename(original_path)
            target_path = os.path.join(target_folder, original_filename)
            if not os.path.exists(target_path):
                os.rename(original_path, target_path)
                return True
        except Exception as e:
            print(f"Error moving original file: {e}")
        return False 