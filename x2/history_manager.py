import numpy as np

class HistoryManager:
    def __init__(self, max_history=200):
        self.history = []
        self.history_index = -1
        self.max_history = max_history

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
        return self.get_history_state()

    def get_history_state(self):
        """履歴の状態を取得"""
        return {
            'can_undo': self.history_index > 0,
            'can_redo': self.history_index < len(self.history) - 1
        }

    def undo(self):
        """1つ前の状態に戻す"""
        if self.history_index > 0:
            self.history_index -= 1
            return self.history[self.history_index].copy()
        return None

    def redo(self):
        """1つ後の状態に進む"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            return self.history[self.history_index].copy()
        return None

    def clear_history(self):
        """履歴をクリア"""
        self.history = []
        self.history_index = -1
        return self.get_history_state() 