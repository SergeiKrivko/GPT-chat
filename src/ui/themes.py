import os
import shutil

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QWidget, QMainWindow, QLineEdit, QTextEdit, QScrollArea, QPushButton, QSpinBox, \
    QDoubleSpinBox, QComboBox, QProgressBar, QTabWidget, QListWidget, QCheckBox, QLabel, QTabBar, QTreeWidget, QMenu, \
    QSlider
import PIL.Image as Image

from src.ui.button import Button
from src.ui.resources import resources

basic_theme = {
    'MainColor': '#FFFFFF',
    'MainHoverColor': '#C9CBCF',
    'MainSelectedColor': '#4BA4FC',
    'BgColor': '#DFE1E3',
    'BgHoverColor': '#CBCDCF',
    'BgSelectedColor': '#5283C9',
    'MenuColor': '#F7F8FA',
    'MenuHoverColor': '#DFE1E5',
    'MenuSelectedColor': '#3573F0',
    'BorderColor': '#BFC0C2',
    'TextColor': '#222222',
    'ImageColor': (25, 28, 66),

    'FontFamily': "Calibri",
    'CodeFontFamily': "Consolas",
}


class Theme:
    def __init__(self, theme_data):
        self.theme_data = theme_data

    def get(self, key):
        return self.theme_data.get(key, basic_theme.get(key))

    def __getitem__(self, item):
        return self.get(item)

    def code_colors(self, lexer):
        if lexer in self.theme_data:
            for key, item in basic_theme[lexer].items():
                yield key, self.theme_data[lexer].get(key, item)
        else:
            return basic_theme[lexer].items()


