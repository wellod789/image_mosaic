import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import os

class ManualMosaicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("手動モザイク処理ツール")
        self.root.geometry("800x600")
        
        # UIの設定
        self.setup_ui()
        
        # 画像関連の変数
        self.current_image = None
        self.processed_image = None
        self.photo = None
        self.original_image = None  # 元の画像を保持
        
    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ボタン
        ttk.Button(main_frame, text="画像を選択", command=self.select_image).grid(row=0, column=0, pady=5)
        ttk.Button(main_frame, text="元に戻す", command=self.reset_image).grid(row=0, column=1, pady=5)
        ttk.Button(main_frame, text="保存", command=self.save_image).grid(row=0, column=2, pady=5)
        
        # 画像表示用のキャンバス
        self.canvas = tk.Canvas(main_frame, width=700, height=500, bg='gray')
        self.canvas.grid(row=1, column=0, columnspan=3, pady=10)
        
        # クリックイベントの設定
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
    def select_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if file_path:
            try:
                pil_img = Image.open(file_path)
                self.original_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")
                return
            self.current_image = self.original_image.copy()
            self.processed_image = self.current_image.copy()
            self.display_image(self.current_image)
            
    def reset_image(self):
        if self.original_image is not None:
            self.current_image = self.original_image.copy()
            self.processed_image = self.current_image.copy()
            self.display_image(self.current_image)
            
    def on_canvas_click(self, event):
        if self.current_image is None:
            return
            
        # キャンバス上の座標を画像の座標に変換
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
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
        
        # 画像の長辺を取得
        max_dimension = max(img_width, img_height)
        
        # FANZA仕様に基づいてモザイクサイズを計算
        if max_dimension >= 400:
            mosaic_size = max(4, int(max_dimension / 100))
        else:
            mosaic_size = 4
            
        # モザイクを適用する領域のサイズ（モザイクサイズの2倍）
        area_size = mosaic_size * 2
        
        # モザイクを適用する領域の座標を計算
        x1 = max(0, img_x - area_size)
        y1 = max(0, img_y - area_size)
        x2 = min(img_width, img_x + area_size)
        y2 = min(img_height, img_y + area_size)
        
        # モザイクを適用
        self.apply_mosaic(x1, y1, x2, y2, mosaic_size)
        
    def apply_mosaic(self, x1, y1, x2, y2, size):
        # 対象領域を切り出し
        roi = self.current_image[y1:y2, x1:x2]
        
        # モザイク処理
        h, w = roi.shape[:2]
        roi = cv2.resize(roi, (w//size, h//size))
        roi = cv2.resize(roi, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # 元の画像に戻す
        self.current_image[y1:y2, x1:x2] = roi
        self.processed_image = self.current_image.copy()
        
        # 画像を更新
        self.display_image(self.current_image)
        
    def display_image(self, img):
        if img is None:
            return
            
        # OpenCVのBGRからRGBに変換
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # PILイメージに変換
        pil_img = Image.fromarray(img_rgb)
        
        # キャンバスサイズに合わせてリサイズ
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # アスペクト比を保持してリサイズ
        img_ratio = pil_img.width / pil_img.height
        canvas_ratio = canvas_width / canvas_height
        
        if img_ratio > canvas_ratio:
            new_width = canvas_width
            new_height = int(canvas_width / img_ratio)
        else:
            new_height = canvas_height
            new_width = int(canvas_height * img_ratio)
            
        pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # PhotoImageに変換
        self.photo = ImageTk.PhotoImage(pil_img)
        
        # キャンバスに表示
        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_width//2, canvas_height//2,
            image=self.photo,
            anchor=tk.CENTER
        )
        
    def save_image(self):
        if self.processed_image is None:
            messagebox.showwarning("警告", "処理済み画像がありません。")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        
        if file_path:
            cv2.imwrite(file_path, self.processed_image)
            messagebox.showinfo("成功", "画像を保存しました。")

if __name__ == "__main__":
    root = tk.Tk()
    app = ManualMosaicApp(root)
    root.mainloop() 