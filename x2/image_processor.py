import cv2
import numpy as np
from PIL import Image

class ImageProcessor:
    def __init__(self):
        pass

    def calculate_fanza_mosaic_size(self, image_shape):
        """FANZA仕様のモザイクサイズを計算"""
        h, w = image_shape[:2]
        max_dim = max(w, h)
        if max_dim >= 400:
            return max(4, int(max_dim / 100))
        return 4

    def process_click(self, image, x, y, mode, mosaic_size):
        # 画像をコピーしてから処理
        img = image.copy()
        if mode == "manual_fanza":
            mosaic_size = self.calculate_fanza_mosaic_size(img.shape)
        x1 = max(0, x - mosaic_size)
        y1 = max(0, y - mosaic_size)
        x2 = min(img.shape[1], x + mosaic_size)
        y2 = min(img.shape[0], y + mosaic_size)
        roi = img[y1:y2, x1:x2]
        if roi.size > 0:
            small = cv2.resize(roi, (mosaic_size, mosaic_size))
            mosaic = cv2.resize(small, (x2-x1, y2-y1), interpolation=cv2.INTER_NEAREST)
            img[y1:y2, x1:x2] = mosaic
        return img

    def save_with_metadata(self, image, file_path):
        """画像をメタデータ付きで保存"""
        try:
            # 画像の保存
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                # PILを使用して保存
                img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img)
                if file_path.lower().endswith('.png'):
                    pil_img.save(file_path)
                else:
                    pil_img.save(file_path, format="JPEG", quality=95)
            else:
                # OpenCVを使用して保存
                cv2.imwrite(file_path, image)
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False 