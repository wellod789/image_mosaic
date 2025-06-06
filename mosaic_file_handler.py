import os
import shutil
import cv2
import numpy as np
from PIL import Image
import threading
from tkinter import filedialog, messagebox
from natsort import natsorted

class MosaicFileHandler:
    def __init__(self, app):
        self.app = app
        self.saving_in_progress = False
        self._pending_close = False

    def save_image(self):
        """画像を保存"""
        if self.app.current_image is None:
            return
        
        # デフォルトファイル名の生成
        initialfile = "output_1.png"
        if self.app.current_image_path:
            base = os.path.splitext(os.path.basename(self.app.current_image_path))[0]
            ext = ".png"
            folder = os.path.dirname(self.app.current_image_path)
            idx = 1
            while True:
                candidate = f"{base}_{idx}{ext}"
                candidate_path = os.path.join(folder, candidate)
                if not os.path.exists(candidate_path):
                    initialfile = candidate
                    break
                idx += 1
        
        # 保存ダイアログを表示
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("All files", "*.*")
            ],
            initialfile=initialfile
        )
        
        if file_path:
            # 画像を保存
            success = self.app.processor.save_with_metadata(
                self.app.current_image,
                file_path
            )
            
            if success:
                messagebox.showinfo("成功", "画像を保存しました")
                # フォルダ内容をリロード
                self.reload_folder_contents()
            else:
                messagebox.showerror("エラー", "画像の保存に失敗しました")

    def quick_save_image(self):
        if self.app.current_image is None:
            print("Debug: No current image")
            return

        print("Debug: Starting quick save process")
        # 保存先フォルダの設定
        base_folder = os.path.dirname(self.app.current_image_path) if self.app.current_image_path else os.getcwd()
        completed_folder = os.path.join(base_folder, "_Completed")
        original_folder = os.path.join(base_folder, "_Original")

        print(f"Debug: Base folder: {base_folder}")
        print(f"Debug: Completed folder: {completed_folder}")
        print(f"Debug: Original folder: {original_folder}")

        # フォルダが存在しない場合は作成
        os.makedirs(completed_folder, exist_ok=True)
        os.makedirs(original_folder, exist_ok=True)

        # 保存ファイル名の生成
        ext = self.app.ui.save_format_var.get()
        if self.app.current_image_path:
            base = os.path.splitext(os.path.basename(self.app.current_image_path))[0]
        else:
            base = "output"
        idx = 1
        while True:
            candidate = f"{base}_{idx}.{ext}"
            candidate_path = os.path.join(completed_folder, candidate)
            if not os.path.exists(candidate_path):
                break
            idx += 1

        print(f"Debug: Saving to: {candidate_path}")

        original_text = self.app.ui.quick_save_button.cget("text")
        self.app.ui.quick_save_button.config(text="保存中...", state="disabled")
        self.app.ui.quick_save_button.update_idletasks()
        self.saving_in_progress = True

        def save_task():
            try:
                print("Debug: Starting save task")
                # モザイク処理済み画像の保存
                if ext in ["png", "jpg", "jpeg"]:
                    img = self.app.current_image
                    if len(img.shape) == 3 and img.shape[2] == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    if img.dtype != np.uint8:
                        img = img.astype(np.uint8)
                    if len(img.shape) == 2:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(img)
                    if ext == "png":
                        pil_img.save(candidate_path)
                    else:
                        pil_img.save(candidate_path, format="JPEG", quality=95)
                else:
                    img = self.app.current_image
                    if len(img.shape) == 3 and img.shape[2] == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    if img.dtype != np.uint8:
                        img = img.astype(np.uint8)
                    if len(img.shape) == 2:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    cv2.imwrite(candidate_path, img)

                print("Debug: Image saved successfully")

                # オリジナル画像の移動
                if self.app.current_image_path:
                    original_filename = os.path.basename(self.app.current_image_path)
                    original_dest = os.path.join(original_folder, original_filename)
                    print(f"Debug: Moving original to: {original_dest}")
                    if not os.path.exists(original_dest):
                        os.rename(self.app.current_image_path, original_dest)
                        print("Debug: Original moved successfully")

                # フォルダ内容をリロード
                self.app.root.after(0, self.reload_folder_contents)

                # プレビューモードでなければ切り替え
                if not self.app.preview_mode:
                    self.app.root.after(0, self.app.toggle_preview_mode)

                # 次の画像があれば自動で送る
                if self.app.current_folder_index < len(self.app.folder_images) - 1:
                    self.app.root.after(0, lambda: self.app.load_folder_image(self.app.current_folder_index + 1))

            except Exception as e:
                print(f"Debug: Error in save task: {str(e)}")
                pass  # エラー時もポップアップ無し
            finally:
                def finish():
                    self.saving_in_progress = False
                    self.app.ui.quick_save_button.config(text=original_text, state="normal")
                    if self._pending_close:
                        self.app.root.destroy()
                self.app.root.after(0, finish)

        print("Debug: Starting save thread")
        threading.Thread(target=save_task, daemon=True).start()

    def skip_mosaic(self):
        """モザイク不要の画像をオリジナルフォルダに移動し、コンプリートフォルダにコピー"""
        if self.app.current_image is None:
            return

        print("Debug: Starting skip mosaic process")
        # 保存先フォルダの設定
        base_folder = os.path.dirname(self.app.current_image_path) if self.app.current_image_path else os.getcwd()
        completed_folder = os.path.join(base_folder, "_Completed")
        original_folder = os.path.join(base_folder, "_Original")

        print(f"Debug: Base folder: {base_folder}")
        print(f"Debug: Completed folder: {completed_folder}")
        print(f"Debug: Original folder: {original_folder}")

        # フォルダが存在しない場合は作成
        os.makedirs(completed_folder, exist_ok=True)
        os.makedirs(original_folder, exist_ok=True)

        # 保存ファイル名の生成
        ext = self.app.ui.save_format_var.get()
        if self.app.current_image_path:
            base = os.path.splitext(os.path.basename(self.app.current_image_path))[0]
        else:
            base = "output"
        idx = 1
        while True:
            candidate = f"{base}_{idx}.{ext}"
            candidate_path = os.path.join(completed_folder, candidate)
            if not os.path.exists(candidate_path):
                break
            idx += 1

        print(f"Debug: Saving to: {candidate_path}")

        original_text = self.app.ui.skip_button.cget("text")
        self.app.ui.skip_button.config(text="処理中...", state="disabled")
        self.app.ui.skip_button.update_idletasks()
        self.saving_in_progress = True

        def skip_task():
            try:
                print("Debug: Starting skip task")
                # オリジナル画像をコンプリートフォルダにコピー
                if self.app.current_image_path:
                    shutil.copy2(self.app.current_image_path, candidate_path)
                    print("Debug: Image copied to completed folder")

                    # オリジナル画像の移動
                    original_filename = os.path.basename(self.app.current_image_path)
                    original_dest = os.path.join(original_folder, original_filename)
                    print(f"Debug: Moving original to: {original_dest}")
                    if not os.path.exists(original_dest):
                        os.rename(self.app.current_image_path, original_dest)
                        print("Debug: Original moved successfully")

                # フォルダ内容をリロード
                self.app.root.after(0, self.reload_folder_contents)

                # 次の画像に移動
                if self.app.current_folder_index < len(self.app.folder_images) - 1:
                    print("Debug: Moving to next image")
                    self.app.root.after(0, lambda: self.app.load_folder_image(self.app.current_folder_index + 1))

            except Exception as e:
                print(f"Debug: Error in skip task: {str(e)}")
                pass  # エラー時もポップアップ無し
            finally:
                def finish():
                    self.saving_in_progress = False
                    self.app.ui.skip_button.config(text=original_text, state="normal")
                    if self._pending_close:
                        self.app.root.destroy()
                self.app.root.after(0, finish)

        print("Debug: Starting skip thread")
        threading.Thread(target=skip_task, daemon=True).start()

    def reload_folder_contents(self):
        """フォルダ内のファイル構成をリロード"""
        if self.app.current_image_path:
            folder_path = os.path.dirname(self.app.current_image_path)
            self.app.folder_images = [
                os.path.abspath(os.path.join(folder_path, f))
                for f in os.listdir(folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))
            ]
            self.app.folder_images = natsorted(self.app.folder_images)
            # 現在の画像のインデックスを更新
            norm_current_path = os.path.normcase(os.path.normpath(self.app.current_image_path))
            norm_folder_images = [os.path.normcase(os.path.normpath(p)) for p in self.app.folder_images]
            if norm_current_path in norm_folder_images:
                self.app.current_folder_index = norm_folder_images.index(norm_current_path)
            # プレビュー情報を更新
            if self.app.preview_mode:
                self.app.ui.update_preview_info() 