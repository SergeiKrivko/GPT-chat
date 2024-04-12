import asyncio
import json
from time import time

from PyQt6.QtCore import QObject, pyqtSignal, QPoint, Qt, QPropertyAnimation, QEasingCurve, QSize, \
    QParallelAnimationGroup
from PyQt6.QtWidgets import QVBoxLayout, QApplication
from PyQtUIkit.widgets import *
from qasync import asyncSlot

from src import config
from src.gpt import gpt
from src.settings_manager import SettingsManager

MANAGER = None


class CheckModelsService(QObject):
    class ModelStatus:
        UPDATE = 0
        OK = 1
        FAIL = 2
        UNKNOWN = 3

    modelStatusUpdated = pyqtSignal(str, object)
    startUpdating = pyqtSignal()
    finishUpdating = pyqtSignal()

    def __init__(self, sm: SettingsManager):
        super().__init__()

        global MANAGER
        MANAGER = self

        self._sm = sm

        data: dict = json.loads(self._sm.get('models_status', '{}'))
        self._last_update = data.get('time', 0)
        self._last_version = data.get('version', '0.0.0')
        self._updating = False

        self._models = {key: item for key, item in data.get('models', dict()).items()}
        self._threads = dict()

    @property
    def updating(self):
        return self._updating

    @staticmethod
    def _message(model):
        try:
            gpt.simple_response([{'role': 'user', 'content': 'Hello!'}], model=model)
            return CheckModelsService.ModelStatus.OK
        except Exception:
            pass
        return CheckModelsService.ModelStatus.FAIL

    @asyncSlot()
    async def update(self):
        self.stop()
        self.startUpdating.emit()
        self._updating = True
        await asyncio.sleep(0.5)
        for model in gpt.get_models():
            self._run_model(model)
            self._set_model_status(model, CheckModelsService.ModelStatus.UPDATE)
            await asyncio.sleep(0.1)

    def stop(self):
        flag = False
        self._updating = False
        for model, el in self._threads.items():
            if not el.isFinished():
                el.terminate()
                flag = True
                self._set_model_status(model, CheckModelsService.ModelStatus.UNKNOWN)
        if flag:
            self.finishUpdating.emit()

    def _run_model(self, model):
        thread = self._sm.run_process(lambda: self._message(model), f'check-gpt-{model}')
        self._threads[model] = thread
        thread.finished.connect(lambda: self._set_model_status(model, thread.res))

    def _on_thead_finished(self, model: str, status: int):
        self._set_model_status(model, status)
        for el in self._threads.values():
            if not el.isFinished:
                return
        self.finishUpdating.emit()
        self._updating = False

    def _set_model_status(self, model: str, status: int):
        self._models[model] = status
        self.modelStatusUpdated.emit(model, status)
        self.save()

    def status(self, model):
        return self._models.get(model, CheckModelsService.ModelStatus.UNKNOWN)

    def save(self):
        self._sm.set('models_status', json.dumps({
            'time': time(),
            'version': config.APP_VERSION,
            'models': self._models,
        }))


class _ModelItem(KitLayoutButton):
    selected = pyqtSignal(object)

    def __init__(self, model: str):
        super().__init__()
        self.model = model
        self._value = model
        self.setCheckable(True)
        self.clicked.connect(self._on_clicked)
        self.border = 0
        self.radius = 6
        self.padding = 6, 3, 3, 3
        self.setFixedHeight(30)

        self._label = KitLabel(model)
        self.addWidget(self._label)

        self._spinner = KitSpinner()
        self._spinner.main_palette = 'Text'
        self._spinner.size = 24
        self._spinner.width = 3
        self.addWidget(self._spinner)

        self._icon_ok = KitIconWidget('line-checkmark')
        self._icon_ok.main_palette = 'Success'
        self._icon_ok.setFixedSize(24, 24)
        self._icon_ok.hide()
        self.addWidget(self._icon_ok)

        self._icon_fail = KitIconWidget('line-close')
        self._icon_fail.main_palette = 'Danger'
        self._icon_fail.setFixedSize(24, 24)
        self._icon_fail.hide()
        self.addWidget(self._icon_fail)

        self._icon_unknown = KitIconWidget('line-help')
        self._icon_unknown.setFixedSize(24, 24)
        self._icon_unknown.hide()
        self.addWidget(self._icon_unknown)

    def set_status(self, status):
        self._spinner.setHidden(status != CheckModelsService.ModelStatus.UPDATE)
        self._icon_ok.setHidden(status != CheckModelsService.ModelStatus.OK)
        self._icon_fail.setHidden(status != CheckModelsService.ModelStatus.FAIL)
        self._icon_unknown.setHidden(status != CheckModelsService.ModelStatus.UNKNOWN)

    def _on_clicked(self, flag):
        if not flag:
            self.setChecked(True)
        self.selected.emit(self)

    @property
    def value(self):
        return self._value


