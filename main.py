import os
import sys
import platform
import threading

# SDL2 设置
os.environ['KIVY_WINDOW'] = 'sdl2'

from kivy.config import Config
Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'dpi', '96')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'position', 'custom')
# 初始窗口设为1x1像素，几乎不可见
# 初始窗口在屏幕外且极小，避免用户看到黑色背景
Config.set('graphics', 'left', '-10000')
Config.set('graphics', 'top', '-10000')
Config.set('graphics', 'width', '10')
Config.set('graphics', 'height', '10')
Config.set('graphics', 'always_on_top', '1')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RenderContext
from kivy.core.window import Window
from kivy.properties import StringProperty, ListProperty, BooleanProperty, NumericProperty
from kivy.metrics import dp
from kivy.clock import Clock

# 导入截图编辑模块
import scissor

# 目标窗口大小和位置
TARGET_WIDTH = 68   # 窗口宽度：按钮48 + 左右padding各10
TARGET_HEIGHT = 244 # 窗口高度：3按钮(144) + 2间距(80) + 上下padding(20)
TARGET_LEFT = 0
TARGET_TOP = 100  # 向下移动50像素

# 定义自定义着色器 - 支持边框
ROUND_BUTTON_FRAG = """
#ifdef GL_ES
    precision highp float;
#endif

varying vec4 frag_color;
varying vec2 tex_coord0;

uniform vec4 base_color;
uniform vec4 border_color;
uniform float border_width;
uniform float hover_factor;
uniform sampler2D texture0;
uniform float has_texture;

void main() {
    vec2 uv = (tex_coord0 - 0.5) * 2.0;
    float dist = length(uv);
    
    float fw = fwidth(dist);
    // 极锐利的边缘过渡，最小化过渡区域
    float alpha = 1.0 - smoothstep(1.0 - fw * 0.05, 1.0 + fw * 0.02, dist);
    
    if (alpha <= 0.001) {
        gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
        return;
    }
    
    // 边框逻辑：根据距离判断是否在边框区域
    float inner_radius = 1.0 - border_width;
    float in_border = 1.0 - smoothstep(inner_radius - fw, inner_radius + fw, dist);
    
    // 混合边框颜色和主体颜色
    vec3 color_rgb = mix(border_color.rgb, base_color.rgb, in_border);
    float final_alpha = base_color.a;

    // 光照模型
    vec3 light_pos = vec3(-0.4, 0.4, 1.0);
    float z = sqrt(max(0.0, 1.0 - dot(uv, uv)));
    vec3 normal = normalize(vec3(uv, z));
    
    float diff = max(dot(normal, normalize(light_pos)), 0.0);
    vec3 view_dir = vec3(0.0, 0.0, 1.0);
    vec3 reflect_dir = reflect(-normalize(light_pos), normal);
    float spec = pow(max(dot(view_dir, reflect_dir), 0.0), 16.0);
    float ambient = 0.35;
    float rim = pow(1.0 - max(dot(normal, view_dir), 0.0), 3.0) * 0.4;
    
    vec3 final_color = color_rgb * (diff + ambient) + vec3(spec * 0.5) + vec3(rim);
    final_color += hover_factor * 0.12;

    if (has_texture > 0.5) {
        vec2 icon_uv = (tex_coord0 - 0.5) / 0.6 + 0.5;
        if (icon_uv.x >= 0.0 && icon_uv.x <= 1.0 && icon_uv.y >= 0.0 && icon_uv.y <= 1.0) {
            vec4 tex_color = texture2D(texture0, icon_uv);
            float icon_lighting = diff * 0.7 + ambient;
            final_color = mix(final_color, tex_color.rgb * icon_lighting + vec3(spec * 0.2), tex_color.a);
        }
    }
    
    gl_FragColor = vec4(final_color, alpha * final_alpha);
}
"""

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

GLOBAL_HWND = None

