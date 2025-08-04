# ui/widgets/vitals/vitals_widget.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar


class VitalsWidget(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app

        self.bars = {}
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(4)
        self.layout.setContentsMargins(4, 4, 4, 4)

        self._init_bar("Health", 11)
        self._init_bar("Mana", 11)
        self._init_bar("Stamina", 9)
        self._init_bar("Fatigue", 20)
        self._init_bar("Intox", 10)
        self._init_bar("Soaked", 6)
        self._init_bar("Stuffed", 10)

        self.app.register_event_handler("on_vitals_update", self.update_vitals)

    def _init_bar(self, name, max_value):
        label = QLabel(name)
        bar = QProgressBar()
        bar.setMaximum(max_value)
        bar.setTextVisible(False)

        bar.setStyleSheet("""
            QProgressBar {
                min-height: 18px;
                max-height: 18px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                margin: 1px;
            }
        """)

        self.layout.addWidget(label)
        self.layout.addWidget(bar)

        self.bars[name.lower()] = bar

    def update_vitals(self, data: dict):
        for key, bar in self.bars.items():
            value = data.get(key)
            if isinstance(value, int):
                max_value = bar.maximum()
                update_bar(bar, value, max_value)


def value_to_color(value: int, max_value: int) -> str:
    if max_value <= 0:
        return "#cc0000"  # fallback for invalid max

    ratio = max(0.0, min(1.0, value / max_value))  # Clamp to [0, 1]

    if ratio >= 0.66:
        # High → Green
        blend_ratio = (ratio - 0.66) / (1.0 - 0.66)
        return interpolate_color("#ffcc00", "#00cc00", blend_ratio)  # yellow → green
    elif ratio >= 0.33:
        # Mid → Yellow
        blend_ratio = (ratio - 0.33) / (0.66 - 0.33)
        return interpolate_color("#ff6600", "#ffcc00", blend_ratio)  # orange → yellow
    else:
        # Low → Red
        blend_ratio = ratio / 0.33
        return interpolate_color("#cc0000", "#ff6600", blend_ratio)  # red → orange


def interpolate_color(start_hex: str, end_hex: str, blend_ratio: float) -> str:
    blend_ratio = max(0.0, min(1.0, blend_ratio))
    start_value = [int(start_hex[i:i + 2], 16) for i in (1, 3, 5)]
    end_value = [int(end_hex[i:i + 2], 16) for i in (1, 3, 5)]
    result = [int(start_value[i] + (end_value[i] - start_value[i]) * blend_ratio) for i in range(3)]
    return f"#{result[0]:02x}{result[1]:02x}{result[2]:02x}"


def update_bar(bar: QProgressBar, value: int, max_value: int):
    bar.setMaximum(max_value)
    bar.setValue(value)

    color = value_to_color(value, max_value)
    bar.setStyleSheet(f"""
        QProgressBar {{
            min-height: 18px;
            max-height: 18px;
            border: 1px solid #555;
            border-radius: 3px;
            background-color: #222;
        }}
        QProgressBar::chunk {{
            background-color: {color};
            margin: 1px;
        }}
    """)