class ModelComboBox(KitHBoxLayout):
    currentIndexChanged = pyqtSignal(object)
    currentValueChanged = pyqtSignal(object)

    def __init__(self):
        if not isinstance(MANAGER, CheckModelsService):
            raise TypeError
        super().__init__()
        self.spacing = 3

        self.__widgets: list[_ModelItem] = []
        MANAGER.modelStatusUpdated.connect(self._on_model_status_updated)
        self.__current = None

        self._button = KitLayoutButton()
        self._button.setContentsMargins(3, 3, 3, 3)
        self.addWidget(self._button)
        self._button.setFixedHeight(28)

        self._label = KitLabel()
        self._button.addWidget(self._label)

        self.setContentsMargins(0, 0, 6, 0)
        self._arrow = KitIconWidget('line-chevron-down')
        self._arrow._use_text_only = False
        self._arrow.setFixedSize(16, 12)
        self._button.addWidget(self._arrow)

        self._update_button = KitIconButton('line-refresh')
        self._update_button.size = 28
        self._update_button.clicked.connect(lambda: MANAGER.update())
        self._update_button.setHidden(MANAGER.updating)
        self.addWidget(self._update_button)

        self._cancel_button = KitIconButton('line-ban')
        self._cancel_button.size = 28
        self._cancel_button.clicked.connect(MANAGER.stop)
        self._cancel_button.setHidden(not MANAGER.updating)
        self.addWidget(self._cancel_button)

        self.__menu = _ComboBoxMenu(self)
        self.__menu.setFixedWidth(self.width())
        self._button.clicked.connect(self._show_menu)

        MANAGER.startUpdating.connect(lambda: (self._update_button.hide(), self._cancel_button.show()))
        MANAGER.finishUpdating.connect(lambda: (self._update_button.show(), self._cancel_button.hide()))

        for el in gpt.get_models():
            item = _ModelItem(el)
            self.addItem(item)
            item.set_status(MANAGER.status(el))

    def _on_model_status_updated(self, model, status):
        for el in self.__widgets:
            if el.model == model:
                el.set_status(status)
                return

    def addItem(self, item: _ModelItem):
        item.selected.connect(self._on_item_selected)
        self.__widgets.append(item)
        self.__menu.add_item(item)
        if len(self.__widgets) == 1:
            self.setCurrentIndex(0)

    def clear(self):
        self.__widgets.clear()
        self.__menu.clear()
        self.__current = None
        self._label.setText('')

    def currentValue(self):
        if not self.__widgets:
            return None
        return self.__widgets[self.__current].value

    def setCurrentValue(self, value):
        for i, el in enumerate(self.__widgets):
            if el.value == value:
                self.setCurrentIndex(i)

    def setCurrentIndex(self, index):
        if self.__current is not None:
            self.__widgets[self.__current].setChecked(False)
        self.__current = index
        self.__widgets[self.__current].setChecked(True)

        if self.__current is not None:
            self._label.setText(self.__widgets[self.__current].model)
        self.currentValueChanged.emit(self.currentValue())
        self.currentIndexChanged.emit(self.__current)

    def _show_menu(self):
        pos = QPoint(0, self.height())
        self.__menu.open(self.mapToGlobal(pos))

    def _on_item_selected(self, item: _ModelItem):
        self.setCurrentIndex(self.__widgets.index(item))
        self.__menu.close()

    def _set_tm(self, tm):
        super()._set_tm(tm)
        self.__menu._set_tm(tm)

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.__menu.setFixedWidth(self.width())

    def _apply_theme(self):
        if not self._tm or not self._tm.active:
            return
        super()._apply_theme()
        self.__menu._apply_theme()


class _ComboBoxMenu(KitMenu):
    def __init__(self, parent):
        super().__init__(parent)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(2, 2, 1, 2)
        self.setLayout(main_layout)

        self._scroll_area = KitScrollArea()
        main_layout.addWidget(self._scroll_area)

        self._scroll_layout = KitVBoxLayout()
        self._scroll_layout.setContentsMargins(3, 3, 3, 3)
        self._scroll_layout.setSpacing(2)
        self._scroll_area.setWidget(self._scroll_layout)

        self._height = 10
        self.__anim = None
        self.__pos = QPoint(0, 0)

    def _resize(self):
        self._height = 26 * min(12, self._scroll_layout.count()) + 8
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if
                                                     self._scroll_layout.count() > 12 else
                                                     Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.resize(self.width(), self._height)

    def _set_tm(self, tm):
        super()._set_tm(tm)
        self._scroll_area._set_tm(tm)

    def add_item(self, item: KitComboBoxItem):
        self._scroll_layout.addWidget(item)
        self._resize()

    def delete_item(self, index):
        self._scroll_layout.deleteWidget(index)

    def clear(self) -> None:
        self._scroll_layout.clear()

    def _apply_theme(self):
        if not self._tm or not self._tm.active:
            return
        super()._apply_theme()
        self._scroll_area._apply_theme()

    def open(self, pos: QPoint, type=1):
        self.__pos = pos
        screen_size = QApplication.primaryScreen().size()
        target_pos = pos - QPoint(0, 0 if type == 1 else self._height // 2)
        if target_pos.y() < 20:
            target_pos.setY(20)
        elif target_pos.y() + self._height > screen_size.height() - 20:
            target_pos.setY(screen_size.height() - self._height - 20)
        self.move(pos)
        self.resize(self.width(), 0)

        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setEndValue(target_pos)
        pos_anim.setDuration(200)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        height_anim = QPropertyAnimation(self, b"size")
        height_anim.setEndValue(QSize(self.width(), self._height))
        height_anim.setDuration(200)
        height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.__anim = QParallelAnimationGroup()
        self.__anim.addAnimation(pos_anim)
        self.__anim.addAnimation(height_anim)
        self.__anim.start()

        self.exec()