def setup_transparent_window():
    """设置窗口透明并调整到目标大小和位置"""
    import threading
    import time
    global GLOBAL_HWND
    if platform.system() != 'Windows':
        return

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    kernel32 = ctypes.windll.kernel32
    
    # 启用DPI感知（Per Monitor V2）
    try:
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
    except:
        try:
            user32.SetProcessDPIAware()
        except:
            pass
    
    # 计算屏幕右侧位置（使用工作区，排除任务栏）
    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG)
        ]
    
    work_area = RECT()
    # SPI_GETWORKAREA = 0x0030
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work_area), 0)
    
    # 计算右侧位置，留出40像素边距确保不超出屏幕
    target_left = work_area.right - TARGET_WIDTH - 40

    def find_hwnd():
        hwnd_local = user32.FindWindowW(None, "SideMenu")
        if hwnd_local:
            return hwnd_local
        hwnd_local = user32.FindWindowW("SDL_app", None)
        if hwnd_local:
            return hwnd_local
        
        def enum_windows_proc(h, lParam):
            if user32.IsWindowVisible(h):
                length = user32.GetWindowTextLengthW(h)
                if length:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buff, length + 1)
                    if "SideMenu" in buff.value:
                        arr = ctypes.cast(lParam, ctypes.POINTER(wintypes.HWND))
                        arr[0] = h
                        return False
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        out = (wintypes.HWND * 1)()
        user32.EnumWindows(EnumWindowsProc(enum_windows_proc), ctypes.cast(out, wintypes.LPARAM))
        return out[0]

    def worker():
        # 立即开始查找窗口
        hwnd = 0
        for i in range(150):
            hwnd = find_hwnd()
            if hwnd:
                break
            time.sleep(0.01)
        
        if not hwnd:
            print("找不到窗口句柄")
            return

        globals()['GLOBAL_HWND'] = hwnd
        print(f"找到窗口: {hwnd}")

        # Windows API 常量
        GWL_EXSTYLE = -20
        GWL_STYLE = -16
        WS_EX_LAYERED = 0x00080000
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_TOPMOST = 0x00000008
        WS_POPUP = 0x80000000
        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        LWA_COLORKEY = 0x00000001
        
        # 获取当前样式
        current_exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        current_style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        
        # 设置Layered Window
        new_exstyle = (current_exstyle | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_exstyle)
        
        # 移除边框
        new_style = (current_style & ~(WS_CAPTION | WS_THICKFRAME)) | WS_POPUP
        user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
        
        # 设置黑色为透明色键，同时设置整体透明度（200/255 = 78%不透明）
        LWA_ALPHA = 0x00000002
        user32.SetLayeredWindowAttributes(hwnd, 0x00000000, 200, LWA_COLORKEY | LWA_ALPHA)
        
        # 先移动到目标位置并设置目标大小（但保持隐藏）
        SWP_FRAMECHANGED = 0x0020
        SWP_HIDEWINDOW = 0x0080
        SWP_NOACTIVATE = 0x0010
        SWP_NOZORDER = 0x0004
        
        # 先隐藏并设置大小位置
        user32.SetWindowPos(
            hwnd, 
            0,  # 不改变Z序
            target_left, TARGET_TOP, 
            TARGET_WIDTH, TARGET_HEIGHT,
            SWP_FRAMECHANGED | SWP_HIDEWINDOW | SWP_NOACTIVATE | SWP_NOZORDER
        )
        
        # 禁用DWM模糊
        try:
            class DWM_BLURBEHIND(ctypes.Structure):
                _fields_ = [
                    ("dwFlags", ctypes.c_uint),
                    ("fEnable", ctypes.c_bool),
                    ("hRgnBlur", ctypes.c_void_p),
                    ("fTransitionOnMaximized", ctypes.c_bool)
                ]
            bb = DWM_BLURBEHIND()
            bb.dwFlags = 0x00000001
            bb.fEnable = False
            bb.hRgnBlur = None
            bb.fTransitionOnMaximized = False
            dwmapi.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(bb))
        except:
            pass
        
        # 强制重绘
        user32.InvalidateRect(hwnd, None, True)
        user32.UpdateWindow(hwnd)
        
        print(f"窗口已设置: 位置({target_left}, {TARGET_TOP}), 大小({TARGET_WIDTH}, {TARGET_HEIGHT})")
        
        # 延迟显示窗口，确保一切准备就绪
        def show_window(dt):
            # 显示窗口
            user32.ShowWindow(hwnd, 1)  # SW_SHOWNORMAL
            # 确保置顶
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 
                               0x0002 | 0x0001 | 0x0010 | 0x0040)
            user32.UpdateWindow(hwnd)
            print("窗口已显示")
            
            # 通知Kivy窗口大小已改变
            Window.size = (TARGET_WIDTH, TARGET_HEIGHT)
        
        Clock.schedule_once(show_window, 0.2)

    threading.Thread(target=worker, daemon=True).start()


