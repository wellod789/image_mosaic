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
        
        # マスク関連の変数
        self.mask_mode = False  # マスク作成モード
        self.mask_start = None  # マスク開始位置
        self.mask_end = None    # マスク終了位置
        self.mask_rect = None   # マスク表示用の矩形
        self.mask_coords = None # マスク座標（画像座標）
        self.is_creating_mask = False  # マスク作成中フラグ
        
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

        # モザイク処理モード
        self.mosaic_mode = True  # モザイク処理モード（デフォルトで有効）
        
        # 初期状態でマスク削除ボタンを無効化
        self.ui.mask_clear_button.config(state='disabled')

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

    def toggle_mask_mode(self):
        """マスクモードの切り替え"""
        self.mask_mode = not self.mask_mode
        if self.mask_mode:
            # マスクモード開始時はモザイク処理モードを無効にする
            self.mosaic_mode = False
            self.ui.mask_button.config(text="範囲設定終了")
            self.ui.mosaic_button.config(text="モザイク処理開始")
            self.ui.mask_status_label.config(text="範囲設定モード: 2点クリックで処理範囲を設定")
            self.ui.mosaic_status_label.config(text="モザイク処理: 無効")
        else:
            # マスクモード終了時はモザイク処理モードを有効にする
            self.mosaic_mode = True
            self.ui.mask_button.config(text="範囲設定")
            self.ui.mosaic_button.config(text="モザイク処理")
            self.ui.mask_status_label.config(text="処理範囲: なし")
            self.ui.mosaic_status_label.config(text="モザイク処理: 有効")
            # マスク表示をクリア
            if self.mask_rect:
                self.ui.canvas.delete(self.mask_rect)
                self.mask_rect = None
            self.mask_coords = None
            self.mask_start = None
            self.mask_end = None
            self.is_creating_mask = False
            # 画像を再表示
            if self.current_image is not None:
                self.ui.display_image(self.current_image)
                # 処理範囲表示を更新
                if self.mask_coords is not None:
                    self.update_mask_display()

    def clear_mask(self):
        """処理範囲をクリア"""
        self.mask_mode = False
        self.mask_coords = None
        self.mask_start = None
        self.mask_end = None
        self.is_creating_mask = False
        if self.mask_rect:
            self.ui.canvas.delete(self.mask_rect)
            self.mask_rect = None
        self.ui.mask_button.config(text="範囲設定")
        self.ui.mask_status_label.config(text="処理範囲: なし")
        # マスク削除ボタンを無効化（マスクがないため）
        self.ui.mask_clear_button.config(state='disabled')
        # 画像を再表示
        if self.current_image is not None:
            self.ui.display_image(self.current_image)

    def toggle_mosaic_mode(self):
        """モザイク処理モードの切り替え"""
        print("DEBUG: mask_coords =", self.mask_coords)  # デバッグ用
        self.mosaic_mode = not self.mosaic_mode
        if self.mosaic_mode:
            # モザイク処理モード開始時はマスクモードを無効にする
            self.mask_mode = False
            self.ui.mosaic_button.config(text="モザイク処理")
            self.ui.mask_button.config(text="範囲設定")
            self.ui.mosaic_status_label.config(text="モザイク処理: 有効")
            if self.mask_coords:
                x1, y1, x2, y2 = self.mask_coords
                self.ui.mask_status_label.config(text=f"処理範囲: ({x1},{y1}) - ({x2},{y2})")
            else:
                self.ui.mask_status_label.config(text="処理範囲: なし")
            # マスク情報は消さない
            # 画像を再表示
            if self.current_image is not None:
                self.ui.display_image(self.current_image)
                # 処理範囲表示を更新
                if self.mask_coords is not None:
                    self.update_mask_display()
        else:
            self.ui.mosaic_button.config(text="モザイク処理開始")
            self.ui.mosaic_status_label.config(text="モザイク処理: 無効")

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
            # 処理範囲をクリア
            self.clear_mask()
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
                
                # 処理範囲をクリア
                self.clear_mask()
                
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
            # 処理範囲表示を更新
            if self.mask_coords is not None:
                self.update_mask_display()

    def on_canvas_click(self, event):
        if self.current_image is None or self.preview_mode:
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
            
        if self.mask_mode:
            # マスク作成モード - ドラッグ開始
            self.mask_start = (img_x, img_y)
            self.is_creating_mask = True
            self.ui.mask_status_label.config(text="範囲設定モード: ドラッグで範囲を設定してください")
        else:
            # 通常のモザイク処理モード
            # モザイク処理モードが無効の場合は処理しない
            if not self.mosaic_mode:
                return
                
            # ドラッグ開始位置を記録（マスク範囲外でも記録）
            self.drag_start = (img_x, img_y)
            self.is_dragging = True

    def update_mask_display(self):
        """処理範囲表示を更新"""
        if self.mask_coords is None:
            return
            
        # 既存の処理範囲表示を削除
        if self.mask_rect:
            self.ui.canvas.delete(self.mask_rect)
            
        # キャンバス上の座標を取得
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
            
        # 座標変換
        x_scale = img_width / display_width
        y_scale = img_height / display_height
        
        x_offset = (canvas_width - display_width) // 2
        y_offset = (canvas_height - display_height) // 2
        
        x1, y1, x2, y2 = self.mask_coords
        
        # キャンバス座標に変換
        canvas_x1 = x1 / x_scale + x_offset
        canvas_y1 = y1 / y_scale + y_offset
        canvas_x2 = x2 / x_scale + x_offset
        canvas_y2 = y2 / y_scale + y_offset
        
        # 処理範囲を青色の半透明矩形で表示
        self.mask_rect = self.ui.canvas.create_rectangle(
            canvas_x1, canvas_y1, canvas_x2, canvas_y2,
            outline='blue', width=2, fill='', stipple='gray50'
        )

    def on_canvas_drag(self, event):
        if self.current_image is None or self.preview_mode:
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
        
        if self.mask_mode and self.is_creating_mask:
            # 範囲設定時のドラッグ処理
            self.mask_end = (img_x, img_y)
            
            # 仮の処理範囲を表示
            if self.mask_rect:
                self.ui.canvas.delete(self.mask_rect)
                
            # キャンバス上の座標に変換して矩形を描画
            start_x = self.mask_start[0] / x_scale + x_offset
            start_y = self.mask_start[1] / y_scale + y_offset
            end_x = img_x / x_scale + x_offset
            end_y = img_y / y_scale + y_offset
            
            self.mask_rect = self.ui.canvas.create_rectangle(
                start_x, start_y, end_x, end_y,
                outline='blue', width=2, fill='', stipple='gray50'
            )
        elif self.is_dragging:
            # 通常のモザイク処理時のドラッグ処理
            # ドラッグ終了位置を保存（マスク範囲外でも保存）
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
        """マウスボタンリリース時の処理"""
        if self.mask_mode and self.is_creating_mask:
            # 範囲設定のドラッグ終了
            print("DEBUG: マスク作成完了 - mask_coords =", self.mask_coords)  # デバッグ用
            self.is_creating_mask = False
            if self.mask_start and self.mask_end:
                x1 = min(self.mask_start[0], self.mask_end[0])
                y1 = min(self.mask_start[1], self.mask_end[1])
                x2 = max(self.mask_start[0], self.mask_end[0])
                y2 = max(self.mask_start[1], self.mask_end[1])
                self.mask_coords = (x1, y1, x2, y2)
                print("DEBUG: 処理範囲座標設定 - mask_coords =", self.mask_coords)  # デバッグ用
                self.update_mask_display()
                self.ui.mask_status_label.config(text=f"処理範囲: ({x1},{y1}) - ({x2},{y2})")
                # マスク削除ボタンを有効化
                self.ui.mask_clear_button.config(state='normal')
            # 範囲設定モード終了
            self.mask_mode = False
            self.ui.mask_button.config(text="範囲設定")
            self.ui.mosaic_button.config(text="モザイク処理")
            self.ui.mosaic_status_label.config(text="モザイク処理: 有効")
            return
            
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

        # ドラッグ領域の座標を取得
        x1 = min(self.drag_start[0], self.drag_end[0])
        y1 = min(self.drag_start[1], self.drag_end[1])
        x2 = max(self.drag_start[0], self.drag_end[0])
        y2 = max(self.drag_start[1], self.drag_end[1])
        
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
            
        # 処理範囲が設定されている場合、処理範囲内に制限
        if self.mask_coords is not None:
            mask_x1, mask_y1, mask_x2, mask_y2 = self.mask_coords
            # ドラッグ領域と処理範囲の重複部分を計算
            x1 = max(x1, mask_x1)
            y1 = max(y1, mask_y1)
            x2 = min(x2, mask_x2)
            y2 = min(y2, mask_y2)
            
            # 重複がない場合は処理を終了
            if x1 >= x2 or y1 >= y2:
                self.is_dragging = False
                self.drag_start = None
                self.drag_end = None
                return
        
        # 最適なクリック間隔を計算（モザイクサイズの2倍）
        click_interval = mosaic_size * 2
        
        # 処理範囲が設定されている場合は、処理範囲を切り出して処理
        if self.mask_coords is not None:
            # ドラッグ座標を準備
            drag_coords = (x1, y1, x2, y2)
            
            # 処理範囲を切り出して処理し、元の画像に合成
            self.current_image = self.processor.process_masked_area(
                self.current_image,
                self.mask_coords,
                drag_coords,
                self.mode,
                mosaic_size,
                multiplier
            )
        else:
            # 従来の処理（処理範囲なし）
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