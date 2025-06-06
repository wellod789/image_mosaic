import os
from natsort import natsorted

class PreviewManager:
    def __init__(self):
        self.preview_mode = False
        self.preview_images = []
        self.current_preview_index = 0
        self.folder_images = []
        self.current_folder_index = 0

    def toggle_preview_mode(self):
        """プレビューモードの切り替え"""
        self.preview_mode = not self.preview_mode
        return self.preview_mode

    def load_folder_image(self, index, image_loader):
        """フォルダ内の指定インデックスの画像を読み込む"""
        if 0 <= index < len(self.folder_images):
            try:
                file_path = self.folder_images[index]
                self.current_folder_index = index
                return image_loader(file_path)
            except Exception as e:
                print(f"Error loading image: {e}")
        return None

    def reload_folder_contents(self, current_image_path):
        """フォルダ内のファイル構成をリロード"""
        if current_image_path:
            folder_path = os.path.dirname(current_image_path)
            self.folder_images = [
                os.path.abspath(os.path.join(folder_path, f))
                for f in os.listdir(folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))
            ]
            self.folder_images = natsorted(self.folder_images)
            # 現在の画像のインデックスを更新
            norm_current_path = os.path.normcase(os.path.normpath(current_image_path))
            norm_folder_images = [os.path.normcase(os.path.normpath(p)) for p in self.folder_images]
            if norm_current_path in norm_folder_images:
                self.current_folder_index = norm_folder_images.index(norm_current_path)

    def get_preview_info(self):
        """プレビュー情報を取得"""
        if not self.preview_mode:
            return None
        return {
            'current_index': self.current_folder_index + 1,
            'total_images': len(self.folder_images)
        }

    def can_move_previous(self):
        """前の画像に移動可能かどうか"""
        return self.preview_mode and self.current_folder_index > 0

    def can_move_next(self):
        """次の画像に移動可能かどうか"""
        return self.preview_mode and self.current_folder_index < len(self.folder_images) - 1 