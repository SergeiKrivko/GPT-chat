from PyQtUIkit.core import KitFont
from PyQtUIkit.themes import KitTheme, builtin_themes, KitPalette

_LIGHT = KitTheme({
    'Transparent': KitPalette('#00000000', '#30000000', '#60000000', '#222222'),
    'GptMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #A1A1A1, stop:1 #D5D5D5)', text='#222222'),
    'LastMessage': KitPalette('#00000000', text='#4D4D4D'),
    'FontSizeSmall': 9,
    'FontSizeMedium': 11,
    'FontSizeBig': 14,
    'FontSizeMono': 10,
}, {
    'default': KitFont('Roboto', 9, 11, 14, 20),
    'italic': KitFont('Roboto', 9, 11, 14, 20, italic=True),
    'bold': KitFont('Roboto', 9, 11, 14, 20, bold=True),
    'strike': KitFont('Roboto', 9, 11, 14, 20, strike=True),
    'mono': KitFont('Roboto Mono', 9, 11, 14, 20)
}, inherit=builtin_themes['Light'])

_DARK = KitTheme({
    'GptMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #18191C, stop:1 #2A2B30)', text='#F0F0F0'),
    'LastMessage': KitPalette('#00000000', text='#999999'),
    'FontSizeSmall': 9,
    'FontSizeMedium': 11,
    'FontSizeBig': 14,
    'FontSizeMono': 10,
}, {
    'default': KitFont('Roboto', 9, 11, 14, 20),
    'italic': KitFont('Roboto', 9, 11, 14, 20, italic=True),
    'bold': KitFont('Roboto', 9, 11, 14, 20, bold=True),
    'strike': KitFont('Roboto', 9, 11, 14, 20, strike=True),
    'mono': KitFont('Roboto Mono', 9, 11, 14, 20)
}, inherit=builtin_themes['Dark'])

THEMES = {
    'light_blue': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3F76BF, stop:1 #3B97CF)',
                                  text='#222222'),
        'Main': KitPalette('#FFFFFF', '#DFE1E5', '#3B97CF', '#222222'),
        'Bg': KitPalette('#D0D8DB', '#A8A9AB', '#3B97CF', '#222222'),
        'Border': KitPalette('#BFC0C2', '#A6A7A8', '#3B97CF', '#222222'),
    }, inherit=_LIGHT),
    'light_green': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #377D2A, stop:1 #72B238)',
                                  text='#222222'),
        'Main': KitPalette('#FFFFFF', '#DFE1E5', '#67A132', '#222222'),
        'Bg': KitPalette('#D0D8DB', '#A8A9AB', '#67A132', '#222222'),
        'Border': KitPalette('#BFC0C2', '#A6A7A8', '#67A132', '#222222'),
    }, inherit=_LIGHT),
    'light_red': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F23C18, stop:1 #F26149)',
                                  text='#222222'),
        'Main': KitPalette('#FFFFFF', '#DFE1E5', '#F23C18', '#222222'),
        'Bg': KitPalette('#D0D8DB', '#A8A9AB', '#F23C18', '#222222'),
        'Border': KitPalette('#BFC0C2', '#A6A7A8', '#F23C18', '#222222'),
    }, inherit=_LIGHT),
    'light_pink': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #C25EBD, stop:1 #C086C2)',
                                  text='#222222'),
        'Main': KitPalette('#FFFFFF', '#DFE1E5', '#C25EBD', '#222222'),
        'Bg': KitPalette('#D0D8DB', '#A8A9AB', '#C25EBD', '#222222'),
        'Border': KitPalette('#BFC0C2', '#A6A7A8', '#C25EBD', '#222222'),
    }, inherit=_LIGHT),
    'light_orange': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #C9650C, stop:1 #E38710)',
                                  text='#222222'),
        'GptMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #A3A3A3, stop:1 #E0E0E0)',
                                 text='#222222'),
        'Main': KitPalette('#FFFFFF', '#DFE1E5', '#E37412', '#222222'),
        'Bg': KitPalette('#D0D8DB', '#A8A9AB', '#E37412', '#222222'),
        'Border': KitPalette('#BFC0C2', '#A6A7A8', '#E37412', '#222222'),
    }, inherit=_LIGHT),

    'dark_blue': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #264773, stop:1 #3C72B8)',
                                  text='#F0F0F0'),
        'Main': KitPalette('#2B2D30', '#3E4145', '#264773', '#F0F0F0'),
        'Bg': KitPalette('#141517', '#4E5157', '#264773', '#F0F0F0'),
        'Border': KitPalette('#474747', '#595959', '#264773', '#F0F0F0'),
    }, inherit=_DARK),
    'dark_green': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #24521C, stop:1 #489632)',
                                  text='#F0F0F0'),
        'Main': KitPalette('#2B2D30', '#3E4145', '#306E25', '#F0F0F0'),
        'Bg': KitPalette('#141517', '#4E5157', '#306E25', '#F0F0F0'),
        'Border': KitPalette('#474747', '#595959', '#306E25', '#F0F0F0'),
    }, inherit=_DARK),
    'dark_red': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #B81818, stop:1 #B83D25)',
                                  text='#F0F0F0'),
        'Main': KitPalette('#2B2D30', '#3E4145', '#B81818', '#F0F0F0'),
        'Bg': KitPalette('#141517', '#4E5157', '#B81818', '#F0F0F0'),
        'Border': KitPalette('#474747', '#595959', '#B81818', '#F0F0F0'),
    }, inherit=_DARK),
    'dark_pink': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #75165F, stop:1 #B32291)',
                                  text='#F0F0F0'),
        'Main': KitPalette('#2B2D30', '#3E4145', '#75165F', '#F0F0F0'),
        'Bg': KitPalette('#141517', '#4E5157', '#75165F', '#F0F0F0'),
        'Border': KitPalette('#474747', '#595959', '#75165F', '#F0F0F0'),
    }, inherit=_DARK),
    'dark_orange': KitTheme({
        'UserMessage': KitPalette('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #B25B15, stop:1 #B28F32)',
                                  text='#F0F0F0'),
        'Main': KitPalette('#2B2D30', '#3E4145', '#B25B15', '#F0F0F0'),
        'Bg': KitPalette('#141517', '#4E5157', '#B25B15', '#F0F0F0'),
        'Border': KitPalette('#474747', '#595959', '#B25B15', '#F0F0F0'),
    }, inherit=_DARK),
}
