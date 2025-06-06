"""
画像モザイク処理ツール

仕様:
1. モード
   - 自動モード: YOLOモデルを使用して人物を検出し、下半身に自動でモザイクを適用
   - 手動(FANZA)モード: FANZA仕様に基づいてモザイクサイズを計算し、クリック位置にモザイクを適用
   - 手動(カスタム)モード: ユーザーが指定したモザイクサイズでクリック位置にモザイクを適用

2. モザイク処理
   - 最初のクリック位置を基準点として保存
   - 2回目以降のクリックでは、基準点からの相対位置に基づいてモザイクを整列
   - モザイクサイズは画像の長辺に応じて自動計算（FANZA仕様）
   - モザイクサイズは最小4ピクセル、画像長辺の1/100（400ピクセル以上の場合）

3. メタデータ
   - 画像ファイルに基準点とモザイクサイズを保存（対応フォーマット: PNG, JPEG, TIFF）
   - 画像を開く際にメタデータから基準点を読み込み
   - メタデータ非対応フォーマットの場合は警告を表示

4. 画像保存
   - メタデータ対応フォーマット: メタデータを含めて保存
   - 非対応フォーマット: 通常の画像として保存（警告表示）
"""

import cv2
import numpy as np
import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import os
import tkinter as tk
from tkinter import messagebox