class RoundButton(ButtonBehavior, FloatLayout):
    icon_type = StringProperty('scissor')
    base_color = ListProperty([0.2, 0.6, 1, 0.95])
    border_color = ListProperty([0.1, 0.3, 0.6, 1.0])  # 边框颜色，默认深色
    hovered = BooleanProperty(False)
    scale = NumericProperty(1.0)
    hover_factor = NumericProperty(0.0)

    def __init__(self, **kwargs):
        self.canvas = RenderContext(use_parent_modelview=True, use_parent_projection=True)
        self.canvas.shader.fs = ROUND_BUTTON_FRAG

        super(RoundButton, self).__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(48), dp(48))  # 按钮大小48dp

        icon_path = resource_path(os.path.join('assets', f'{self.icon_type}.png'))
        from kivy.core.image import Image as CoreImage
        self._texture = CoreImage(icon_path).texture

        Window.bind(mouse_pos=self.on_mouse_pos)
        self.update_canvas()

        self.bind(
            pos=self.update_canvas, size=self.update_canvas,
            base_color=self.update_canvas, hover_factor=self.update_canvas,
            scale=self.update_canvas, border_color=self.update_canvas
        )

    def on_mouse_pos(self, window, pos):
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
            Animation(scale=1.1, hover_factor=1.0, duration=0.2, t='out_quad').start(self)
        else:
            Animation(scale=1.0, hover_factor=0.0, duration=0.2, t='out_quad').start(self)

    def update_canvas(self, *args):
        # 设置 shader 参数
        self.canvas['base_color'] = [float(c) for c in self.base_color]
        self.canvas['border_color'] = [float(c) for c in self.border_color]
        # 边框宽度：2像素相对于60dp按钮的比率
        self.canvas['border_width'] = float(dp(2) / (self.size[0] * self.scale) * 2.0)
        self.canvas['hover_factor'] = float(self.hover_factor)
        self.canvas['has_texture'] = 1.0 if self._texture else 0.0

        self.canvas.clear()
        with self.canvas:
            w, h = self.size[0] * self.scale, self.size[1] * self.scale
            cx, cy = self.center
            
            # 扩大渲染尺寸，让边缘抗锯齿部分超出可见区域
            overscan = dp(8)  # 每边多渲染8像素
            render_w = w + overscan * 2
            render_h = h + overscan * 2
            new_pos = (cx - render_w / 2, cy - render_h / 2)
            new_size = (render_w, render_h)
            
            # 绘制按钮（shader 会处理边框和主体）
            Color(1, 1, 1, 1)
            Rectangle(pos=new_pos, size=new_size, texture=self._texture)

    def show_exit_confirmation(self):
        if platform.system() == "Windows":
            import ctypes
            result = ctypes.windll.user32.MessageBoxW(
                GLOBAL_HWND, "确定要退出应用吗？", "退出确认",
                0x00000001 | 0x00000020 | 0x00010000
            )
            if result == 1:
                App.get_running_app().stop()
        else:
            from kivy.uix.popup import Popup
            content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
            content.add_widget(Label(text="确定要退出应用吗？", font_size=dp(16)))
            btns = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(20))
            confirm_btn = Button(text="确定", background_color=[1, 0.4, 0.4, 1])
            cancel_btn = Button(text="取消")
            btns.add_widget(confirm_btn)
            btns.add_widget(cancel_btn)
            content.add_widget(btns)
            popup = Popup(title="退出确认", content=content, size_hint=(None, None), size=(dp(280), dp(160)))
            confirm_btn.bind(on_release=lambda x: App.get_running_app().stop())
            cancel_btn.bind(on_release=lambda x: popup.dismiss())
            popup.open()

    def is_inside_circle(self, pos):
        cx, cy = self.center
        radius = (self.width * self.scale) / 2
        return ((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2) ** 0.5 <= radius

    def on_touch_down(self, touch):
        if self.is_inside_circle(touch.pos):
            touch.ud['start_time'] = Clock.get_time()
            if touch.button == 'right' and self.icon_type == 'album':
                self.show_exit_confirmation()
                return True
            return super(RoundButton, self).on_touch_down(touch)
        return False

    def on_touch_up(self, touch):
        if self.is_inside_circle(touch.pos):
            if 'start_time' in touch.ud:
                duration = Clock.get_time() - touch.ud['start_time']
                if duration > 1.0 and touch.button == 'left' and self.icon_type == 'album':
                    self.show_exit_confirmation()
                    return True
        return super(RoundButton, self).on_touch_up(touch)

    def on_press(self):
        self.opacity = 0.7

    def on_release(self):
        self.opacity = 1.0
        if self.icon_type == 'scissor':
            print("触发：截屏编辑功能")
            self.trigger_screenshot()
        elif self.icon_type == 'whiteboard':
            print("触发：白板绘图功能")
        elif self.icon_type == 'album':
            print("触发：相册管理功能")

    def trigger_screenshot(self):
        """触发截图编辑功能"""
        # 获取主应用实例
        app = App.get_running_app()
        # 切换到截图编辑界面
        app.show_screenshot_editor()


class MainMenu(FloatLayout):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        
        with self.canvas.before:
            Color(0, 0, 0, 1)  # 黑色背景，将被Windows色键扣除为透明
            self.bg_rect = Rectangle(pos=(0, 0), size=Window.size)
        
        self.bind(pos=self._update_bg, size=self._update_bg)
        Window.bind(size=self._on_window_size)

        btn_size = dp(48)  # 按钮大小改为48dp
        padding = dp(10)
        spacing = dp(40)   # 间距等于按钮大小

        # 三个按钮颜色：从上到下依次为偏红、偏蓝、偏绿
        # 重新计算位置，确保按钮完整显示
        # 从底部开始：padding + 按钮 + 间距 + 按钮 + 间距 + 按钮
        btn1_y = padding + spacing * 2 + btn_size * 2  # 最上面的按钮
        btn2_y = padding + spacing + btn_size          # 中间的按钮
        btn3_y = padding                               # 最下面的按钮
        
        self.btn_scissor = RoundButton(
            icon_type='scissor',
            pos=(padding, btn1_y),
            base_color=[0.95, 0.35, 0.35, 0.98],  # 偏红色
            border_color=[0.7, 0.2, 0.2, 1.0]     # 深红色边框
        )
        self.btn_whiteboard = RoundButton(
            icon_type='whiteboard',
            pos=(padding, btn2_y),
            base_color=[0.35, 0.55, 0.95, 0.98],  # 偏蓝色
            border_color=[0.2, 0.35, 0.7, 1.0]    # 深蓝色边框
        )
        self.btn_album = RoundButton(
            icon_type='album',
            pos=(padding, btn3_y),
            base_color=[0.35, 0.85, 0.45, 0.98],  # 偏绿色
            border_color=[0.2, 0.6, 0.3, 1.0]     # 深绿色边框
        )
        self.add_widget(self.btn_scissor)
        self.add_widget(self.btn_whiteboard)
        self.add_widget(self.btn_album)
    
    def _update_bg(self, *args):
        self.bg_rect.pos = (0, 0)
        self.bg_rect.size = Window.size
    
    def _on_window_size(self, instance, value):
        self.bg_rect.size = value


class SideMenuApp(App):
    def build(self):
        Window.clearcolor = (0, 0, 0, 1)  # 黑色背景作为透明色键
        # 立即启动透明设置（窗口初始在屏幕外且很小）
        setup_transparent_window()
        
        # 创建根布局，用于切换主菜单和截图编辑器
        self.root_layout = FloatLayout()
        
        # 创建主菜单
        self.main_menu = MainMenu()
        self.root_layout.add_widget(self.main_menu)
        
        # 截图编辑器（初始不存在）
        self.screenshot_editor = None
        
        return self.root_layout
    
    def show_screenshot_editor(self):
        """显示截图编辑界面"""
        # 先隐藏窗口（避免捕捉到主窗口）
        Window.hide()
        
        # 移除主菜单
        self.root_layout.remove_widget(self.main_menu)
        
        # 延迟创建截图编辑器，确保窗口已隐藏
        def create_editor(dt):
            self.screenshot_editor = scissor.create_screenshot_editor(
                on_complete=self.show_main_menu
            )
            self.root_layout.add_widget(self.screenshot_editor)
        
        Clock.schedule_once(create_editor, 0.2)
    
    def show_main_menu(self):
        """显示主菜单界面"""
        # 移除截图编辑器
        if self.screenshot_editor:
            self.root_layout.remove_widget(self.screenshot_editor)
            self.screenshot_editor = None
        
        # 添加主菜单
        self.root_layout.add_widget(self.main_menu)
        
        # 计算屏幕右侧位置（使用工作区，排除任务栏）
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG)
            ]
        
        work_area = RECT()
        user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work_area), 0)
        
        # 计算右侧位置，留出40像素边距确保不超出屏幕
        target_left = work_area.right - TARGET_WIDTH - 40
        
        # 恢复窗口大小和位置
        Window.size = (TARGET_WIDTH, TARGET_HEIGHT)
        Window.left = target_left
        Window.top = TARGET_TOP
        Window.fullscreen = False
        
        # 显示窗口
        Window.show()
        
        # 重新设置置顶
        Clock.schedule_once(self._restore_topmost, 0.2)
    
    def _restore_topmost(self, dt):
        """恢复窗口置顶"""
        if GLOBAL_HWND:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetWindowPos(GLOBAL_HWND, -1, 0, 0, 0, 0, 
                               0x0002 | 0x0001 | 0x0010 | 0x0040)


if __name__ == '__main__':
    SideMenuApp().run()
