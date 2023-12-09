import os
from uuid import uuid4

import matplotlib.pyplot as plt


_fig = None


class _LatexImage:
    def __init__(self, formula, path):
        self.formula = formula
        self.path = path
        self.count = 1

    def add(self):
        self.count += 1

    def delete(self):
        self.count -= 1
        if self.count <= 0:
            _images.pop(self)


_images: dict[str: _LatexImage] = dict()


def render_latex(sm, tm, latex: str):
    if latex in _images:
        image = _images[latex]
        image.count += 1
        return image.path

    global _fig
    if _fig is None:
        _fig = plt.figure()
    # Создание области отрисовки
    _fig.clear()
    _fig.set_facecolor("#00000000")
    ax = _fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    # Отрисовка формулы
    t = ax.text(0.5, 0.5, f"${latex}$",
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=14, color=tm['TextColor'])

    # Определение размеров формулы
    ax.figure.canvas.draw()
    bbox = t.get_window_extent()

    # Установка размеров области отрисовки
    _fig.set_size_inches(bbox.width / 100, bbox.height / 100)  # dpi=80

    os.makedirs(f"{sm.app_data_dir}/temp", exist_ok=True)
    image_id = uuid4()
    path = f"{sm.app_data_dir}/temp/{image_id}.svg"
    plt.savefig(path)
    _images[latex] = _LatexImage(latex, path)
    return path


def delete_image(formula):
    _images[formula].delete()