class MosaicProcessor:
    def __init__(self):
        self.reference_point = None
        self.current_mosaic_size = None
        self.metadata_formats = {'png', 'jpg', 'jpeg', 'tiff', 'tif'}
        
        # メタデータの内容を定義
        self.metadata_text = """この画像は、ベルロッド電子商会が提供するモザイク処理ツールを使用して加工されています。
特定の範囲での配布のみを許可しており、無断での再配布は禁止されています。

お問い合わせ先：alexia.douglas789@vellod-ec.com

---
This image has been processed using the mosaic processing tool provided by Vellod Electronics Trading Co.
Distribution is permitted only within specific ranges, and unauthorized redistribution is prohibited.

Contact: alexia.douglas789@vellod-ec.com"""

    def calculate_fanza_mosaic_size(self, image_shape):
        """FANZA仕様に基づいてモザイクサイズを計算"""
        max_dimension = max(image_shape[0], image_shape[1])
        if max_dimension >= 400:
            return max(4, int(max_dimension / 100))
        return 4

    def apply_mosaic(self, image, x1, y1, x2, y2, size):
        """指定された領域にモザイクを適用"""
        # 座標を整数に変換
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        size = int(size)
        
        # 対象領域を切り出し
        roi = image[y1:y2, x1:x2]
        
        # モザイク処理
        h, w = roi.shape[:2]
        
        # 領域がモザイクサイズより小さい場合は、そのままモザイク処理を適用
        if w <= size or h <= size:
            # 最小サイズでモザイク処理
            roi = cv2.resize(roi, (1, 1))
            roi = cv2.resize(roi, (w, h), interpolation=cv2.INTER_NEAREST)
        else:
            # モザイクサイズで割り切れるように領域を調整
            new_w = (w // size) * size
            new_h = (h // size) * size
            
            # 調整後の領域を切り出し
            roi = roi[:new_h, :new_w]
            
            # モザイク処理
            roi = cv2.resize(roi, (new_w//size, new_h//size))
            roi = cv2.resize(roi, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            
            # 残りの部分もモザイク処理
            if new_w < w and new_h > 0:
                remaining_w = roi[:, new_w:]
                if remaining_w.size > 0:  # 空でないことを確認
                    remaining_w = cv2.resize(remaining_w, (1, remaining_w.shape[0]))
                    remaining_w = cv2.resize(remaining_w, (w - new_w, remaining_w.shape[0]), interpolation=cv2.INTER_NEAREST)
                    roi = np.hstack([roi, remaining_w])
            
            if new_h < h and new_w > 0:
                remaining_h = roi[new_h:, :]
                if remaining_h.size > 0:  # 空でないことを確認
                    remaining_h = cv2.resize(remaining_h, (remaining_h.shape[1], 1))
                    remaining_h = cv2.resize(remaining_h, (remaining_h.shape[1], h - new_h), interpolation=cv2.INTER_NEAREST)
                    roi = np.vstack([roi, remaining_h])
            
            # サイズが一致していることを確認
            if roi.shape[:2] != (h, w):
                roi = cv2.resize(roi, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # 元の画像に戻す
        image[y1:y2, x1:x2] = roi
            
        return image

    def apply_mosaic_with_origin(self, image, x1, y1, x2, y2, size):
        """原点を基準にモザイクを適用"""
        # 座標を整数に変換
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        size = int(size)
        
        # 対象領域を切り出し
        roi = image[y1:y2, x1:x2]
        
        # モザイク処理
        h, w = roi.shape[:2]
        
        # 領域がモザイクサイズより小さい場合は、そのままモザイク処理を適用
        if w <= size or h <= size:
            # 最小サイズでモザイク処理
            roi = cv2.resize(roi, (1, 1))
            roi = cv2.resize(roi, (w, h), interpolation=cv2.INTER_NEAREST)
        else:
            # 画像全体のサイズを取得
            img_h, img_w = image.shape[:2]
            
            # 原点からのオフセットを計算
            offset_x = x1 % size
            offset_y = y1 % size
            
            # モザイクサイズで割り切れるように領域を調整
            mosaic_w = (w // size) * size
            mosaic_h = (h // size) * size
            
            # 拡張した領域を作成（元のROIと同じサイズ）
            expanded_roi = np.zeros((h, w, 3), dtype=roi.dtype)
            
            # 元のROIを拡張領域にコピー
            expanded_roi = roi.copy()
            
            # モザイク処理を適用
            if mosaic_w > 0 and mosaic_h > 0:
                # モザイク領域を処理
                for i in range(0, mosaic_h, size):
                    for j in range(0, mosaic_w, size):
                        # グリッドの位置を計算
                        grid_x = (x1 + j) // size
                        grid_y = (y1 + i) // size
                        
                        # グリッド内の領域を取得
                        grid_roi = expanded_roi[i:i+size, j:j+size]
                        
                        # グリッド内の色の分散を計算
                        color_std = np.std(grid_roi, axis=(0, 1))
                        
                        # 色の分散が小さい（既にモザイク処理されている）場合はスキップ
                        if np.mean(color_std) < 5:  # 閾値は調整可能
                            continue
                        
                        # グリッド内の平均色を計算
                        avg_color = np.mean(grid_roi, axis=(0, 1))
                        
                        # グリッド全体に平均色を適用
                        expanded_roi[i:i+size, j:j+size] = avg_color
            
            # 残りの部分もモザイク処理
            if mosaic_w < w:
                remaining_w = expanded_roi[:, mosaic_w:]
                if remaining_w.size > 0:
                    # 残りの部分の色の分散を計算
                    color_std = np.std(remaining_w, axis=(0, 1))
                    
                    # 色の分散が小さい場合はスキップ
                    if np.mean(color_std) >= 5:  # 閾値は調整可能
                        # 残りの部分の平均色を計算
                        avg_color = np.mean(remaining_w, axis=(0, 1))
                        remaining_w[:] = avg_color
            
            if mosaic_h < h:
                remaining_h = expanded_roi[mosaic_h:, :]
                if remaining_h.size > 0:
                    # 残りの部分の色の分散を計算
                    color_std = np.std(remaining_h, axis=(0, 1))
                    
                    # 色の分散が小さい場合はスキップ
                    if np.mean(color_std) >= 5:  # 閾値は調整可能
                        # 残りの部分の平均色を計算
                        avg_color = np.mean(remaining_h, axis=(0, 1))
                        remaining_h[:] = avg_color
            
            roi = expanded_roi
        
        # 元の画像に戻す
        image[y1:y2, x1:x2] = roi
            
        return image

    def process_image_auto(self, image):
        """自動モードは無効化（YOLO未使用）"""
        # 何も処理せずそのまま返す
        return image

    def process_click(self, image, click_x, click_y, mode, custom_mosaic_size=None):
        """クリック位置に基づいてモザイクを適用"""
        if image is None:
            return image
            
        img = image.copy()
        img_height, img_width = img.shape[:2]
        
        # モザイクサイズの決定
        if mode == "manual_fanza":
            mosaic_size = self.calculate_fanza_mosaic_size(img.shape)
        else:
            mosaic_size = int(custom_mosaic_size)
            
        # モザイクを適用する領域のサイズ（モザイクサイズの2倍）
        area_size = mosaic_size * 2
        
        # クリック位置をモザイクサイズで割り切れるように調整
        adjusted_x = (click_x // mosaic_size) * mosaic_size
        adjusted_y = (click_y // mosaic_size) * mosaic_size
        
        # モザイクを適用する領域の座標を計算
        x1 = max(0, adjusted_x - area_size)
        y1 = max(0, adjusted_y - area_size)
        x2 = min(img_width, adjusted_x + area_size)
        y2 = min(img_height, adjusted_y + area_size)
        
        # モザイクを適用
        img = self.apply_mosaic(img, x1, y1, x2, y2, mosaic_size)
        return img

    def load_reference_point(self, image_path):
        """PNGファイルから基準点を読み込む"""
        if image_path and image_path.lower().endswith('.png'):
            try:
                with Image.open(image_path) as img:
                    if 'reference_point' in img.info:
                        ref_data = json.loads(img.info['reference_point'])
                        self.reference_point = (ref_data['x'], ref_data['y'])
                        self.current_mosaic_size = ref_data['mosaic_size']
                        return True
            except Exception as e:
                print(f"メタデータの読み込みに失敗しました: {e}")
        self.reference_point = None
        self.current_mosaic_size = None
        return False

    def save_with_metadata(self, image, file_path):
        """画像をメタデータ付きで保存"""
        try:
            # ファイル拡張子を取得
            ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            
            if ext in self.metadata_formats:
                # メタデータを準備
                metadata = PngInfo()
                metadata.add_text("Software", "Vellod Mosaic Tool")
                metadata.add_text("ProcessingInfo", self.metadata_text)
                
                if self.reference_point:
                    metadata.add_text("ReferencePoint", json.dumps(self.reference_point))
                if self.current_mosaic_size:
                    metadata.add_text("MosaicSize", str(self.current_mosaic_size))
                
                # PILイメージに変換
                if isinstance(image, np.ndarray):
                    image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                
                # メタデータ付きで保存
                image.save(file_path, pnginfo=metadata)
                return True
            else:
                # メタデータ非対応フォーマットの場合
                if isinstance(image, np.ndarray):
                    cv2.imwrite(file_path, image)
                else:
                    image.save(file_path)
                return False
                
        except Exception as e:
            print(f"メタデータの保存に失敗: {str(e)}")
            # メタデータなしで保存を試みる
            try:
                if isinstance(image, np.ndarray):
                    cv2.imwrite(file_path, image)
                else:
                    image.save(file_path)
                return False
            except Exception as e:
                print(f"画像の保存に失敗: {str(e)}")
                return False 