class ThemeManager:
    BASIC_THEME = 'light'

    def __init__(self, sm, theme_name='basic'):
        self.sm = sm
        self.themes = {
            ThemeManager.BASIC_THEME: Theme(basic_theme),
            'dark':
                Theme({
                    'MainColor': '#2B2D30',
                    'MainHoverColor': '#3E4145',
                    'MainSelectedColor': '#2E436E',
                    'BgColor': '#141517',
                    'BgHoverColor': '#222345',
                    'BgSelectedColor': '#323466',
                    'MenuColor': '#1F2024',
                    'MenuHoverColor': '#4E5157',
                    'MenuSelectedColor': '#3574F0',
                    'BorderColor': '#474747',
                    'TextColor': '#F0F0F0',
                    'ImageColor': (250, 250, 250),
                }),
            'fresh':
                Theme({
                    'MainColor': '#D2D79F',
                    'MainHoverColor': '#BAD78C',
                    'MainSelectedColor': '#A3CF63',
                    'BgColor': '#90B77D',
                    'BgHoverColor': '#9FC98A',
                    'BgSelectedColor': '#73C978',
                    'MenuColor': '#539667',
                    'MenuHoverColor': '#4C8A5F',
                    'MenuSelectedColor': '#4D8A51',
                    'BorderColor': '#39703A',
                    'TextColor': '#403232',
                    'ImageColor': (64, 50, 50),
                }),
            'coffee':
                Theme({
                    'MenuColor': '#D9B28D',
                    'MenuHoverColor': '#E0BB9D',
                    'MenuSelectedColor': '#E8C3B0',
                    'BgColor': '#D7B19D',
                    'BgHoverColor': '#CCA895',
                    'BgSelectedColor': '#BD9A8A',
                    'MainColor': '#946949',
                    'MainHoverColor': '#9C6242',
                    'MainSelectedColor': '#AB6B49',
                    'BorderColor': '#6B432E',
                    'TextColor': '#402218',
                    'ImageColor': (64, 34, 24),
                }),
            'night':
                Theme({
                    'MainColor': '#634378',
                    'MainHoverColor': '#4E4378',
                    'MainSelectedColor': '#703673',
                    'BgColor': '#250230',
                    'BgHoverColor': '#330342',
                    'BgSelectedColor': '#47045C',
                    'MenuColor': '#470246',
                    'MenuHoverColor': '#570355',
                    'MenuSelectedColor': '#70046E',
                    'BorderColor': '#9C0499',
                    'TextColor': '#EDBFF2',
                    'ImageColor': (237, 191, 242),
                }),
            'orange':
                Theme({
                    'MainColor': '#F2D7AD',
                    'MainHoverColor': '#F2CE9C',
                    'MainSelectedColor': '#FFCB99',
                    'BgColor': '#F0F0F0',
                    'BgHoverColor': '#E3D2C8',
                    'BgSelectedColor': '#E3C3AE',
                    'MenuColor': '#F28B41',
                    'MenuHoverColor': '#E3823D',
                    'MenuSelectedColor': '#E0651B',
                    'BorderColor': '#F26510',
                    'TextColor': '#000000',
                    'ImageColor': (217, 126, 29),
                }),
            'flamingo':
                Theme({
                    'MainColor': '#F0C6F2',
                    'MainHoverColor': '#E6ACE5',
                    'MainSelectedColor': '#D6A0D5',
                    'BgColor': '#FFFFFF',
                    'BgHoverColor': '#F3DEF7',
                    'BgSelectedColor': '#F3C6F7',
                    'MenuColor': '#DEA7F2',
                    'MenuHoverColor': '#DC9CF2',
                    'MenuSelectedColor': '#D67CF2',
                    'BorderColor': '#93699E',
                    'TextColor': '#2F1233',
                    'ImageColor': (47, 18, 51),
                }),
            'space':
                Theme({
                    'MainColor': '#292E3D',
                    'MainHoverColor': '#23233D',
                    'MainSelectedColor': '#20204D',
                    'BgColor': '#111129',
                    'BgHoverColor': '#1C1C42',
                    'BgSelectedColor': '#2E2E6B',
                    'MenuColor': '#191B4D',
                    'MenuHoverColor': '#212463',
                    'MenuSelectedColor': '#303491',
                    'BorderColor': '#07093B',
                    'TextColor': '#F0F0F0',
                    'ImageColor': (240, 240, 240),
                }),
            'christmas':
                Theme({
                    'MainColor': '#FFDBD7',
                    'MainHoverColor': '#E8C7C4',
                    'MainSelectedColor': '#E88C8C',
                    'BgColor': '#FFF5E0',
                    'BgHoverColor': '#FFD6C8',
                    'BgSelectedColor': '#E3968A',
                    'MenuColor': '#E6726C',
                    'MenuHoverColor': '#B84643',
                    'MenuSelectedColor': '#BA0F0F',
                    'BorderColor': '#A62121',
                    'TextColor': '#101838',
                    'ImageColor': (16, 24, 56),
                }),
            'winter':
                Theme({
                    'MainColor': '#B4D2FA',
                    'MainHoverColor': '#93BBFA',
                    'MainSelectedColor': '#4BA7FA',
                    'BgColor': '#EEEEEE',
                    'BgHoverColor': '#D1D1D1',
                    'BgSelectedColor': '#7798C7',
                    'MenuColor': '#7798C7',
                    'MenuHoverColor': '#5787C7',
                    'MenuSelectedColor': '#2971C7',
                    'BorderColor': '#3E5875',
                    'TextColor': '#191C42',
                    'ImageColor': (25, 28, 66),
                }),
        }

        self.theme_name = ''
        self.theme = None
        self.style_sheet = ''
        self.bg_style_sheet = ''
        self.set_theme(theme_name)

    def __getitem__(self, item):
        return self.theme.get(item)

    @staticmethod
    def shift(palette):
        if palette == 'Bg':
            return 'Main'
        if palette == 'Main':
            return 'Menu'
        if palette == 'Menu':
            return 'Bg'

    def get(self, item):
        return self.theme.get(item)

    def code_colors(self, lexer):
        return self.theme.code_colors(lexer)

    def set_theme_to_list_widget(self, widget, font=None, palette='Main', border=True, border_radius=True):
        # widget.setFocusPolicy(False)
        widget.setStyleSheet(self.list_widget_css(palette, border, border_radius))
        for i in range(widget.count()):
            item = widget.item(i)
            if hasattr(item, 'set_theme'):
                item.set_theme()
            else:
                item.setFont(font if font else self.font_medium)

    def auto_css(self, widget: QWidget, code_font=False, palette='Main', border=True, border_radius=True, padding=False):
        if code_font:
            widget.setFont(self.code_font)
        else:
            widget.setFont(self.font_medium)

        if isinstance(widget, QMainWindow):
            widget.setStyleSheet(self.bg_style_sheet)
        elif isinstance(widget, QComboBox):
            widget.setStyleSheet(self.combobox_css(palette))
        elif isinstance(widget, QLineEdit):
            widget.setStyleSheet(self.base_css(palette, border, border_radius))
        elif isinstance(widget, QTextEdit):
            widget.setStyleSheet(self.text_edit_css(palette, border))
        elif isinstance(widget, QTreeWidget):
            widget.setStyleSheet(self.tree_widget_css(palette, border, border_radius))
        elif isinstance(widget, QScrollArea):
            widget.setStyleSheet(self.scroll_area_css(palette, border))
        elif isinstance(widget, Button):
            widget.set_theme(tm=self)
        elif isinstance(widget, QPushButton):
            widget.setStyleSheet(self.button_css(palette, border, border_radius, padding))
        elif isinstance(widget, QLabel):
            widget.setStyleSheet('border: none;')
        elif isinstance(widget, QSpinBox):
            widget.setStyleSheet(self.spinbox_css(palette))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setStyleSheet(self.double_spinbox_css(palette))
        elif isinstance(widget, QProgressBar):
            widget.setStyleSheet(self.progress_bar_css(palette))
        elif isinstance(widget, QTabBar):
            widget.setStyleSheet(self.tab_bar_css(palette))
        elif isinstance(widget, QTabWidget):
            widget.setStyleSheet(self.tab_widget_css(palette))
        elif isinstance(widget, QListWidget):
            self.set_theme_to_list_widget(widget, palette=palette, border=border, border_radius=border_radius)
        elif isinstance(widget, QCheckBox):
            widget.setStyleSheet(self.checkbox_css(palette))
        elif isinstance(widget, QMenu):
            widget.setStyleSheet(self.menu_css(palette))
        elif isinstance(widget, QSlider):
            widget.setStyleSheet(self.slider_css(palette))

    def set_theme(self, theme_name):
        self.theme_name = theme_name
        self.clear_images()
        if theme_name not in self.themes:
            self.theme_name = ThemeManager.BASIC_THEME
        self.theme = self.themes.get(theme_name, self.themes[ThemeManager.BASIC_THEME])
        self.font_small = QFont(self.get('FontFamily'), 10)
        self.font_medium = QFont(self.get('FontFamily'), 11)
        self.font_big = QFont(self.get('FontFamily'), 14)
        self.code_font_std = QFont(self.get('CodeFontFamily'), 10)
        self.code_font = QFont(self.get('CodeFontFamily'), 11)
        self.bg_style_sheet = f"color: {self['TextColor']};\n" \
                              f"background-color: {self['BgColor']};"

    def scintilla_css(self, border=False):
        return f"""
QsciScintilla {{
    background-color: {self['Paper'].name()};
    border: {'1' if border else '0'}px solid {self['BorderColor']};
    background-color: {self['Paper'].name()};
}}
QsciScintilla QScrollBar:vertical {{
    background: {self['Paper'].name()};
    width: 12px;
    margin: 0px;
}}
QsciScintilla QScrollBar::handle::vertical {{
    background-color: {self['BorderColor']};
    margin: 2px 2px 2px 6px;
    border-radius: 2px;
    min-height: 20px;
}}
QsciScintilla QScrollBar::handle::vertical:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QsciScintilla QScrollBar::sub-page, QScrollBar::add-page {{
    background: none;
}}
QsciScintilla QScrollBar::sub-line, QScrollBar::add-line {{
    background: none;
    height: 0px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
{self.menu_css()}"""

    def list_widget_css(self, palette, border=True, border_radius=True):
        return f"""
QListWidget {{
    {self.base_css(palette, border, border_radius)}
}}
QListWidget::item {{
    border-radius: 6px;
}}
QListWidget::item:hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QListWidget::item:selected {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}SelectedColor']};
    border-radius: 6px;
}}
QListWidget QScrollBar:vertical {{
    background: {self[f'{palette}Color']};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    width: 12px;
    margin: 0px;
}}
QListWidget QScrollBar:horizontal {{
    background: {self[f'{palette}Color']};
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    height: 12px;
    margin: 0px;
}}
QListWidget QScrollBar::handle::vertical {{
    background-color: {self['BorderColor']};
    margin: 2px 2px 2px 6px;
    border-radius: 2px;
    min-height: 20px;
}}
QListWidget QScrollBar::handle::vertical:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QListWidget QScrollBar::handle::horizontal {{
    background-color: {self['BorderColor']};
    margin: 6px 2px 2px 2px;
    border-radius: 2px;
    min-width: 20px;
}}
QListWidget QScrollBar::handle::horizontal:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QListWidget QScrollBar::sub-page, QScrollBar::add-page {{
    background: none;
}}
QListWidget QScrollBar::sub-line, QScrollBar::add-line {{
    background: none;
    height: 0px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
"""

    def tree_widget_css(self, palette, border=True, border_radius=True):
        return f"""
QTreeWidget {{
    {self.base_css(palette, border, border_radius)}
}}
QTreeView {{
    show-decoration-selected: 1;
}}
QTreeWidget::item {{
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}
QTreeWidget::item:hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QTreeWidget::item:selected {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}SelectedColor']};
}}

QTreeView::branch {{
    background-color: {self[f'{palette}Color']};
}}
QTreeView::branch:hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QTreeView::branch::selected {{
    border-top-left-radius: 6px;
    border-bottom-left-radius: 6px;
    background-color: {self[f'{palette}SelectedColor']};
}}

QTreeView::branch:closed:has-children {{
        image: url({self.get_image('right_arrow')});
}}
QTreeView::branch:open:has-children {{
        image: url({self.get_image('down_arrow')});
}}

QTreeWidget QScrollBar:vertical {{
    background: {self[f'{palette}Color']};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    width: 12px;
    margin: 0px;
}}
QTreeWidget QScrollBar:horizontal {{
    background: {self[f'{palette}Color']};
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    height: 12px;
    margin: 0px;
}}
QTreeWidget QScrollBar::handle::vertical {{
    background-color: {self['BorderColor']};
    margin: 2px 2px 2px 6px;
    border-radius: 2px;
    min-height: 20px;
}}
QTreeWidget QScrollBar::handle::vertical:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QTreeWidget QScrollBar::handle::horizontal {{
    background-color: {self['BorderColor']};
    margin: 6px 2px 2px 2px;
    border-radius: 2px;
    min-width: 20px;
}}
QTreeWidget QScrollBar::handle::horizontal:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QTreeWidget QScrollBar::sub-page, QScrollBar::add-page {{
    background: none;
}}
QTreeWidget QScrollBar::sub-line, QScrollBar::add-line {{
    background: none;
    height: 0px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
"""

    def base_css(self, palette='Bg', border=True, border_radius=True):
        return f"color: {self['TextColor']};\n" \
               f"background-color: {self[f'{palette}Color']};\n" \
               f"border: {'1' if border else '0'}px solid {self['BorderColor']};\n" \
               f"border-radius: {'4' if border_radius else '0'}px;"

    def scroll_area_css(self, palette, border=True):
        return f"""
QScrollArea {{
    {self.base_css(palette, border)}
}}
QScrollArea QScrollBar:vertical {{
    background: {self[f'{palette}Color']};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    width: 12px;
    margin: 0px;
}}
QScrollArea QScrollBar:horizontal {{
    background: {self[f'{palette}Color']};
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    height: 12px;
    margin: 0px;
}}
QScrollArea QScrollBar::handle::vertical {{
    background-color: {self['BorderColor']};
    margin: 2px 2px 2px 6px;
    border-radius: 2px;
    min-height: 20px;
}}
QScrollArea QScrollBar::handle::vertical:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QScrollArea QScrollBar::handle::horizontal {{
    background-color: {self['BorderColor']};
    margin: 6px 2px 2px 2px;
    border-radius: 2px;
    min-width: 20px;
}}
QScrollArea QScrollBar::handle::horizontal:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QScrollArea QScrollBar::sub-page, QScrollBar::add-page {{
    background: none;
}}
QScrollArea QScrollBar::sub-line, QScrollBar::add-line {{
    background: none;
    height: 0px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
"""

    def text_edit_css(self, palette, border=True):
        return f"""
QTextEdit {{
    {self.base_css(palette, border)}
}}
QTextEdit QScrollBar:vertical {{
    background: {self[f'{palette}Color']};
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    width: 12px;
    margin: 0px;
}}
QTextEdit QScrollBar:horizontal {{
    background: {self[f'{palette}Color']};
    border-bottom-left-radius: 5px;
    border-bottom-right-radius: 5px;
    height: 12px;
    margin: 0px;
}}
QTextEdit QScrollBar::handle::horizontal {{
    background-color: {self['BorderColor']};
    margin: 6px 2px 2px 2px;
    border-radius: 2px;
    min-width: 20px;
}}
QTextEdit QScrollBar::handle::horizontal:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QTextEdit QScrollBar::handle::vertical {{
    background-color: {self['BorderColor']};
    margin: 2px 2px 2px 6px;
    border-radius: 2px;
    min-height: 20px;
}}
QTextEdit QScrollBar::handle::vertical:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QTextEdit QScrollBar::sub-page, QScrollBar::add-page {{
    background: none;
}}
QTextEdit QScrollBar::sub-line, QScrollBar::add-line {{
    background: none;
    height: 0px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
{self.menu_css(palette)}
"""

    def combobox_css(self, palette='Bg'):
        return f"""
QComboBox {{
    {self.base_css(palette)}
}}
QComboBox::hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QComboBox::drop-down:button {{
    border-radius: 5px;
}}
QComboBox::down-arrow {{
    image: url({self.get_image('down_arrow')});
}}
QComboBox QAbstractItemView {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}Color']};
    border: 1px solid {self['BorderColor']};
    selection-color: {self['TextColor']};
    selection-background-color: {self[f'{palette}HoverColor']};
    border-radius: 4px;
}}
QComboBox QScrollBar:vertical {{
    background-color: {self[f'{palette}Color']};
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    width: 12px;
    margin: 0px;
}}
QComboBox QScrollBar::handle::vertical {{
    background-color: {self['BorderColor']};
    margin: 2px 2px 2px 6px;
    border-radius: 2px;
    min-height: 20px;
}}
QComboBox QScrollBar::handle::vertical:hover {{
    margin: 2px;
    border-radius: 4px;
}}
QComboBox QScrollBar::sub-page, QScrollBar::add-page {{
    background: none;
}}
QComboBox QScrollBar::sub-line, QScrollBar::add-line {{
    background: none;
    height: 0px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
"""

    def progress_bar_css(self, palette='Bg'):
        return f"""
QProgressBar {{
color: {self['TextColor']};
background-color: {self[f'{self.shift(palette)}Color']};
border: 1px solid {self['BorderColor']};
border-radius: 4px;
text-align: center;
}}
QProgressBar::chunk {{
background-color: {self[f'{palette}Color']};
}}
"""

    def spinbox_css(self, palette='Bg'):
        return f"""
QSpinBox {{
    {self.base_css(palette)}
}}
QSpinBox::up-button {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}Color']};
    border-left: 1px solid {self['BorderColor']};
    border-bottom: 1px solid {self['BorderColor']};
    border-top-right-radius: 3px;
}}
QSpinBox::up-button::disabled {{
    border: 0px solid {self['BorderColor']};
}}
QSpinBox::up-button::hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QSpinBox::up-arrow {{
    image: url({self.get_image('up_arrow')});
}}
QSpinBox::down-button {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}Color']};
    border-left: 1px solid {self['BorderColor']};
    border-top: 1px solid {self['BorderColor']};
    border-bottom-right-radius: 3px;
}}
QSpinBox::down-button::disabled {{
    border: 0px solid {self['BorderColor']};
}}
QSpinBox::down-button::hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QSpinBox::down-arrow {{
    image: url({self.get_image('down_arrow')});
}}
QSpinBox::disabled {{
    color: {self['BgColor']};
    border-color: {self[f'{palette}Color']};
}}
"""

    def double_spinbox_css(self, palette='Bg'):
        return self.spinbox_css(palette=palette).replace('QSpinBox', 'QDoubleSpinBox')

    def button_css(self, palette='Bg', border=True, border_radius=True, padding=False, align='none'):
        return f"""
QPushButton {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}Color']};
    border: {'1' if border else '0'}px solid {self['BorderColor']};
    border-radius: {'5' if border_radius else '0'}px;
    {'padding: 3px 8px 3px 8px;' if padding else 'padding: 0px;'}
    text-align: {align};
}}
QPushButton::hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QPushButton::disabled {{
    color: {self['BgColor']};
    border-color: {self['MainColor']};
}}
QPushButton::checked {{
    background-color: {self[f'{palette}SelectedColor']};
}}
QPushButton::menu-indicator {{
    image: url({self.get_image('down_arrow')});
    subcontrol-origin: padding;
    padding-right: 5px;
    subcontrol-position: right;
}}
"""

    def tab_bar_css(self, palette='Main'):
        return f"""
QTabBar::tab {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}Color']};
    border-bottom-color: {self['TextColor']};
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    border: 1px solid {self['BorderColor']};
    width: 125px;
    padding: 4px;
}}
QTabBar::tab:hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QTabBar::tab:selected {{
    background-color: {self[f'{palette}SelectedColor']};
}}
QTabBar QToolButton {{
    background-color: {self[f'{palette}Color']};
    border: 1px solid {self['BorderColor']};
}}
QTabBar QToolButton::hover {{
    background-color: {self[f'{palette}HoverColor']};
}}
QTabBar QToolButton::right-arrow {{
    image: url({self.get_image('right_arrow')});
}}
QTabBar QToolButton::left-arrow {{
    image: url({self.get_image('left_arrow')});
}}
"""

    def tab_widget_css(self, palette='Main'):
        return f"""
QTabWidget::pane {{
    color: {self[f'{self.shift(palette)}Color']};
}}
{self.tab_bar_css(palette)}
"""

    def checkbox_css(self, palette='Main'):
        return f"""
QCheckBox::indicator {{
    width: 13px;
    height: 13px;
}}
QCheckBox::indicator:unchecked {{
    image: url({self.get_image('checkbox_unchecked')});
}}
QCheckBox::indicator:unchecked:hover {{
    image: url({self.get_image('checkbox_unchecked')});
}}
QCheckBox::indicator:unchecked:pressed {{
    image: url({self.get_image('checkbox_unchecked')});
}}
QCheckBox::indicator:checked {{
    image: url({self.get_image('checkbox')});
}}
QCheckBox::indicator:checked:hover {{
    image: url({self.get_image('checkbox')});
}}
QCheckBox::indicator:checked:pressed {{
    image: url({self.get_image('checkbox')});
}}"""

    def menu_css(self, palette='Bg'):
        return f"""
QMenu {{
    color: {self['TextColor']};
    background-color: {self[f'{palette}Color']};
    border: 1px solid {self['BorderColor']};
    border-radius: 6px;
    spacing: 4px;
    padding: 3px;
}}

QMenu::icon {{
    padding-left: 10px;
}}

QMenu::item {{
    border: 0px solid {self['BorderColor']};
    background-color: transparent;
    border-radius: 8px;
    padding: 4px 16px;
}}

QMenu::item:selected {{
    background-color: {self[f'{palette}HoverColor']};
}}
QMenu::separator {{
    height: 1px;
    background: {self['BorderColor']};
    margin: 4px 10px;
}}"""

    def slider_css(self, palette='Bg'):
        return f"""
QSlider {{
    height: 28;
}}
QSlider::groove:horizontal {{
    border: 1px solid {self['BorderColor']};
    height: 8px;
    background-color: {self[f'{palette}Color']};
    margin: 2px 0;
}}
QSlider::add-page:horizontal {{
    background: {self[f'{palette}Color']};
}}
QSlider::sub-page:horizontal {{
    background: {self[f'{palette}SelectedColor']};
}}
QSlider::handle:horizontal {{
    border: 1px solid {self['BorderColor']};
    background-color: {self[f'{palette}Color']};
    width: 8px;
    height: 26px;
    margin: -8px 0;
}}"""

    def get_image(self, name: str, default=None, color=None):
        if name not in resources and default is not None:
            name = default

        if color is None:
            color = self['ImageColor']
        elif isinstance(color, str):
            color = QColor(color)
            color = color.red(), color.green(), color.blue()
        elif isinstance(color, QColor):
            color = color.red(), color.green(), color.blue()

        path = f"{self.sm.app_data_dir}/images/{name}_{QColor(*color).name()}.png"
        if not os.path.isfile(path):
            os.makedirs(f"{self.sm.app_data_dir}/images", exist_ok=True)
            image = Image.frombytes(*resources[name])

            image = image.convert("RGBA")
            datas = image.getdata()
            new_data = []
            for item in datas:
                if item[0] == 255 and item[1] == 255 and item[2] == 255:
                    new_data.append((255, 255, 255, 0))
                elif item[0] == 0 and item[1] == 0 and item[2] == 0:
                    new_data.append(color)
                else:
                    new_data.append(item)
            image.putdata(new_data)

            image.save(path)

        return path

    def clear_images(self):
        if os.path.isdir(path := f"{self.sm.app_data_dir}/images"):
            shutil.rmtree(path)

    def add_custom_theme(self, theme_name, theme_data):
        self.themes[theme_name] = Theme(theme_data)
