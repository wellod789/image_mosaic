import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import numpy as np

class MosaicUI:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        self.setup_ui()
        
    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ボタンフレーム（上部）
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, columnspan=4, pady=5, sticky=(tk.W, tk.E))
        
        # 各カラムの幅を均等に（ボタン9つ＋mode_frameで10カラム）
        for i in range(10):
            button_frame.columnconfigure(i, weight=1)
        
        # 各ボタン
        self.select_button = ttk.Button(button_frame, text="画像を選択", command=self.app.select_image)
        self.select_button.grid(row=0, column=0, padx=4, sticky=tk.EW)
        self.reset_button = ttk.Button(button_frame, text="元に戻す", command=self.app.reset_image)
        self.reset_button.grid(row=0, column=1, padx=4, sticky=tk.EW)
        self.undo_button = ttk.Button(button_frame, text="戻る", command=self.app.undo, state='disabled')
        self.undo_button.grid(row=0, column=2, padx=4, sticky=tk.EW)
        self.redo_button = ttk.Button(button_frame, text="進む", command=self.app.redo, state='disabled')
        self.redo_button.grid(row=0, column=3, padx=4, sticky=tk.EW)
        self.save_button = ttk.Button(button_frame, text="保存", command=self.app.file_handler.save_image)
        self.save_button.grid(row=0, column=4, padx=4, sticky=tk.EW)
        self.preview_button = ttk.Button(button_frame, text="プレビュー", command=self.app.toggle_preview_mode)
        self.preview_button.grid(row=0, column=5, padx=4, sticky=tk.EW)
        self.skip_button = ttk.Button(button_frame, text="モザイク不要", command=self.app.file_handler.skip_mosaic)
        self.skip_button.grid(row=0, column=6, padx=4, sticky=tk.EW)
        
        # マスク関連のボタン
        self.mask_button = ttk.Button(button_frame, text="範囲設定", command=self.app.toggle_mask_mode)
        self.mask_button.grid(row=0, column=7, padx=4, sticky=tk.EW)
        
        # マスク削除ボタン
        self.mask_clear_button = ttk.Button(button_frame, text="範囲クリア", command=self.app.clear_mask)
        self.mask_clear_button.grid(row=0, column=8, padx=4, sticky=tk.EW)
        
        # モザイク処理ボタン
        self.mosaic_button = ttk.Button(button_frame, text="モザイク処理", command=self.app.toggle_mosaic_mode)
        self.mosaic_button.grid(row=0, column=9, padx=4, sticky=tk.EW)
        
        # --- クイック保存用ラジオボタンとボタン ---
        self.save_format_var = tk.StringVar(value="png")
        radio_frame = ttk.Frame(button_frame)
        radio_frame.grid(row=0, column=10, padx=4, sticky=tk.EW)
        ttk.Radiobutton(radio_frame, text="PNG", variable=self.save_format_var, value="png").pack(side=tk.LEFT)
        ttk.Radiobutton(radio_frame, text="JPEG", variable=self.save_format_var, value="jpg").pack(side=tk.LEFT)
        self.quick_save_button = ttk.Button(button_frame, text="クイック保存", command=self.app.file_handler.quick_save_image)
        self.quick_save_button.grid(row=0, column=11, padx=4, sticky=tk.EW)
        # ---
        
        # モード切替フレーム
        mode_frame = ttk.LabelFrame(button_frame, text="モード切替", padding=(5, 2), labelanchor='n')
        mode_frame.grid(row=0, column=12, padx=4, sticky=tk.EW)
        mode_frame.columnconfigure(0, weight=1)
        
        # モード切替ボタン
        self.mode_button = ttk.Button(
            mode_frame,
            text="手動(FANZA)",
            width=24,
            command=self.app.toggle_mode,
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
        self.create_tooltip(self.mask_button, "クリックして範囲設定モードを開始\n2点クリックでモザイク処理範囲を設定")
        self.create_tooltip(self.mask_clear_button, "クリックして処理範囲をクリア\n設定された処理範囲を削除します")
        self.create_tooltip(self.mosaic_button, "クリックしてモザイク処理モードを開始\nドラッグでモザイク処理を実行")
        
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
        display_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky='nsew')
        
        # 画像表示用のキャンバス
        self.canvas = tk.Canvas(display_frame, bg='gray')
        self.canvas.grid(row=0, column=0, padx=(0, 10), sticky='nsew')
        
        # パラメータ表示用のフレーム
        param_frame = ttk.LabelFrame(display_frame, text="モザイクパラメータ", padding="10", width=250)
        param_frame.grid(row=0, column=1, padx=(0, 10), sticky=(tk.E, tk.N, tk.S))
        param_frame.grid_propagate(False)  # サイズを固定
        
        # パラメータ表示用のラベル
        self.param_labels = {
            'mode': ttk.Label(param_frame, text="モード: 手動(FANZA)", width=25),
            'mosaic_size': ttk.Label(param_frame, text="モザイクサイズ: -", width=25),
            'image_size': ttk.Label(param_frame, text="画像サイズ: -", width=25),
            'max_dimension': ttk.Label(param_frame, text="長辺: -", width=25),
            'mask_status': ttk.Label(param_frame, text="処理範囲: なし", width=25),
            'mosaic_status': ttk.Label(param_frame, text="モザイク処理: 有効", width=25),
            'description': ttk.Label(param_frame, text="説明: 最小4ピクセル平方モザイクかつ画像全体の長辺が400ピクセル以上の場合、\n必要部位に「画像全体長辺×1/100」程度を算出したピクセル平方モザイク(FANZA仕様)\n※自己責任でご利用ください", wraplength=200)
        }
        
        # ラベルを配置
        for i, (key, label) in enumerate(self.param_labels.items()):
            if key != 'description':  # 説明文以外は常に表示
                label.grid(row=i, column=0, sticky=tk.W, pady=2)
            else:  # 説明文は手動FANZAモードの時のみ表示
                label.grid(row=i, column=0, sticky=tk.W, pady=2)
                label.grid_remove()  # 初期状態では非表示
        
        # マスク状態表示ラベルの参照を保存
        self.mask_status_label = self.param_labels['mask_status']
        self.mosaic_status_label = self.param_labels['mosaic_status']
        
        # クリックイベントの設定
        self.canvas.bind("<Button-1>", self.app.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.app.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.app.on_canvas_release)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # グリッドの重みを設定して、ウィンドウリサイズ時に適切に拡大/縮小されるようにする
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        display_frame.columnconfigure(0, weight=1)  # キャンバス側の重みを大きく
        display_frame.columnconfigure(1, weight=0)  # パラメータ側の重みを小さく
        display_frame.rowconfigure(0, weight=1)
        size_frame.columnconfigure(1, weight=1)

    def on_canvas_resize(self, event):
        """キャンバスのリサイズ時に画像を再描画"""
        # debounce/throttleを実装するのが理想的ですが、まずは単純に再描画します
        if self.app.current_image is not None:
            self.display_image(self.app.current_image)
            # プレビューモードの場合は情報も再表示
            if self.app.preview_mode:
                self.update_preview_info()

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

    def display_image(self, img):
        if img is None:
            return
            
        # OpenCVのBGRからRGBに変換
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # PILイメージに変換
        pil_img = Image.fromarray(img_rgb)
        
        # UIの表示を強制的に更新して、最新のサイズ情報を取得
        self.canvas.update_idletasks()
        
        # キャンバスサイズに合わせてリサイズ
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 画像が1x1ピクセルのように非常に小さい場合のガード
        if canvas_width <= 1 or canvas_height <= 1:
            return

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
        
        # 処理範囲表示を更新
        if self.app.mask_coords is not None:
            self.app.update_mask_display()

    def display_preview_image(self):
        """プレビュー用の画像を表示"""
        if self.app.current_image is not None:
            self.display_image(self.app.current_image)
            self.update_preview_info()

    def update_parameter_display(self):
        if self.app.current_image is None:
            return
            
        # モード表示の更新
        mode_text = {
            "manual_fanza": "手動(FANZA)",
            "manual_custom": "手動(カスタム)"
        }
        self.param_labels['mode'].config(
            text=f"モード: {mode_text[self.app.mode]}"
        )
        
        # 説明文の表示/非表示を切り替え
        if self.app.mode == "manual_fanza":
            self.param_labels['description'].grid()
        else:
            self.param_labels['description'].grid_remove()
        
        # モザイクサイズ表示の更新
        if self.app.mode == "manual_fanza":
            # FANZA仕様のモザイクサイズを計算
            base_mosaic_size = self.app.processor.calculate_fanza_mosaic_size(self.app.current_image.shape)
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
        h, w = self.app.current_image.shape[:2]
        self.param_labels['image_size'].config(
            text=f"画像サイズ: {w}x{h}"
        )
        
        # 長辺表示の更新
        max_dim = max(w, h)
        self.param_labels['max_dimension'].config(
            text=f"長辺: {max_dim}px"
        )

    def update_preview_info(self):
        """プレビュー情報を更新"""
        if not self.app.preview_mode:
            return
            
        # プレビュー情報を表示
        info_text = f"プレビュー: {self.app.current_folder_index + 1}/{len(self.app.folder_images)}"
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

    def update_preview_buttons(self):
        """プレビューモード時のボタン状態を更新"""
        if self.app.preview_mode:
            # プレビューモード時は一部のボタンを無効化
            self.select_button.config(state='disabled')
            self.reset_button.config(state='disabled')
            self.undo_button.config(state='disabled')
            self.redo_button.config(state='disabled')
            self.save_button.config(state='disabled')
            self.mode_button.config(state='disabled')
            self.mask_button.config(state='disabled')
            self.mask_clear_button.config(state='disabled')
            self.mosaic_button.config(state='disabled')
            # モザイク不要ボタンは有効のまま
        else:
            # 通常モード時はボタンを有効化
            self.select_button.config(state='normal')
            self.reset_button.config(state='normal')
            self.undo_button.config(state='normal')
            self.redo_button.config(state='normal')
            self.save_button.config(state='normal')
            self.mode_button.config(state='normal')
            self.mask_button.config(state='normal')
            self.mask_clear_button.config(state='normal')
            self.mosaic_button.config(state='normal')

    def update_history_buttons(self):
        """履歴操作ボタンの状態を更新"""
        # 戻るボタン
        if self.app.history_index > 0:
            self.undo_button.config(state='normal')
        else:
            self.undo_button.config(state='disabled')
            
        # 進むボタン
        if self.app.history_index < len(self.app.history) - 1:
            self.redo_button.config(state='normal')
        else:
            self.redo_button.config(state='disabled') 