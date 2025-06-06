import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import os
from mosaic_processor import MosaicProcessor
import re
from natsort import natsorted
import threading

class MosaicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("画像モザイク処理ツール")
        self.root.geometry("980x670")
        
        # モード設定（setup_uiより前に移動）
        self.mode = "manual_fanza"  # "manual_fanza", "manual_custom"
        self.preview_mode = False  # プレビューモードの状態
        
        # ドラッグ関連の変数
        self.drag_start = None
        self.drag_end = None
        self.drag_rect = None
        self.is_dragging = False
        
        # モザイク処理クラスの初期化
        self.processor = MosaicProcessor()
        
        # UIの設定
        self.setup_ui()
        
        # 画像関連の変数
        self.current_image = None
        self.processed_image = None
        self.photo = None
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
        
    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ボタンフレーム（上部）
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, columnspan=4, pady=5, sticky=(tk.W, tk.E))
        
        # 各カラムの幅を均等に（ボタン7つ＋mode_frameで8カラム）
        for i in range(8):
            button_frame.columnconfigure(i, weight=1)
        
        # 各ボタン
        self.select_button = ttk.Button(button_frame, text="画像を選択", command=self.select_image)
        self.select_button.grid(row=0, column=0, padx=4, sticky=tk.EW)
        self.reset_button = ttk.Button(button_frame, text="元に戻す", command=self.reset_image)
        self.reset_button.grid(row=0, column=1, padx=4, sticky=tk.EW)
        self.undo_button = ttk.Button(button_frame, text="戻る", command=self.undo, state='disabled')
        self.undo_button.grid(row=0, column=2, padx=4, sticky=tk.EW)
        self.redo_button = ttk.Button(button_frame, text="進む", command=self.redo, state='disabled')
        self.redo_button.grid(row=0, column=3, padx=4, sticky=tk.EW)
        self.save_button = ttk.Button(button_frame, text="保存", command=self.save_image)
        self.save_button.grid(row=0, column=4, padx=4, sticky=tk.EW)
        self.preview_button = ttk.Button(button_frame, text="プレビュー", command=self.toggle_preview_mode)
        self.preview_button.grid(row=0, column=5, padx=4, sticky=tk.EW)
        self.skip_button = ttk.Button(button_frame, text="モザイク不要", command=self.skip_mosaic)
        self.skip_button.grid(row=0, column=6, padx=4, sticky=tk.EW)
        
        # --- クイック保存用ラジオボタンとボタン ---
        self.save_format_var = tk.StringVar(value="png")
        radio_frame = ttk.Frame(button_frame)
        radio_frame.grid(row=0, column=7, padx=4, sticky=tk.EW)
        ttk.Radiobutton(radio_frame, text="PNG", variable=self.save_format_var, value="png").pack(side=tk.LEFT)
        ttk.Radiobutton(radio_frame, text="JPEG", variable=self.save_format_var, value="jpg").pack(side=tk.LEFT)
        self.quick_save_button = ttk.Button(button_frame, text="クイック保存", command=self.quick_save_image)
        self.quick_save_button.grid(row=0, column=8, padx=4, sticky=tk.EW)
        # ---
        
        # モード切替フレーム（labelanchorで高さを揃え、paddingで余白調整）
        mode_frame = ttk.LabelFrame(button_frame, text="モード切替", padding=(5, 2), labelanchor='n')
        mode_frame.grid(row=0, column=9, padx=4, sticky=tk.EW)
        mode_frame.columnconfigure(0, weight=1)
        
        # モード切替ボタン（1つだけ、幅固定）
        self.mode_button = ttk.Button(
            mode_frame,
            text="手動(FANZA)",
            width=24,
            command=self.toggle_mode,
            style='Mode.TButton'
        )
        self.mode_button.grid(row=0, column=0, padx=2, sticky=tk.EW)
        
        # モード切替ボタンのスタイル設定
        style = ttk.Style()
        style.configure(
            'Mode.TButton',
            padding=5,
            relief='raised',
            borderwidth=2
        )
        
        # ツールチップの設定
        self.create_tooltip(self.mode_button, "クリックしてモードを切り替え\n手動(FANZA) → 手動(カスタム)")
        
        # モザイクサイズの設定フレーム
        size_frame = ttk.Frame(main_frame)
        size_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Label(size_frame, text="モザイクサイズ:").grid(row=0, column=0, padx=5)
        
        # 数値入力フィールドの変数
        self.mosaic_size_var = tk.StringVar(value="20")
        
        # 数値入力フィールド
        self.mosaic_size_entry = ttk.Entry(
            size_frame,
            textvariable=self.mosaic_size_var,
            width=2,
            justify='right',
            font=('', 10)
        )
        self.mosaic_size_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2, ipadx=0)
        
        # モザイク倍率のラジオボタン
        self.mosaic_multiplier_var = tk.StringVar(value="1")
        multiplier_frame = ttk.LabelFrame(size_frame, text="モザイク倍率", padding=(5, 2))
        multiplier_frame.grid(row=0, column=2, padx=10, sticky=tk.EW)
        
        multipliers = [("等倍", "1"), ("2倍", "2"), ("3倍", "3"), ("4倍", "4")]
        for i, (text, value) in enumerate(multipliers):
            ttk.Radiobutton(
                multiplier_frame,
                text=text,
                value=value,
                variable=self.mosaic_multiplier_var
            ).grid(row=0, column=i, padx=5)
        
        # 数値入力の検証関数
        def validate_mosaic_size(P):
            if P == "": return True
            try:
                value = int(P)
                return 1 <= value <= 100
            except ValueError:
                return False
        
        # 検証コマンドの登録
        vcmd = (self.root.register(validate_mosaic_size), '%P')
        self.mosaic_size_entry.config(validate='key', validatecommand=vcmd)
        
        # 画像表示用のフレーム
        display_frame = ttk.Frame(main_frame)
        display_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        # 画像表示用のキャンバス
        self.canvas = tk.Canvas(display_frame, width=600, height=500, bg='gray')
        self.canvas.grid(row=0, column=0, padx=10)
        
        # パラメータ表示用のフレーム
        param_frame = ttk.LabelFrame(display_frame, text="モザイクパラメータ", padding="10")
        param_frame.grid(row=0, column=1, padx=10, sticky=(tk.N, tk.S))
        
        # パラメータ表示用のラベル
        self.param_labels = {
            'mode': ttk.Label(param_frame, text="モード: 手動(FANZA)"),
            'mosaic_size': ttk.Label(param_frame, text="モザイクサイズ: -"),
            'image_size': ttk.Label(param_frame, text="画像サイズ: -"),
            'max_dimension': ttk.Label(param_frame, text="長辺: -"),
            'description': ttk.Label(param_frame, text="説明: 最小4ピクセル平方モザイクかつ画像全体の長辺が400ピクセル以上の場合、\n必要部位に「画像全体長辺×1/100」程度を算出したピクセル平方モザイク(FANZA仕様)\n※自己責任でご利用ください", wraplength=200)
        }
        
        # ラベルを配置
        for i, (key, label) in enumerate(self.param_labels.items()):
            if key != 'description':  # 説明文以外は常に表示
                label.grid(row=i, column=0, sticky=tk.W, pady=2)
            else:  # 説明文は手動FANZAモードの時のみ表示
                label.grid(row=i, column=0, sticky=tk.W, pady=2)
                label.grid_remove()  # 初期状態では非表示
        
        # クリックイベントの設定
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # グリッドの重みを設定して、ウィンドウリサイズ時に適切に拡大/縮小されるようにする
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        display_frame.columnconfigure(0, weight=1)
        display_frame.rowconfigure(0, weight=1)
        size_frame.columnconfigure(1, weight=1)
        
    def update_parameter_display(self):
        if self.current_image is None:
            return
            
        # モード表示の更新
        mode_text = {
            "manual_fanza": "手動(FANZA)",
            "manual_custom": "手動(カスタム)"
        }
        self.param_labels['mode'].config(
            text=f"モード: {mode_text[self.mode]}"
        )
        
        # 説明文の表示/非表示を切り替え
        if self.mode == "manual_fanza":
            self.param_labels['description'].grid()
        else:
            self.param_labels['description'].grid_remove()
        
        # モザイクサイズ表示の更新
        if self.mode == "manual_fanza":
            # FANZA仕様のモザイクサイズを計算
            base_mosaic_size = self.processor.calculate_fanza_mosaic_size(self.current_image.shape)
            multiplier = int(self.mosaic_multiplier_var.get())
            mosaic_size = base_mosaic_size * multiplier
            self.param_labels['mosaic_size'].config(
                text=f"モザイクサイズ: {mosaic_size} (FANZA仕様 × {multiplier}倍)"
            )
        else:
            # カスタムモードの場合は入力フィールドの値と倍率を表示
            base_size = int(self.mosaic_size_var.get())
            multiplier = int(self.mosaic_multiplier_var.get())
            mosaic_size = base_size * multiplier
            self.param_labels['mosaic_size'].config(
                text=f"モザイクサイズ: {mosaic_size} ({base_size} × {multiplier}倍)"
            )
        
        # 画像サイズ表示の更新
        h, w = self.current_image.shape[:2]
        self.param_labels['image_size'].config(
            text=f"画像サイズ: {w}x{h}"
        )
        
        # 長辺表示の更新
        max_dim = max(w, h)
        self.param_labels['max_dimension'].config(
            text=f"長辺: {max_dim}px"
        )
        
    def create_tooltip(self, widget, text):
        """ツールチップを作成"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(
                tooltip,
                text=text,
                justify=tk.LEFT,
                background="#ffffe0",
                relief=tk.SOLID,
                borderwidth=1,
                padding=5
            )
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
            widget.bind('<ButtonPress>', lambda e: hide_tooltip())
        
        widget.bind('<Enter>', show_tooltip)

    def toggle_mode(self):
        # モードを切り替え
        if self.mode == "manual_fanza":
            self.mode = "manual_custom"
            self.mode_button.config(text="手動(カスタム)")
            self.mosaic_size_entry.config(state='normal')  # 入力フィールドを有効化
        else:
            self.mode = "manual_fanza"
            self.mode_button.config(text="手動(FANZA)")
            self.mosaic_size_entry.config(state='disabled')  # 入力フィールドを無効化
        if self.current_image is not None:
            self.reset_image()
        self.update_parameter_display()

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
        self.update_history_buttons()

    def update_history_buttons(self):
        """履歴操作ボタンの状態を更新"""
        # 戻るボタン
        if self.history_index > 0:
            self.undo_button.config(state='normal')
        else:
            self.undo_button.config(state='disabled')
            
        # 進むボタン
        if self.history_index < len(self.history) - 1:
            self.redo_button.config(state='normal')
        else:
            self.redo_button.config(state='disabled')

    def undo(self):
        """1つ前の状態に戻す"""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_image = self.history[self.history_index].copy()
            self.processed_image = self.current_image.copy()
            self.display_image(self.current_image)
            self.update_parameter_display()
            self.update_history_buttons()

    def redo(self):
        """1つ後の状態に進む"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_image = self.history[self.history_index].copy()
            self.processed_image = self.current_image.copy()
            self.display_image(self.current_image)
            self.update_parameter_display()
            self.update_history_buttons()

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
            self.update_history_buttons()
            self.display_image(self.current_image)
            self.update_parameter_display()
            # 画像選択後にプレビューモードへ移行
            self.toggle_preview_mode()

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
                self.update_history_buttons()
                
                self.display_image(self.current_image)
                self.update_parameter_display()
                
                return True
            except Exception as e:
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")
        return False

    def reset_image(self):
        if self.original_image is not None:
            self.current_image = self.original_image.copy()
            self.processed_image = self.current_image.copy()
            self.display_image(self.current_image)
            # 履歴をクリアして新しい画像を追加
            self.history = [self.current_image.copy()]
            self.history_index = 0
            self.update_history_buttons()

    def on_canvas_click(self, event):
        if self.current_image is None or self.preview_mode:
            return
            
        # ドラッグ開始位置を記録
        self.drag_start = (event.x, event.y)
        self.is_dragging = True
        
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
        
        # クリック位置が画像の範囲内かチェック
        if not (0 <= img_x < img_width and 0 <= img_y < img_height):
            return
            
        # ドラッグ開始位置を画像座標で保存
        self.drag_start = (img_x, img_y)

    def on_canvas_drag(self, event):
        if not self.is_dragging or self.current_image is None or self.preview_mode:
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
            self.canvas.delete(self.drag_rect)
            
        # キャンバス上の座標に変換して矩形を描画
        start_x = self.drag_start[0] / x_scale + x_offset
        start_y = self.drag_start[1] / y_scale + y_offset
        end_x = img_x / x_scale + x_offset
        end_y = img_y / y_scale + y_offset
        
        self.drag_rect = self.canvas.create_rectangle(
            start_x, start_y, end_x, end_y,
            outline='red', width=2
        )

    def on_canvas_release(self, event):
        if not self.is_dragging or self.current_image is None or self.preview_mode:
            return
            
        # ドラッグ終了位置を画像座標に変換
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
            self.canvas.delete(self.drag_rect)
            self.drag_rect = None
            
        # モザイクサイズの決定
        if self.mode == "manual_fanza":
            base_mosaic_size = self.processor.calculate_fanza_mosaic_size(self.current_image.shape)
        else:
            base_mosaic_size = int(self.mosaic_size_var.get())
            
        # 倍率を適用
        multiplier = int(self.mosaic_multiplier_var.get())
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
        self.display_image(self.current_image)
        self.update_parameter_display()
        
        # ドラッグ状態をリセット
        self.is_dragging = False
        self.drag_start = None
        self.drag_end = None

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
        
    def reload_folder_contents(self):
        """フォルダ内のファイル構成をリロード"""
        if self.current_image_path:
            folder_path = os.path.dirname(self.current_image_path)
            self.folder_images = [
                os.path.abspath(os.path.join(folder_path, f))
                for f in os.listdir(folder_path)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))
            ]
            self.folder_images = natsorted(self.folder_images)
            # 現在の画像のインデックスを更新
            norm_current_path = os.path.normcase(os.path.normpath(self.current_image_path))
            norm_folder_images = [os.path.normcase(os.path.normpath(p)) for p in self.folder_images]
            if norm_current_path in norm_folder_images:
                self.current_folder_index = norm_folder_images.index(norm_current_path)
            # プレビュー情報を更新
            if self.preview_mode:
                self.update_preview_info()

    def save_image(self):
        """画像を保存"""
        if self.current_image is None:
            return
        
        # デフォルトファイル名の生成
        initialfile = "output_1.png"
        if self.current_image_path:
            base = os.path.splitext(os.path.basename(self.current_image_path))[0]
            ext = ".png"
            folder = os.path.dirname(self.current_image_path)
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
            success = self.processor.save_with_metadata(
                self.current_image,
                file_path
            )
            
            if success:
                messagebox.showinfo("成功", "画像を保存しました")
                # フォルダ内容をリロード
                self.reload_folder_contents()
            else:
                messagebox.showerror("エラー", "画像の保存に失敗しました")

    def toggle_preview_mode(self):
        """プレビューモードの切り替え"""
        if not self.preview_mode:
            # プレビューモードを開始
            self.preview_mode = True
            self.preview_button.config(text="プレビュー終了")
            
            # 現在の画像をプレビューリストに追加
            if self.current_image is not None:
                self.preview_images = [self.current_image.copy()]
                self.current_preview_index = 0
                
                # プレビュー用の画像を表示
                self.display_preview_image()
                
                # ボタンの状態を更新
                self.update_preview_buttons()
        else:
            # プレビューモードを終了
            self.exit_preview_mode()

    def exit_preview_mode(self, event=None):
        """プレビューモードを終了"""
        if self.preview_mode:
            self.preview_mode = False
            self.preview_button.config(text="プレビュー")
            
            # 元の画像を表示
            if self.current_image is not None:
                self.display_image(self.current_image)
            
            # ボタンの状態を更新
            self.update_preview_buttons()

    def display_preview_image(self):
        """プレビュー用の画像を表示"""
        if not self.preview_images:
            return
            
        # 現在のプレビュー画像を表示
        self.display_image(self.preview_images[self.current_preview_index])
        
        # プレビュー情報を表示
        self.update_preview_info()

    def update_preview_info(self):
        """プレビュー情報を更新"""
        if not self.preview_mode:
            return
            
        # プレビュー情報を表示
        info_text = f"プレビュー: {self.current_folder_index + 1}/{len(self.folder_images)}"
        self.canvas.create_text(
            self.canvas.winfo_width() - 10,
            10,
            text=info_text,
            anchor=tk.NE,
            fill="white",
            font=("Arial", 12)
        )
        # キーボード操作説明を表示
        self.canvas.create_text(
            self.canvas.winfo_width() - 10,
            30,
            text="←→キーで前後の画像を切り替えられます",
            anchor=tk.NE,
            fill="white",
            font=("Arial", 10)
        )

    def previous_image(self, event=None):
        """前の画像に移動"""
        if not self.preview_mode:
            return
            
        if self.current_folder_index > 0:
            if self.load_folder_image(self.current_folder_index - 1):
                self.update_preview_info()

    def next_image(self, event=None):
        """次の画像に移動"""
        if not self.preview_mode:
            return
            
        if self.current_folder_index < len(self.folder_images) - 1:
            if self.load_folder_image(self.current_folder_index + 1):
                self.update_preview_info()

    def update_preview_buttons(self):
        """プレビューモード時のボタン状態を更新"""
        if self.preview_mode:
            # プレビューモード時は一部のボタンを無効化
            self.select_button.config(state='disabled')
            self.reset_button.config(state='disabled')
            self.undo_button.config(state='disabled')
            self.redo_button.config(state='disabled')
            self.save_button.config(state='disabled')
            self.mode_button.config(state='disabled')
            # モザイク不要ボタンは有効のまま
        else:
            # 通常モード時はボタンを有効化
            self.select_button.config(state='normal')
            self.reset_button.config(state='normal')
            self.undo_button.config(state='normal')
            self.redo_button.config(state='normal')
            self.save_button.config(state='normal')
            self.mode_button.config(state='normal')

    def on_closing(self):
        if self.saving_in_progress:
            self._pending_close = True
            self.quick_save_button.config(text="保存中... 終了待機", state="disabled")
            return
        self.root.destroy()

    def quick_save_image(self):
        if self.current_image is None:
            print("Debug: No current image")
            return

        print("Debug: Starting quick save process")
        # 保存先フォルダの設定
        base_folder = os.path.dirname(self.current_image_path) if self.current_image_path else os.getcwd()
        completed_folder = os.path.join(base_folder, "_Completed")
        original_folder = os.path.join(base_folder, "_Original")

        print(f"Debug: Base folder: {base_folder}")
        print(f"Debug: Completed folder: {completed_folder}")
        print(f"Debug: Original folder: {original_folder}")

        # フォルダが存在しない場合は作成
        os.makedirs(completed_folder, exist_ok=True)
        os.makedirs(original_folder, exist_ok=True)

        # 保存ファイル名の生成
        ext = self.save_format_var.get()
        if self.current_image_path:
            base = os.path.splitext(os.path.basename(self.current_image_path))[0]
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

        original_text = self.quick_save_button.cget("text")
        self.quick_save_button.config(text="保存中...", state="disabled")
        self.quick_save_button.update_idletasks()
        self.saving_in_progress = True

        def save_task():
            try:
                print("Debug: Starting save task")
                # モザイク処理済み画像の保存
                from PIL import Image
                if ext in ["png", "jpg", "jpeg"]:
                    img = self.current_image
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
                    img = self.current_image
                    if len(img.shape) == 3 and img.shape[2] == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    if img.dtype != np.uint8:
                        img = img.astype(np.uint8)
                    if len(img.shape) == 2:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    cv2.imwrite(candidate_path, img)

                print("Debug: Image saved successfully")

                # オリジナル画像の移動
                if self.current_image_path:
                    original_filename = os.path.basename(self.current_image_path)
                    original_dest = os.path.join(original_folder, original_filename)
                    print(f"Debug: Moving original to: {original_dest}")
                    if not os.path.exists(original_dest):
                        os.rename(self.current_image_path, original_dest)
                        print("Debug: Original moved successfully")

                # フォルダ内容をリロード
                self.root.after(0, self.reload_folder_contents)

                # プレビューモードの場合、次の画像に移動
                if self.preview_mode and self.current_folder_index < len(self.folder_images) - 1:
                    print("Debug: Moving to next image in preview mode")
                    self.root.after(0, lambda: self.load_folder_image(self.current_folder_index + 1))

            except Exception as e:
                print(f"Debug: Error in save task: {str(e)}")
                pass  # エラー時もポップアップ無し
            finally:
                def finish():
                    self.saving_in_progress = False
                    self.quick_save_button.config(text=original_text, state="normal")
                    if self._pending_close:
                        self.root.destroy()
                self.root.after(0, finish)

        print("Debug: Starting save thread")
        threading.Thread(target=save_task, daemon=True).start()

    def skip_mosaic(self):
        """モザイク不要の画像をオリジナルフォルダに移動し、コンプリートフォルダにコピー"""
        if self.current_image is None:
            return

        print("Debug: Starting skip mosaic process")
        # 保存先フォルダの設定
        base_folder = os.path.dirname(self.current_image_path) if self.current_image_path else os.getcwd()
        completed_folder = os.path.join(base_folder, "_Completed")
        original_folder = os.path.join(base_folder, "_Original")

        print(f"Debug: Base folder: {base_folder}")
        print(f"Debug: Completed folder: {completed_folder}")
        print(f"Debug: Original folder: {original_folder}")

        # フォルダが存在しない場合は作成
        os.makedirs(completed_folder, exist_ok=True)
        os.makedirs(original_folder, exist_ok=True)

        # 保存ファイル名の生成
        ext = self.save_format_var.get()
        if self.current_image_path:
            base = os.path.splitext(os.path.basename(self.current_image_path))[0]
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

        original_text = self.skip_button.cget("text")
        self.skip_button.config(text="処理中...", state="disabled")
        self.skip_button.update_idletasks()
        self.saving_in_progress = True

        def skip_task():
            try:
                print("Debug: Starting skip task")
                # オリジナル画像をコンプリートフォルダにコピー
                if self.current_image_path:
                    import shutil
                    shutil.copy2(self.current_image_path, candidate_path)
                    print("Debug: Image copied to completed folder")

                    # オリジナル画像の移動
                    original_filename = os.path.basename(self.current_image_path)
                    original_dest = os.path.join(original_folder, original_filename)
                    print(f"Debug: Moving original to: {original_dest}")
                    if not os.path.exists(original_dest):
                        os.rename(self.current_image_path, original_dest)
                        print("Debug: Original moved successfully")

                # フォルダ内容をリロード
                self.root.after(0, self.reload_folder_contents)

                # 次の画像に移動
                if self.current_folder_index < len(self.folder_images) - 1:
                    print("Debug: Moving to next image")
                    self.root.after(0, lambda: self.load_folder_image(self.current_folder_index + 1))

            except Exception as e:
                print(f"Debug: Error in skip task: {str(e)}")
                pass  # エラー時もポップアップ無し
            finally:
                def finish():
                    self.saving_in_progress = False
                    self.skip_button.config(text=original_text, state="normal")
                    if self._pending_close:
                        self.root.destroy()
                self.root.after(0, finish)

        print("Debug: Starting skip thread")
        threading.Thread(target=skip_task, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MosaicApp(root)
    root.mainloop()