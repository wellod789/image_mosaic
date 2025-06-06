import cv2
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from mosaic_processor import MosaicProcessor
from mosaic_ui import MosaicUI
from mosaic_file_handler import MosaicFileHandler
import re
from natsort import natsorted
import threading

class MosaicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("画像モザイク処理ツール")
        self.root.geometry("980x670")
        
        # モード設定
        self.mode = "manual_fanza"  # "manual_fanza", "manual_custom"
        self.preview_mode = False  # プレビューモードの状態
        
        # ドラッグ関連の変数
        self.drag_start = None
        self.drag_end = None
        self.drag_rect = None
        self.is_dragging = False
        
        # モザイク処理クラスの初期化
        self.processor = MosaicProcessor()
        
        # ファイル操作ハンドラの初期化
        self.file_handler = MosaicFileHandler(self)
        
        # UIの初期化
        self.ui = MosaicUI(root, self)
        
        # 画像関連の変数
        self.current_image = None
        self.processed_image = None
        self.original_image = None  # 元の画像を保持
        self.current_image_path = None  # 現在の画像のパス
        
        # プレビューモード用の変数
        self.preview_images = []  # プレビュー用の画像リスト
        self.current_preview_index = 0  # 現在のプレビュー画像のインデックス
        self.folder_images = []  # フォルダ内の画像ファイルリスト
        self.current_folder_index = 0  # 現在のフォルダ内インデックス
        
        # 履歴管理
        self.history = []  # 画像の履歴を保存
        self.history_index = -1  # 現在の履歴位置
        self.max_history = 200  # 最大履歴数
        
        # キーボードイベントの設定
        self.root.bind("<Left>", self.previous_image)
        self.root.bind("<Right>", self.next_image)
        self.root.bind("<Escape>", self.exit_preview_mode)
        
        self.saving_in_progress = False  # 保存中フラグ
        self._pending_close = False      # 終了待ちフラグ
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_mode(self):
        # モードを切り替え
        if self.mode == "manual_fanza":
            self.mode = "manual_custom"
            self.ui.mode_button.config(text="手動(カスタム)")
            self.ui.mosaic_size_entry.config(state='normal')  # 入力フィールドを有効化
        else:
            self.mode = "manual_fanza"
            self.ui.mode_button.config(text="手動(FANZA)")
            self.ui.mosaic_size_entry.config(state='disabled')  # 入力フィールドを無効化
        if self.current_image is not None:
            self.reset_image()
        self.ui.update_parameter_display()

    def add_to_history(self, image):
        """履歴に画像を追加"""
        # 現在位置より後の履歴を削除
        self.history = self.history[:self.history_index + 1]
        # 新しい画像を追加
        self.history.append(image.copy())
        self.history_index = len(self.history) - 1
        # 履歴が長すぎる場合は古いものを削除
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1
        # ボタンの状態を更新
        self.ui.update_history_buttons()

    def undo(self):
        """1つ前の状態に戻す"""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_image = self.history[self.history_index].copy()
            self.processed_image = self.current_image.copy()
            self.ui.display_image(self.current_image)
            self.ui.update_parameter_display()
            self.ui.update_history_buttons()

    def redo(self):
        """1つ後の状態に進む"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_image = self.history[self.history_index].copy()
            self.processed_image = self.current_image.copy()
            self.ui.display_image(self.current_image)
            self.ui.update_parameter_display()
            self.ui.update_history_buttons()

    def select_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if file_path:
            try:
                folder_path = os.path.dirname(file_path)
                file_path_abs = os.path.abspath(file_path)
                self.folder_images = [
                    os.path.abspath(os.path.join(folder_path, f))
                    for f in os.listdir(folder_path)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))
                ]
                self.folder_images = natsorted(self.folder_images)
                # パスを正規化して比較
                norm_file_path = os.path.normcase(os.path.normpath(file_path_abs))
                norm_folder_images = [os.path.normcase(os.path.normpath(p)) for p in self.folder_images]
                self.current_folder_index = norm_folder_images.index(norm_file_path)
                pil_img = Image.open(file_path_abs)
                self.original_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")
                return
            self.current_image = self.original_image.copy()
            self.processed_image = self.current_image.copy()
            self.current_image_path = file_path_abs
            # 履歴をクリアして新しい画像を追加
            self.history = [self.current_image.copy()]
            self.history_index = 0
            self.ui.update_history_buttons()
            self.ui.display_image(self.current_image)
            self.ui.update_parameter_display()
            # 画像選択後にプレビューモードへ移行
            self.toggle_preview_mode()
            # フォルダ内容をリロード
            self.file_handler.reload_folder_contents()

    def load_folder_image(self, index):
        """フォルダ内の指定インデックスの画像を読み込む"""
        if 0 <= index < len(self.folder_images):
            try:
                file_path = self.folder_images[index]
                pil_img = Image.open(file_path)
                self.original_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                self.current_image = self.original_image.copy()
                self.processed_image = self.current_image.copy()
                self.current_image_path = file_path
                self.current_folder_index = index
                
                # 履歴をクリアして新しい画像を追加
                self.history = [self.current_image.copy()]
                self.history_index = 0
                self.ui.update_history_buttons()
                
                self.ui.display_image(self.current_image)
                self.ui.update_parameter_display()
                
                # フォルダ内容をリロード
                self.file_handler.reload_folder_contents()
                
                return True
            except Exception as e:
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")
        return False

    def reset_image(self):
        if self.original_image is not None:
            self.current_image = self.original_image.copy()
            self.processed_image = self.current_image.copy()
            self.ui.display_image(self.current_image)
            # 履歴をクリアして新しい画像を追加
            self.history = [self.current_image.copy()]
            self.history_index = 0
            self.ui.update_history_buttons()

    def on_canvas_click(self, event):
        if self.current_image is None or self.preview_mode:
            return
            
        # ドラッグ開始位置を記録
        self.drag_start = (event.x, event.y)
        self.is_dragging = True
        
        # キャンバス上の座標を画像の座標に変換
        canvas_width = self.ui.canvas.winfo_width()
        canvas_height = self.ui.canvas.winfo_height()
        
        # 画像の表示サイズを取得
        img_height, img_width = self.current_image.shape[:2]
        img_ratio = img_width / img_height
        canvas_ratio = canvas_width / canvas_height
        
        if img_ratio > canvas_ratio:
            display_width = canvas_width
            display_height = int(canvas_width / img_ratio)
        else:
            display_height = canvas_height
            display_width = int(canvas_height * img_ratio)
            
        # クリック位置を画像座標に変換
        x_scale = img_width / display_width
        y_scale = img_height / display_height
        
        x_offset = (canvas_width - display_width) // 2
        y_offset = (canvas_height - display_height) // 2
        
        img_x = int((event.x - x_offset) * x_scale)
        img_y = int((event.y - y_offset) * y_scale)
        
        # クリック位置が画像の範囲内かチェック
        if not (0 <= img_x < img_width and 0 <= img_y < img_height):
            return
            
        # ドラッグ開始位置を画像座標で保存
        self.drag_start = (img_x, img_y)

    def on_canvas_drag(self, event):
        if not self.is_dragging or self.current_image is None or self.preview_mode:
            return
            
        # キャンバス上の座標を画像の座標に変換
        canvas_width = self.ui.canvas.winfo_width()
        canvas_height = self.ui.canvas.winfo_height()
        
        # 画像の表示サイズを取得
        img_height, img_width = self.current_image.shape[:2]
        img_ratio = img_width / img_height
        canvas_ratio = canvas_width / canvas_height
        
        if img_ratio > canvas_ratio:
            display_width = canvas_width
            display_height = int(canvas_width / img_ratio)
        else:
            display_height = canvas_height
            display_width = int(canvas_height * img_ratio)
            
        # ドラッグ位置を画像座標に変換
        x_scale = img_width / display_width
        y_scale = img_height / display_height
        
        x_offset = (canvas_width - display_width) // 2
        y_offset = (canvas_height - display_height) // 2
        
        img_x = int((event.x - x_offset) * x_scale)
        img_y = int((event.y - y_offset) * y_scale)
        
        # ドラッグ終了位置を保存
        self.drag_end = (img_x, img_y)
        
        # 仮のモザイク領域を表示
        if self.drag_rect:
            self.ui.canvas.delete(self.drag_rect)
            
        # キャンバス上の座標に変換して矩形を描画
        start_x = self.drag_start[0] / x_scale + x_offset
        start_y = self.drag_start[1] / y_scale + y_offset
        end_x = img_x / x_scale + x_offset
        end_y = img_y / y_scale + y_offset
        
        self.drag_rect = self.ui.canvas.create_rectangle(
            start_x, start_y, end_x, end_y,
            outline='red', width=2
        )

    def on_canvas_release(self, event):
        if not self.is_dragging or self.current_image is None or self.preview_mode:
            return
            
        # ドラッグ終了位置を画像座標に変換
        canvas_width = self.ui.canvas.winfo_width()
        canvas_height = self.ui.canvas.winfo_height()
        
        # 画像の表示サイズを取得
        img_height, img_width = self.current_image.shape[:2]
        img_ratio = img_width / img_height
        canvas_ratio = canvas_width / canvas_height
        
        if img_ratio > canvas_ratio:
            display_width = canvas_width
            display_height = int(canvas_width / img_ratio)
        else:
            display_height = canvas_height
            display_width = int(canvas_height * img_ratio)
            
        # ドラッグ位置を画像座標に変換
        x_scale = img_width / display_width
        y_scale = img_height / display_height
        
        x_offset = (canvas_width - display_width) // 2
        y_offset = (canvas_height - display_height) // 2
        
        img_x = int((event.x - x_offset) * x_scale)
        img_y = int((event.y - y_offset) * y_scale)
        
        # ドラッグ終了位置を保存
        self.drag_end = (img_x, img_y)
        
        # 仮のモザイク領域を削除
        if self.drag_rect:
            self.ui.canvas.delete(self.drag_rect)
            self.drag_rect = None
            
        # モザイクサイズの決定
        if self.mode == "manual_fanza":
            base_mosaic_size = self.processor.calculate_fanza_mosaic_size(self.current_image.shape)
        else:
            base_mosaic_size = int(self.ui.mosaic_size_var.get())
            
        # 倍率を適用
        multiplier = int(self.ui.mosaic_multiplier_var.get())
        mosaic_size = base_mosaic_size * multiplier
            
        # ドラッグ領域の座標を取得
        x1 = min(self.drag_start[0], self.drag_end[0])
        y1 = min(self.drag_start[1], self.drag_end[1])
        x2 = max(self.drag_start[0], self.drag_end[0])
        y2 = max(self.drag_start[1], self.drag_end[1])
        
        # 最適なクリック間隔を計算（モザイクサイズの2倍）
        click_interval = mosaic_size * 2
        
        # ドラッグ領域内を最適化された間隔でクリックしたことにする
        for y in range(y1, y2, click_interval):
            for x in range(x1, x2, click_interval):
                # 画像の範囲内かチェック
                if 0 <= x < img_width and 0 <= y < img_height:
                    # クリック位置にモザイクを適用
                    self.current_image = self.processor.process_click(
                        self.current_image,
                        x, y,
                        self.mode,
                        mosaic_size
                    )
        
        self.processed_image = self.current_image.copy()
        
        # 履歴に追加
        self.add_to_history(self.current_image)
        
        # 画像を更新
        self.ui.display_image(self.current_image)
        self.ui.update_parameter_display()
        
        # ドラッグ状態をリセット
        self.is_dragging = False
        self.drag_start = None
        self.drag_end = None

    def toggle_preview_mode(self):
        """プレビューモードの切り替え"""
        if not self.preview_mode:
            # プレビューモードを開始
            self.preview_mode = True
            self.ui.preview_button.config(text="プレビュー終了")
            
            # 現在の画像をプレビューリストに追加
            if self.current_image is not None:
                self.preview_images = [self.current_image.copy()]
                self.current_preview_index = 0
                
                # プレビュー用の画像を表示
                self.ui.display_preview_image()
                
                # ボタンの状態を更新
                self.ui.update_preview_buttons()
        else:
            # プレビューモードを終了
            self.exit_preview_mode()

    def exit_preview_mode(self, event=None):
        """プレビューモードを終了"""
        if self.preview_mode:
            self.preview_mode = False
            self.ui.preview_button.config(text="プレビュー")
            
            # 元の画像を表示
            if self.current_image is not None:
                self.ui.display_image(self.current_image)
            
            # ボタンの状態を更新
            self.ui.update_preview_buttons()

    def previous_image(self, event=None):
        """前の画像に移動"""
        if not self.preview_mode:
            return
            
        if self.current_folder_index > 0:
            if self.load_folder_image(self.current_folder_index - 1):
                self.ui.update_preview_info()

    def next_image(self, event=None):
        """次の画像に移動"""
        if not self.preview_mode:
            return
            
        if self.current_folder_index < len(self.folder_images) - 1:
            if self.load_folder_image(self.current_folder_index + 1):
                self.ui.update_preview_info()

    def on_closing(self):
        if self.saving_in_progress:
            self._pending_close = True
            self.ui.quick_save_button.config(text="保存中... 終了待機", state="disabled")
            return
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MosaicApp(root)
    root.mainloop()