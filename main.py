import os
import sys
import platform

# SDL2 设置 - 启用透明窗口支持
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_WINDOW_HIDE'] = '0'

from kivy.config import Config
Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '50')
Config.set('graphics', 'width', '70')
Config.set('graphics', 'height', '230')
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

# 定义自定义着色器
ROUND_BUTTON_FRAG = """
#ifdef GL_ES
    precision highp float;
#endif

varying vec4 frag_color;
varying vec2 tex_coord0;

uniform vec4 base_color;
uniform float hover_factor;
uniform sampler2D texture0;
uniform float has_texture;

void main() {
    vec2 uv = (tex_coord0 - 0.5) * 2.0;
    float dist = length(uv);
    
    // 使用fwidth进行更好的抗锯齿
    float fw = fwidth(dist);
    float alpha = 1.0 - smoothstep(1.0 - fw * 2.0, 1.0 + fw * 0.5, dist);
    
    if (alpha <= 0.001) {
        gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
        return;
    }

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
    
    vec3 color_rgb = base_color.rgb;
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
    
    gl_FragColor = vec4(final_color, alpha * base_color.a);
}
"""

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

GLOBAL_HWND = None

def make_window_transparent():
    """使用 Windows API 强制窗口透明"""
    import threading
    import time
    global GLOBAL_HWND
    if platform.system() != 'Windows':
        return

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32

    def find_hwnd(title_substr="SideMenu"):
        # 尝试多种方式查找窗口
        hwnd_local = user32.FindWindowW(None, "SideMenu")
        if hwnd_local:
            return hwnd_local
        
        # 尝试通过SDL2窗口类名查找
        hwnd_local = user32.FindWindowW("SDL_app", None)
        if hwnd_local:
            return hwnd_local
            
        hwnd_local = user32.FindWindowW("SDL_app", "SideMenu")
        if hwnd_local:
            return hwnd_local
        
        # 枚举所有窗口
        def enum_windows_proc(h, lParam):
            if user32.IsWindowVisible(h):
                length = user32.GetWindowTextLengthW(h)
                if length:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buff, length + 1)
                    title = buff.value
                    if "SideMenu" in title or "sidemenu" in title.lower():
                        print(f"找到窗口: {title}, HWND={h}")
                        arr = ctypes.cast(lParam, ctypes.POINTER(wintypes.HWND))
                        arr[0] = h
                        return False
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        out = (wintypes.HWND * 1)()
        user32.EnumWindows(EnumWindowsProc(enum_windows_proc), ctypes.cast(out, wintypes.LPARAM))
        return out[0]

    def worker():
        # 等待窗口创建完成
        time.sleep(0.5)
        
        hwnd = 0
        for i in range(500):
            hwnd = find_hwnd()
            if hwnd:
                break
            time.sleep(0.01)
        
        if not hwnd:
            print("找不到窗口句柄 SideMenu")
            return

        try:
            globals()['GLOBAL_HWND'] = hwnd
        except:
            pass

        print(f"找到窗口句柄: {hwnd}")
        
        # 获取当前线程ID和进程ID
        pid = kernel32.GetCurrentProcessId()
        tid = kernel32.GetCurrentThreadId()
        print(f"当前进程ID: {pid}, 线程ID: {tid}")

        # Windows API 常量
        GWL_EXSTYLE = -20
        GWL_STYLE = -16
        WS_EX_LAYERED = 0x00080000
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_TOPMOST = 0x00000008
        WS_EX_TRANSPARENT = 0x00000020
        WS_POPUP = 0x80000000
        WS_VISIBLE = 0x10000000
        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        LWA_COLORKEY = 0x00000001
        LWA_ALPHA = 0x00000002
        
        # 获取当前样式
        current_exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        current_style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        print(f"当前扩展样式: 0x{current_exstyle:08X}")
        print(f"当前窗口样式: 0x{current_style:08X}")
        
        # 设置Layered Window属性
        # 注意：不要覆盖现有的样式，而是添加新的属性
        new_exstyle = (current_exstyle | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST) & ~WS_EX_TRANSPARENT
        result = user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_exstyle)
        print(f"SetWindowLongW(GWL_EXSTYLE) 结果: {result}")
        
        # 设置窗口样式为无边框弹出窗口，但保留可见性
        new_style = (current_style & ~(WS_CAPTION | WS_THICKFRAME)) | WS_POPUP | WS_VISIBLE
        result = user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
        print(f"SetWindowLongW(GWL_STYLE) 结果: {result}")
        
        # 关键：设置黑色为透明色键
        # 使用 COLORREF 格式: 0x00BBGGRR
        cr_key = 0x00000000  # 纯黑 RGB(0,0,0)
        result = user32.SetLayeredWindowAttributes(hwnd, cr_key, 255, LWA_COLORKEY)
        print(f"SetLayeredWindowAttributes 结果: {result}, GetLastError={kernel32.GetLastError()}")
        
        # 刷新窗口 - 使用更完整的刷新标志
        SWP_FRAMECHANGED = 0x0020
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        SWP_NOACTIVATE = 0x0010
        SWP_NOZORDER = 0x0004
        SWP_ASYNCWINDOWPOS = 0x4000
        SWP_STATECHANGED = 0x8000
        
        result = user32.SetWindowPos(
            hwnd, 
            -1,  # HWND_TOPMOST
            0, 0, 0, 0, 
            SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE | SWP_NOZORDER
        )
        print(f"SetWindowPos 结果: {result}")
        
        # 强制重绘
        user32.InvalidateRect(hwnd, None, True)
        user32.UpdateWindow(hwnd)
        # RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN = 0x0085
        RDW_INVALIDATE = 0x0001
        RDW_ERASE = 0x0004
        RDW_FRAME = 0x0080
        RDW_ALLCHILDREN = 0x0080
        rdw_flags = RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN
        # Note: RedrawWindow may not be available in some Windows versions, use InvalidateRect instead
        
        # 再次确认样式
        final_exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        print(f"最终扩展样式: 0x{final_exstyle:08X}, WS_EX_LAYERED={(final_exstyle & WS_EX_LAYERED) != 0}")
        
        # 尝试DWM模糊效果
        try:
            class DWM_BLURBEHIND(ctypes.Structure):
                _fields_ = [
                    ("dwFlags", ctypes.c_uint),
                    ("fEnable", ctypes.c_bool),
                    ("hRgnBlur", ctypes.c_void_p),
                    ("fTransitionOnMaximized", ctypes.c_bool)
                ]
            
            DWM_BB_ENABLE = 0x00000001
            bb = DWM_BLURBEHIND()
            bb.dwFlags = DWM_BB_ENABLE
            bb.fEnable = False  # 禁用模糊效果，因为我们想要完全透明
            bb.hRgnBlur = None
            bb.fTransitionOnMaximized = False
            
            dwmapi.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(bb))
        except Exception as e:
            print(f"DWM 效果设置失败: {e}")
        
        print("窗口透明设置完成")

    threading.Thread(target=worker, daemon=True).start()


