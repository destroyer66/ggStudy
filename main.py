import os
import sys
import platform

# 强制使用sdl2作为后端，因为它支持透明和无边框效果较好
os.environ['KIVY_WINDOW'] = 'sdl2'

from kivy.config import Config
# 尝试设置透明位
Config.set('graphics', 'multisamples', '4') # 开启抗锯齿
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '50')
Config.set('graphics', 'width', '80')
Config.set('graphics', 'height', '300')
Config.set('graphics', 'always_on_top', '1')
# 开启针对透明窗口的特殊提示
Config.set('graphics', 'shaped', '1')
# 禁用多点触控模拟（防止右键点击出现红点）
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Line, Rectangle, Canvas, Mesh
from kivy.core.window import Window
from kivy.properties import StringProperty, ListProperty, BooleanProperty, NumericProperty
from kivy.metrics import dp
from kivy.clock import Clock

def make_window_transparent():
    """使用 Windows API 强制窗口透明"""
    if platform.system() != 'Windows':
        return

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    
    # 查找窗口
    # Kivy 默认标题是 "SideMenu"
    hwnd = user32.FindWindowW(None, "SideMenu")
    if not hwnd:
        # 如果找不到，尝试枚举
        def enum_windows_proc(h, lParam):
            if user32.IsWindowVisible(h):
                length = user32.GetWindowTextLengthW(h)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(h, buff, length + 1)
                if "SideMenu" in buff.value:
                    nonlocal hwnd
                    hwnd = h
                    return False
            return True
        
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        EnumWindows(EnumWindowsProc(enum_windows_proc), 0)

    if hwnd:
        # 设置为层叠窗口
        # GWL_EXSTYLE = -20, WS_EX_LAYERED = 0x00080000
        ex_style = user32.GetWindowLongW(hwnd, -20)
        user32.SetWindowLongW(hwnd, -20, ex_style | 0x00080000)
        
        # LWA_COLORKEY = 0x00000001, LWA_ALPHA = 0x00000002
        # 将特定的黑色 (0,0,1) 设置为透明键 (0x010000)
        # 同时设置全局半透明度，例如 200 (255为全不透明)
        # 标志位设为 0x03 (0x01 | 0x02) 即同时启用颜色键和 Alpha 透明
        user32.SetLayeredWindowAttributes(hwnd, 0x010000, 200, 3)

class RoundButton(ButtonBehavior, FloatLayout):
    icon_type = StringProperty('scissor') # 'scissor', 'whiteboard', 'album'
    # bg_color 为基础渐变起始色
    base_color = ListProperty([0.2, 0.6, 1, 0.7]) # 增加半透明度
    hovered = BooleanProperty(False)
    scale = NumericProperty(1.0)
    
    def __init__(self, **kwargs):
        super(RoundButton, self).__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(60), dp(60)) # 减小按钮尺寸
        
        # 初始绑定悬停检测
        Window.bind(mouse_pos=self.on_mouse_pos)
        
        # 绘制逻辑
        self.update_canvas()
        
        self.bind(pos=self.update_canvas, size=self.update_canvas, hovered=self.update_canvas, scale=self.update_canvas)
        
        # 添加图标图片
        icon_path = os.path.join('assets', f'{self.icon_type}.png')
        self.icon = Image(
            source=icon_path, 
            size_hint=(None, None), 
            size=(dp(32), dp(32)), # 缩小图标尺寸
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.icon)

    def on_mouse_pos(self, window, pos):
        # 转换坐标并检查是否在按钮内
        if self.collide_point(*self.to_widget(*pos)):
            if not self.hovered:
                self.hovered = True
                self.animate_hover(True)
        else:
            if self.hovered:
                self.hovered = False
                self.animate_hover(False)

    def animate_hover(self, is_hover):
        from kivy.animation import Animation
        if is_hover:
            Animation(scale=1.1, duration=0.2, t='out_quad').start(self)
        else:
            Animation(scale=1.0, duration=0.2, t='out_quad').start(self)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # 计算缩放后的位置和大小
            w, h = self.size[0] * self.scale, self.size[1] * self.scale
            cx, cy = self.center
            new_pos = (cx - w/2, cy - h/2)
            new_size = (w, h)

            # 绘制阴影 (稍微向外扩散一点，模拟柔和边缘)
            Color(0, 0, 0, 0.15)
            Ellipse(pos=(new_pos[0]+1.5, new_pos[1]-1.5), size=(new_size[0]+1, new_size[1]+1))

            # 绘制主圆 (使用稍微大一点点的大小来平滑边缘)
            r, g, b, a = self.base_color
            
            # 底层边缘平滑 (用极低透明度画一层稍大的圆)
            Color(r, g, b, a * 0.3)
            Ellipse(pos=(new_pos[0]-0.5, new_pos[1]-0.5), size=(new_size[0]+1, new_size[1]+1))

            # 底色
            Color(r*0.8, g*0.8, b*0.8, a) 
            Ellipse(pos=new_pos, size=new_size)
            
            # 中间渐变
            Color(r, g, b, a)
            Ellipse(pos=(new_pos[0], new_pos[1]+dp(2)), size=(new_size[0], new_size[1]-dp(2)))
            
            # 顶部高光
            Color(1, 1, 1, 0.35)
            Ellipse(pos=(new_pos[0]+new_size[0]*0.2, new_pos[1]+new_size[1]*0.5), 
                    size=(new_size[0]*0.6, new_size[1]*0.4))

            # 如果悬停，增加外发光感
            if self.hovered:
                Color(1, 1, 1, 0.3)
                Line(ellipse=(new_pos[0]-1, new_pos[1]-1, new_size[0]+2, new_size[1]+2), width=1.2)

    def show_exit_confirmation(self):
        """弹出退出确认对话框"""
        # 为了满足“独立窗口”的要求，在 Windows 上我们直接使用系统的 MessageBoxW。
        # 这样对话框就是系统原生的独立窗口，且自动居中，不影响主应用窗口。
        if platform.system() == "Windows":
            import ctypes
            # MB_OKCANCEL = 1, MB_ICONQUESTION = 0x20, IDOK = 1
            result = ctypes.windll.user32.MessageBoxW(
                None, 
                "确定要退出应用吗？", 
                "退出确认", 
                0x00000001 | 0x00000020 | 0x00001000 # MB_OKCANCEL | MB_ICONQUESTION | MB_SYSTEMMODAL
            )
            if result == 1: # IDOK
                App.get_running_app().stop()
        else:
            # 非 Windows 平台（如 Android）保留 Kivy 原生 Popup
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.label import Label
            from kivy.uix.button import Button
            
            # 在 Android 上，默认字体通常是 Roboto，但为了支持中文，我们尝试寻找系统字体
            chinese_font = None
            font_paths = [
                "/system/fonts/DroidSansFallback.ttf",
                "/system/fonts/NotoSansCJK-Regular.ttc",
                "/system/fonts/SourceHanSansCN-Regular.otf",
                "DroidSansFallback.ttf"
            ]
            for path in font_paths:
                if os.path.exists(path):
                    chinese_font = path
                    break

            content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
            content.add_widget(Label(text="确定要退出应用吗？", font_size=dp(16), font_name=chinese_font))
            
            btns = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(20))
            confirm_btn = Button(text="确定", background_color=[1, 0.4, 0.4, 1], font_name=chinese_font)
            cancel_btn = Button(text="取消", font_name=chinese_font)
            
            btns.add_widget(confirm_btn)
            btns.add_widget(cancel_btn)
            content.add_widget(btns)
            
            popup = Popup(
                title="退出确认",
                title_font=chinese_font,
                content=content,
                size_hint=(None, None),
                size=(dp(280), dp(160))
            )
            confirm_btn.bind(on_release=lambda x: App.get_running_app().stop())
            cancel_btn.bind(on_release=lambda x: popup.dismiss())
            popup.open()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # 记录长按开始时间，用于 Android/移动端模拟右键功能（长按退出）
            touch.ud['start_time'] = Clock.get_time()
            
            if touch.button == 'right':
                if self.icon_type == 'album':
                    print("右键点击相册图标：准备弹出退出确认对话框")
                    self.show_exit_confirmation()
                return True
            return super(RoundButton, self).on_touch_down(touch)
        return False

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            # 检查是否是长按（针对 Android）
            if 'start_time' in touch.ud:
                duration = Clock.get_time() - touch.ud['start_time']
                # 长按超过 1 秒触发退出确认（仅针对相册按钮且非右键点击时，右键在 Windows 下由 down 处理）
                if duration > 1.0 and touch.button == 'left' and self.icon_type == 'album':
                    print("长按相册图标：准备弹出退出确认对话框")
                    self.show_exit_confirmation()
                    return True
        return super(RoundButton, self).on_touch_up(touch)

    def on_press(self):
        self.opacity = 0.7

    def on_release(self):
        self.opacity = 1.0
        if self.icon_type == 'scissor':
            print("触发：截屏编辑功能")
        elif self.icon_type == 'whiteboard':
            print("触发：白板绘图功能")
        elif self.icon_type == 'album':
            print("触发：相册管理功能")

class MainMenu(FloatLayout):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        
        # 创建三个按钮并垂直排列在左侧
        # 调整位置：按钮间隔缩小为现在的 2/3 (约 93dp)
        self.btn_scissor = RoundButton(icon_type='scissor', pos=(dp(5), dp(226)), base_color=[1, 0.4, 0.4, 0.7])
        self.btn_whiteboard = RoundButton(icon_type='whiteboard', pos=(dp(5), dp(133)), base_color=[0.4, 0.9, 0.4, 0.7])
        self.btn_album = RoundButton(icon_type='album', pos=(dp(5), dp(40)), base_color=[0.4, 0.4, 1, 0.7])
        
        self.add_widget(self.btn_scissor)
        self.add_widget(self.btn_whiteboard)
        self.add_widget(self.btn_album)

class SideMenuApp(App):
    def build(self):
        # 设置窗口背景为近乎黑色，用于 Win32 透明键
        # 颜色设置为 (0, 0, 1/255, 1) 即 RGB(0,0,1)
        Window.clearcolor = (0, 0, 1/255, 1)
        
        # 延时一点时间执行，确保窗口已经创建
        Clock.schedule_once(lambda dt: make_window_transparent(), 0.1)
        
        return MainMenu()

if __name__ == '__main__':
    SideMenuApp().run()