class RoundButton(ButtonBehavior, FloatLayout):
    icon_type = StringProperty('scissor')
    base_color = ListProperty([0.2, 0.6, 1, 0.95])
    hovered = BooleanProperty(False)
    scale = NumericProperty(1.0)
    hover_factor = NumericProperty(0.0)

    def __init__(self, **kwargs):
        self.canvas = RenderContext(use_parent_modelview=True, use_parent_projection=True)
        self.canvas.shader.fs = ROUND_BUTTON_FRAG

        super(RoundButton, self).__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(60), dp(60))

        # 加载贴图
        icon_path = resource_path(os.path.join('assets', f'{self.icon_type}.png'))
        from kivy.core.image import Image as CoreImage
        self._texture = CoreImage(icon_path).texture

        Window.bind(mouse_pos=self.on_mouse_pos)
        self.update_canvas()

        self.bind(
            pos=self.update_canvas,
            size=self.update_canvas,
            base_color=self.update_canvas,
            hover_factor=self.update_canvas,
            scale=self.update_canvas
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
        self.canvas['base_color'] = [float(c) for c in self.base_color]
        self.canvas['hover_factor'] = float(self.hover_factor)
        self.canvas['has_texture'] = 1.0 if self._texture else 0.0

        self.canvas.clear()
        with self.canvas:
            w, h = self.size[0] * self.scale, self.size[1] * self.scale
            cx, cy = self.center
            new_pos = (cx - w / 2, cy - h / 2)
            new_size = (w, h)

            Color(1, 1, 1, 1)
            Rectangle(pos=new_pos, size=new_size, texture=self._texture)

    def show_exit_confirmation(self):
        if platform.system() == "Windows":
            import ctypes
            result = ctypes.windll.user32.MessageBoxW(
                GLOBAL_HWND,
                "确定要退出应用吗？",
                "退出确认",
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
        dist = ((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2) ** 0.5
        return dist <= radius

    def on_touch_down(self, touch):
        if self.is_inside_circle(touch.pos):
            touch.ud['start_time'] = Clock.get_time()
            if touch.button == 'right':
                if self.icon_type == 'album':
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
        elif self.icon_type == 'whiteboard':
            print("触发：白板绘图功能")
        elif self.icon_type == 'album':
            print("触发：相册管理功能")


class MainMenu(FloatLayout):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        
        # 关键：确保背景是纯黑色（将被Windows扣除为透明）
        # 使用 Kivy 的 canvas.before 设置背景
        with self.canvas.before:
            # 纯黑色背景 - 这个会被Windows色键扣除变成透明
            Color(0, 0, 0, 1)
            # 使用Window大小确保背景覆盖整个窗口
            self.bg_rect = Rectangle(pos=(0, 0), size=Window.size)
        
        self.bind(pos=self._update_bg, size=self._update_bg)
        # 窗口大小改变时更新背景
        Window.bind(size=self._on_window_size)

        btn_size = dp(60)
        padding = dp(5)
        spacing = dp(15)

        self.btn_scissor = RoundButton(
            icon_type='scissor',
            pos=(padding, spacing * 2 + btn_size * 2),
            base_color=[1, 0.4, 0.4, 0.98]
        )
        self.btn_whiteboard = RoundButton(
            icon_type='whiteboard',
            pos=(padding, spacing + btn_size),
            base_color=[0.4, 0.9, 0.4, 0.98]
        )
        self.btn_album = RoundButton(
            icon_type='album',
            pos=(padding, padding),
            base_color=[0.4, 0.4, 1, 0.98]
        )
        self.add_widget(self.btn_scissor)
        self.add_widget(self.btn_whiteboard)
        self.add_widget(self.btn_album)
    
    def _update_bg(self, *args):
        self.bg_rect.pos = (0, 0)
        self.bg_rect.size = Window.size
    
    def _on_window_size(self, instance, value):
        # 窗口大小改变时更新背景
        self.bg_rect.size = value


class SideMenuApp(App):
    def build(self):
        # 关键：设置背景为纯黑色（RGB 0,0,0）
        # Windows将把这个颜色作为透明色键扣除
        Window.clearcolor = (0, 0, 0, 1)
        
        make_window_transparent()
        return MainMenu()


if __name__ == '__main__':
    SideMenuApp().run()
