"""
截图编辑功能模块 - 完整绘图编辑器
"""

import os
import time
import platform
import math
from datetime import datetime
from PIL import ImageGrab

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.uix.colorpicker import ColorPicker
from kivy.graphics import Color, Rectangle, Line, Ellipse, Triangle
from kivy.graphics import InstructionGroup
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.utils import get_color_from_hex


def get_chinese_font():
    """获取系统中可用的中文字体"""
    if platform.system() == 'Windows':
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
    return None


CHINESE_FONT = get_chinese_font()
if CHINESE_FONT:
    try:
        LabelBase.register(name='ChineseFont', fn_regular=CHINESE_FONT)
    except:
        pass

def get_font():
    return CHINESE_FONT if CHINESE_FONT else 'Roboto'


PRESET_COLORS = [
    '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
    '#FFFF00', '#00FFFF', '#FF00FF', '#FFA500', '#800080',
    '#FFC0CB', '#A52A2A', '#808080', '#FFD700', '#32CD32',
]


class TransparentButton(Button):
    """半透明镂空按钮"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.2, 0.2, 0.2, 0.7)
        self.color = (1, 1, 1, 1)
        self.font_name = get_font()


class DraggableShape:
    """可拖拽的形状对象 - 基于手柄矩形的变换系统"""
    
    def __init__(self, shape_type, start_pos, end_pos, 
                 color=(1, 0, 0, 1), line_width=2, line_style='solid'):
        self.shape_type = shape_type
        # 原始手柄位置（定义控制矩形）
        self.original_start = list(start_pos) if start_pos else [0, 0]
        
        # 当前手柄位置（经过变换后）
        self.current_start = list(self.original_start)
        
        # 自由画笔的点列表（相对于original_start的偏移）
        self.points = []
        
        if shape_type == 'free' and isinstance(end_pos, (list, tuple)) and len(end_pos) > 2:
            # 自由画：end_pos是点列表 [x1,y1,x2,y2,...]
            base_x, base_y = self.original_start
            for i in range(0, len(end_pos), 2):
                px = end_pos[i] - base_x
                py = end_pos[i+1] - base_y
                self.points.append([px, py])
            # original_end设为最后一个点
            self.original_end = [end_pos[-2], end_pos[-1]] if len(end_pos) >= 2 else list(self.original_start)
            self.current_end = list(self.original_end)
        else:
            # 其他形状：end_pos是终点 [x, y]
            self.original_end = list(end_pos) if end_pos else list(self.original_start)
            self.current_end = list(self.original_end)
        
        # 样式属性
        self.color = list(color)
        self.line_width = line_width
        self.line_style = line_style
        self.is_selected = False
        
        # 变换状态
        self.flip_x = 1  # 1 或 -1（镜像）
        self.flip_y = 1  # 1 或 -1（镜像）
        
    def get_handle_positions(self):
        """获取当前手柄位置"""
        if self.shape_type in ['line', 'arrow', 'free']:
            return [('start', self.current_start), ('end', self.current_end)]
        else:
            # 矩形/圆形/三角形 - 四个角
            x1, y1 = self.current_start
            x2, y2 = self.current_end
            return [
                ('tl', [x1, y2]),  # 左上
                ('tr', [x2, y2]),  # 右上
                ('br', [x2, y1]),  # 右下
                ('bl', [x1, y1]),  # 左下
            ]
    
    def move_by(self, dx, dy):
        """整体移动"""
        self.current_start[0] += dx
        self.current_start[1] += dy
        self.current_end[0] += dx
        self.current_end[1] += dy
    
    def resize(self, handle, new_pos):
        """调整大小 - 手柄精确跟随鼠标，对角手柄锁定"""
        nx, ny = new_pos
        
        if self.shape_type in ['line', 'arrow']:
            # 直线：两个端点直接跟随手柄
            if handle == 'start':
                self.current_start = [nx, ny]
            elif handle == 'end':
                self.current_end = [nx, ny]
                
        elif self.shape_type == 'free':
            # 自由画笔：拖动一个手柄，另一个手柄锁定
            if handle == 'start':
                # 锁定终点，移动起点
                self.current_start = [nx, ny]
            elif handle == 'end':
                # 锁定起点，移动终点
                self.current_end = [nx, ny]
                
        else:
            # 矩形/圆形/三角形：四个角，锁定对角
            # 定义：current_start 为左下 (bl), current_end 为右上 (tr)
            # 实际实现中，current_start 为起点，current_end 为终点
            # 按照 get_handle_positions 的定义：
            # tl: (x1, y2), tr: (x2, y2), br: (x2, y1), bl: (x1, y1)
            
            if handle == 'tl':
                # 左上 (x1, y2)：锁定右下 (x2, y1)
                self.current_start[0] = nx
                self.current_end[1] = ny
            elif handle == 'tr':
                # 右上 (x2, y2)：锁定左下 (x1, y1)
                self.current_end[0] = nx
                self.current_end[1] = ny
            elif handle == 'br':
                # 右下 (x2, y1)：锁定左上 (x1, y2)
                self.current_end[0] = nx
                self.current_start[1] = ny
            elif handle == 'bl':
                # 左下 (x1, y1)：锁定右上 (x2, y2)
                self.current_start[0] = nx
                self.current_start[1] = ny
    
    def get_render_points(self):
        """获取渲染用的点（应用所有变换）"""
        if self.shape_type == 'free':
            if not self.points:
                return []
            
            # 计算当前手柄矩形的参数
            curr_w = self.current_end[0] - self.current_start[0]
            curr_h = self.current_end[1] - self.current_start[1]
            orig_w = self.original_end[0] - self.original_start[0]
            orig_h = self.original_end[1] - self.original_start[1]
            
            # 防止除零
            if abs(orig_w) < 0.001:
                orig_w = 1
            if abs(orig_h) < 0.001:
                orig_h = 1
            
            scale_x = curr_w / orig_w
            scale_y = curr_h / orig_h
            
            result = []
            for p in self.points:
                # 应用缩放 - 确保正负缩放都正确工作
                x = self.current_start[0] + p[0] * scale_x
                y = self.current_start[1] + p[1] * scale_y
                result.extend([x, y])
            return result
        
        elif self.shape_type == 'rect':
            x1, y1 = self.current_start
            x2, y2 = self.current_end
            return [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]
        
        elif self.shape_type == 'circle':
            x1, y1 = self.current_start
            x2, y2 = self.current_end
            return [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]
        
        elif self.shape_type in ['line', 'arrow']:
            return self.current_start + self.current_end
        
        elif self.shape_type == 'triangle':
            x1, y1 = self.current_start
            x2, y2 = self.current_end
            # 确保正确的三角形方向
            left = min(x1, x2)
            right = max(x1, x2)
            top = min(y1, y2)  # y轴向下，所以min是顶部
            bottom = max(y1, y2)
            mid_x = (left + right) / 2
            return [mid_x, top, left, bottom, right, bottom]
        
        return []
    
    def get_bounds(self):
        """获取边界框"""
        if self.shape_type == 'free':
            pts = self.get_render_points()
            if pts:
                xs = pts[0::2]
                ys = pts[1::2]
                return [min(xs), min(ys), max(xs), max(ys)]
            return [0, 0, 0, 0]
        
        x1, y1 = self.current_start
        x2, y2 = self.current_end
        return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
    
    def contains_point(self, pos):
        """检查点是否在形状内或附近"""
        x, y = pos
        margin = max(15, self.line_width + 8)
        
        if self.shape_type == 'free':
            pts = self.get_render_points()
            for i in range(0, len(pts) - 2, 2):
                if self._point_to_segment_distance(x, y, pts[i], pts[i+1], pts[i+2], pts[i+3]) < margin:
                    return True
            return False
        
        elif self.shape_type == 'rect':
            bounds = self.get_bounds()
            return (bounds[0] - margin <= x <= bounds[2] + margin and 
                    bounds[1] - margin <= y <= bounds[3] + margin)
        
        elif self.shape_type == 'circle':
            bounds = self.get_bounds()
            cx = (bounds[0] + bounds[2]) / 2
            cy = (bounds[1] + bounds[3]) / 2
            rx = max(1, (bounds[2] - bounds[0]) / 2)
            ry = max(1, (bounds[3] - bounds[1]) / 2)
            dx = x - cx
            dy = y - cy
            return (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 1.3
        
        elif self.shape_type in ['line', 'arrow']:
            pts = self.get_render_points()
            if len(pts) >= 4:
                return self._point_to_segment_distance(x, y, pts[0], pts[1], pts[2], pts[3]) < margin
            return False
        
        elif self.shape_type == 'triangle':
            bounds = self.get_bounds()
            return (bounds[0] - margin <= x <= bounds[2] + margin and 
                   bounds[1] - margin <= y <= bounds[3] + margin)
        
        return False
    
    def _point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)


class SelectionHandle:
    """选择手柄 - 只显示手柄点"""
    HANDLE_SIZE = dp(14)
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.shape = None
        self.instruction_group = None
        
    def attach(self, shape):
        self.detach()
        self.shape = shape
        self.draw()
        
    def detach(self):
        if self.instruction_group:
            self.canvas.remove(self.instruction_group)
            self.instruction_group = None
        self.shape = None
    
    def update(self):
        if self.shape:
            self.draw()
    
    def draw(self):
        """绘制圆点手柄"""
        if self.instruction_group:
            self.canvas.remove(self.instruction_group)
        
        self.instruction_group = InstructionGroup()
        handles = self.shape.get_handle_positions()
        hs = self.HANDLE_SIZE
        
        for name, (hx, hy) in handles:
            # 白色外圈
            self.instruction_group.add(Color(1, 1, 1, 1))
            self.instruction_group.add(Ellipse(pos=(hx - hs/2, hy - hs/2), size=(hs, hs)))
            # 蓝色内圈
            self.instruction_group.add(Color(0.2, 0.6, 1, 1))
            inner_hs = hs * 0.6
            self.instruction_group.add(Ellipse(pos=(hx - inner_hs/2, hy - inner_hs/2), size=(inner_hs, inner_hs)))
        
        self.canvas.add(self.instruction_group)
    
    def get_handle_at(self, pos):
        """获取点击的手柄"""
        if not self.shape:
            return None
        
        handles = self.shape.get_handle_positions()
        hs = self.HANDLE_SIZE * 2  # 增大点击区域
        px, py = pos
        
        for name, (hx, hy) in handles:
            if abs(px - hx) <= hs/2 and abs(py - hy) <= hs/2:
                return name
        return None


class DrawingCanvas(FloatLayout):
    """绘图画布"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shapes = []
        self.shape_canvases = {}
        self.selection_handle = SelectionHandle(self.canvas)
        self.undo_stack = []
        self.redo_stack = []
        
    def add_shape(self, shape):
        self.shapes.append(shape)
        self.undo_stack.append(('add', shape))
        self.redo_stack.clear()
        self.render_shape(shape)
        
    def render_shape(self, shape, is_preview=False):
        if is_preview and hasattr(self, 'preview_instruction') and self.preview_instruction:
            self.canvas.remove(self.preview_instruction)
        
        instr_group = InstructionGroup()
        r, g, b, a = shape.color
        instr_group.add(Color(r, g, b, a))
        
        if shape.shape_type == 'free':
            pts = shape.get_render_points()
            if len(pts) >= 4:
                if shape.line_style == 'dashed':
                    self._draw_dashed_line(instr_group, pts, shape.line_width)
                else:
                    instr_group.add(Line(points=pts, width=shape.line_width, cap='round', joint='round'))
                
        elif shape.shape_type == 'rect':
            x, y, w, h = shape.get_render_points()
            if shape.line_style == 'dashed':
                self._draw_dashed_rect(instr_group, x, y, w, h, shape.line_width)
            else:
                instr_group.add(Line(rectangle=(x, y, w, h), width=shape.line_width))
            
        elif shape.shape_type == 'circle':
            x, y, w, h = shape.get_render_points()
            if shape.line_style == 'dashed':
                self._draw_dashed_ellipse(instr_group, x, y, w, h, shape.line_width)
            else:
                instr_group.add(Line(ellipse=(x, y, w, h), width=shape.line_width))
            
        elif shape.shape_type in ['line', 'arrow']:
            pts = shape.get_render_points()
            if len(pts) >= 4:
                if shape.line_style == 'dashed':
                    self._draw_dashed_line(instr_group, pts, shape.line_width)
                else:
                    instr_group.add(Line(points=pts, width=shape.line_width, cap='round'))
                
                if shape.shape_type == 'arrow':
                    arrow_pts = self._calc_arrow_points(pts[:2], pts[2:], shape.line_width)
                    for ap in arrow_pts:
                        instr_group.add(Line(points=ap, width=shape.line_width, cap='round'))
                
        elif shape.shape_type == 'triangle':
            pts = shape.get_render_points()
            if len(pts) >= 6:
                if shape.line_style == 'dashed':
                    self._draw_dashed_line(instr_group, pts + pts[:2], shape.line_width)
                else:
                    instr_group.add(Line(points=pts, width=shape.line_width, close=True))
        
        self.canvas.add(instr_group)
        
        if is_preview:
            self.preview_instruction = instr_group
        else:
            self.shape_canvases[shape] = instr_group
            
        return instr_group
    
    def _draw_dashed_line(self, instr_group, points, width):
        dash_len = dp(10)
        i = 0
        while i < len(points) - 2:
            x1, y1 = points[i], points[i+1]
            x2, y2 = points[i+2], points[i+3]
            instr_group.add(Line(points=[x1, y1, x2, y2], width=width, 
                               dash_length=dash_len, dash_offset=dp(6)))
            i += 2
    
    def _draw_dashed_rect(self, instr_group, x, y, w, h, width):
        pts = [x, y, x+w, y, x+w, y+h, x, y+h, x, y]
        self._draw_dashed_line(instr_group, pts, width)
    
    def _draw_dashed_ellipse(self, instr_group, x, y, w, h, width):
        cx, cy = x + w/2, y + h/2
        rx, ry = max(1, w/2), max(1, h/2)
        num_segments = max(20, int((rx + ry) / dp(5)))
        pts = []
        for i in range(num_segments + 1):
            angle = 2 * math.pi * i / num_segments
            px = cx + rx * math.cos(angle)
            py = cy + ry * math.sin(angle)
            pts.extend([px, py])
        self._draw_dashed_line(instr_group, pts, width)
    
    def _calc_arrow_points(self, start, end, width):
        x1, y1 = start
        x2, y2 = end
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = max(dp(12), width * dp(4))
        arrow_angle = math.pi / 6
        x3 = x2 - arrow_len * math.cos(angle - arrow_angle)
        y3 = y2 - arrow_len * math.sin(angle - arrow_angle)
        x4 = x2 - arrow_len * math.cos(angle + arrow_angle)
        y4 = y2 - arrow_len * math.sin(angle + arrow_angle)
        return [[x2, y2, x3, y3], [x2, y2, x4, y4]]
    
    def remove_shape_render(self, shape):
        if shape in self.shape_canvases:
            self.canvas.remove(self.shape_canvases[shape])
            del self.shape_canvases[shape]
    
    def select_shape_at(self, pos):
        for shape in reversed(self.shapes):
            if shape.contains_point(pos):
                self.select_shape(shape)
                return shape
        self.deselect()
        return None
    
    def select_shape(self, shape):
        self.deselect()
        shape.is_selected = True
        self.selection_handle.attach(shape)
    
    def deselect(self):
        self.selection_handle.detach()
        for shape in self.shapes:
            shape.is_selected = False
    
    def move_shape(self, shape, dx, dy):
        shape.move_by(dx, dy)
        self.remove_shape_render(shape)
        self.render_shape(shape)
        if shape.is_selected:
            self.selection_handle.update()
    
    def resize_shape(self, shape, handle, new_pos):
        shape.resize(handle, new_pos)
        self.remove_shape_render(shape)
        self.render_shape(shape)
        if shape.is_selected:
            self.selection_handle.update()
    
    def erase_at(self, pos):
        to_remove = []
        for shape in self.shapes:
            if shape.contains_point(pos):
                to_remove.append(shape)
        
        for shape in to_remove:
            self.undo_stack.append(('erase', shape))
            self.remove_shape_render(shape)
            if shape in self.shapes:
                self.shapes.remove(shape)
            if shape.is_selected:
                self.deselect()
    
    def undo(self):
        if not self.undo_stack:
            return False
        action, shape = self.undo_stack.pop()
        
        if action == 'add':
            self.remove_shape_render(shape)
            if shape in self.shapes:
                self.shapes.remove(shape)
            if shape.is_selected:
                self.deselect()
            self.redo_stack.append(('add', shape))
        elif action == 'erase':
            self.shapes.append(shape)
            self.render_shape(shape)
            self.redo_stack.append(('erase', shape))
        return True
    
    def redo(self):
        if not self.redo_stack:
            return False
        action, shape = self.redo_stack.pop()
        
        if action == 'add':
            self.shapes.append(shape)
            self.undo_stack.append(('add', shape))
            self.render_shape(shape)
        elif action == 'erase':
            self.remove_shape_render(shape)
            if shape in self.shapes:
                self.shapes.remove(shape)
            if shape.is_selected:
                self.deselect()
            self.undo_stack.append(('erase', shape))
        return True
    
    def clear_canvas(self):
        for shape in list(self.shapes):
            self.remove_shape_render(shape)
        self.shapes.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.deselect()


class CustomSpinner(TransparentButton):
    """自定义下拉菜单"""
    def __init__(self, text='', values=None, **kwargs):
        self.values = values or []
        self.dropdown = None
        self._callbacks = []
        super().__init__(text=text, **kwargs)
        self.bind(on_press=self.open_dropdown)
        
    def bind(self, **kwargs):
        if 'on_select' in kwargs:
            self._callbacks.append(kwargs.pop('on_select'))
        super().bind(**kwargs)
        
    def open_dropdown(self, *args):
        if self.dropdown:
            self.dropdown.dismiss()
            self.dropdown = None
            return
        
        self.dropdown = DropDown(auto_width=False, width=self.width)
        font_name = get_font()
        
        for val in self.values:
            btn = Button(
                text=val, size_hint_y=None, height=dp(40),
                font_name=font_name, background_color=(0.25, 0.25, 0.25, 0.95)
            )
            btn.bind(on_release=lambda b, v=val: self.select(v))
            self.dropdown.add_widget(btn)
        
        self.dropdown.open(self)
    
    def select(self, value):
        self.text = value
        if self.dropdown:
            self.dropdown.dismiss()
            self.dropdown = None
        for callback in self._callbacks:
            callback(self, value)


class ScreenshotEditor(FloatLayout):
    """截图编辑界面"""
    
    current_color = ListProperty([1, 0, 0, 1])
    line_width = NumericProperty(2)
    tool_mode = StringProperty('brush')
    line_style = StringProperty('solid')
    shape_mode = StringProperty('free')
    
    def __init__(self, on_complete=None, **kwargs):
        super().__init__(**kwargs)
        self.on_complete = on_complete
        self.screenshot_path = None
        self.drawing = False
        self.start_pos = None
        self.temp_points = []
        self.selected_shape = None
        self.moving = False
        self.resizing = False
        self.resize_handle = None
        self.last_touch = None
        
        self.capture_and_show()
    
    def capture_and_show(self):
        self.show_editor_background()
        Clock.schedule_once(self._do_capture, 0.3)
    
    def _do_capture(self, dt):
        try:
            screenshot = ImageGrab.grab()
            self.screenshot_path = os.path.join(os.path.dirname(__file__), 'temp_screenshot.png')
            screenshot.save(self.screenshot_path)
            self.show_editor()
        except Exception as e:
            print(f"截图失败: {e}")
            self.close_editor()
    
    def show_editor_background(self):
        Window.fullscreen = 'auto'
        Window.show()
        Window.canvas.ask_update()
    
    def show_editor(self):
        Window.show()
        Window.fullscreen = 'auto'
        
        self.img = Image(allow_stretch=True, keep_ratio=False,
                        size_hint=(1, 1), pos=(0, 0), nocache=True)
        self.img.source = self.screenshot_path
        self.add_widget(self.img)
        
        self.drawing_canvas = DrawingCanvas(size_hint=(1, 1), pos=(0, 0))
        self.add_widget(self.drawing_canvas)
        
        self.setup_top_menu()
        self.setup_color_palette()
        self.update_cursor()
    
    def setup_top_menu(self):
        self.top_menu = BoxLayout(
            size_hint=(None, None),
            size=(dp(980), dp(50)),
            pos=(dp(20), Window.height - dp(70)),
            spacing=dp(5)
        )
        
        font_name = get_font()
        
        self.tool_btn = TransparentButton(text='✏️ 画笔', size_hint_x=None, width=dp(90))
        self.tool_btn.bind(on_press=self.toggle_tool)
        self.top_menu.add_widget(self.tool_btn)
        
        color_btn = TransparentButton(text='🎨 调色', size_hint_x=None, width=dp(90))
        color_btn.bind(on_press=self.show_color_picker)
        self.top_menu.add_widget(color_btn)
        
        self.line_style_btn = TransparentButton(text='➖ 实线', size_hint_x=None, width=dp(90))
        self.line_style_btn.bind(on_press=self.toggle_line_style)
        self.top_menu.add_widget(self.line_style_btn)
        
        self.shape_spinner = CustomSpinner(
            text='📐 自由画', values=['📐 自由画', '⬜ 矩形', '⭕ 圆形', '➡️ 箭头', '📏 直线', '🔺 三角形'],
            size_hint_x=None, width=dp(110)
        )
        self.shape_spinner.bind(on_select=self.on_shape_select)
        self.top_menu.add_widget(self.shape_spinner)
        
        width_layout = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(100))
        self.width_label = Label(text='宽度: 2', font_name=font_name, color=(1, 1, 1, 1), size_hint_y=0.4, font_size=dp(12))
        self.width_slider = Slider(min=1, max=20, value=2, size_hint_y=0.6)
        self.width_slider.bind(value=self.on_width_change)
        width_layout.add_widget(self.width_label)
        width_layout.add_widget(self.width_slider)
        self.top_menu.add_widget(width_layout)
        
        clear_btn = TransparentButton(text='🗑️ 清空', size_hint_x=None, width=dp(80))
        clear_btn.bind(on_press=self.clear_canvas)
        self.top_menu.add_widget(clear_btn)
        
        undo_redo = BoxLayout(size_hint_x=None, width=dp(100), spacing=dp(2))
        undo_btn = TransparentButton(text='↩️')
        undo_btn.bind(on_press=self.undo)
        redo_btn = TransparentButton(text='↪️')
        redo_btn.bind(on_press=self.redo)
        undo_redo.add_widget(undo_btn)
        undo_redo.add_widget(redo_btn)
        self.top_menu.add_widget(undo_redo)
        
        exit_btn = TransparentButton(text='❌ 退出', size_hint_x=None, width=dp(90))
        exit_btn.bind(on_press=self.close_editor)
        self.top_menu.add_widget(exit_btn)
        
        self.time_label = Label(text='', size_hint_x=None, width=dp(80), 
                               font_name=font_name, color=(1, 1, 1, 1), font_size=dp(14))
        self.top_menu.add_widget(self.time_label)
        
        more_spinner = CustomSpinner(
            text='📋 更多', values=['💾 保存截图', 'ℹ️ 关于', '❓ 帮助'],
            size_hint_x=None, width=dp(100)
        )
        more_spinner.bind(on_select=self.on_more_select)
        self.top_menu.add_widget(more_spinner)
        
        self.add_widget(self.top_menu)
        
        Clock.schedule_interval(self.update_time, 1)
        self.update_time()
        Window.bind(on_resize=self.on_window_resize)
    
    def setup_color_palette(self):
        # 使用 FloatLayout 代替 BoxLayout 以便灵活控制按钮位置和背景
        self.color_palette = FloatLayout(
            size_hint=(None, None),
            size=(dp(400), dp(200)),
            pos=(Window.width / 2 - dp(200), -dp(100))  # 放在底部中间，向下偏离，只露出一半
        )
        
        # 为调色板添加半圆背景
        with self.color_palette.canvas.before:
            Color(0.2, 0.2, 0.2, 0.8)
            self.palette_bg = Ellipse(
                pos=self.color_palette.pos,
                size=self.color_palette.size
            )
        
        # 绑定位置更新以保持居中和圆心一致
        def update_palette_pos(instance, pos):
            self.palette_bg.pos = pos
            self.palette_bg.size = instance.size
        self.color_palette.bind(pos=update_palette_pos, size=update_palette_pos)

        # 扇形分布按钮
        radius = dp(140)
        center_x = dp(200)
        center_y = dp(100)
        
        for i, color_hex in enumerate(PRESET_COLORS):
            # 将 0-180 度分布
            angle = math.radians(180 - (i * (180 / (len(PRESET_COLORS) - 1))))
            bx = center_x + radius * math.cos(angle) - dp(15)
            by = center_y + radius * math.sin(angle) - dp(15)
            
            btn = Button(
                background_normal='',
                background_color=get_color_from_hex(color_hex),
                size_hint=(None, None),
                size=(dp(30), dp(30)),
                pos=(bx, by)
            )
            # 在 Kivy 中，子部件位置是相对于父部件的
            btn.pos = (bx, by)
            btn.bind(on_press=lambda b, c=color_hex: self.set_color(c))
            self.color_palette.add_widget(btn)
        
        self.add_widget(self.color_palette)
    
    def on_window_resize(self, instance, w, h):
        self.top_menu.pos = (dp(20), h - dp(70))
        # 更新调色板位置
        self.color_palette.pos = (w / 2 - dp(200), -dp(100))
    
    def update_time(self, *args):
        self.time_label.text = datetime.now().strftime('%H:%M:%S')
    
    def update_cursor(self):
        if self.tool_mode == 'brush':
            Window.set_system_cursor('crosshair')
        elif self.tool_mode == 'eraser':
            Window.set_system_cursor('no')
        elif self.tool_mode == 'select':
            Window.set_system_cursor('size_all')
    
    def toggle_tool(self, instance):
        modes = [('brush', '✏️ 画笔', 'crosshair'), 
                ('eraser', '🧽 橡皮', 'no'),
                ('select', '👆 选择', 'size_all')]
        current = self.tool_mode
        idx = [m[0] for m in modes].index(current)
        next_idx = (idx + 1) % len(modes)
        self.tool_mode, name, cursor = modes[next_idx]
        self.tool_btn.text = name
        Window.set_system_cursor(cursor)
        if self.tool_mode != 'select':
            self.drawing_canvas.deselect()
    
    def toggle_line_style(self, instance):
        self.line_style = 'dashed' if self.line_style == 'solid' else 'solid'
        self.line_style_btn.text = '- - 虚线' if self.line_style == 'dashed' else '➖ 实线'
    
    def on_shape_select(self, instance, value):
        mapping = {'📐 自由画': 'free', '⬜ 矩形': 'rect', '⭕ 圆形': 'circle', 
                  '➡️ 箭头': 'arrow', '📏 直线': 'line', '🔺 三角形': 'triangle'}
        self.shape_mode = mapping.get(value, 'free')
        self.shape_spinner.text = value
        self.drawing_canvas.deselect()
    
    def on_width_change(self, instance, value):
        self.line_width = int(value)
        self.width_label.text = f'宽度: {self.line_width}'
    
    def set_color(self, color_hex):
        self.current_color = get_color_from_hex(color_hex)
    
    def show_color_picker(self, instance):
        font_name = get_font()
        content = BoxLayout(orientation='vertical', spacing=dp(10))
        picker = ColorPicker(color=self.current_color)
        picker.bind(color=lambda i, v: setattr(self, 'current_color', list(v)))
        close_btn = Button(text='确定', size_hint_y=None, height=dp(50), font_name=font_name)
        popup = Popup(title='选择颜色', content=content, size_hint=(0.8, 0.8), title_font=font_name)
        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(picker)
        content.add_widget(close_btn)
        popup.open()
    
    def clear_canvas(self, instance):
        self.drawing_canvas.clear_canvas()
    
    def undo(self, instance):
        self.drawing_canvas.undo()
    
    def redo(self, instance):
        self.drawing_canvas.redo()
    
    def on_more_select(self, instance, value):
        mapping = {'💾 保存截图': self.save_screenshot, 'ℹ️ 关于': self.show_about, '❓ 帮助': self.show_help}
        func = mapping.get(value)
        if func:
            func()
    
    def on_touch_down(self, touch):
        if self._check_ui_collision(touch.pos):
            return super().on_touch_down(touch)
        
        if self.tool_mode == 'select':
            # 优先检查是否点击了当前选中对象的手柄
            if self.drawing_canvas.selection_handle.shape:
                handle = self.drawing_canvas.selection_handle.get_handle_at(touch.pos)
                if handle:
                    self.selected_shape = self.drawing_canvas.selection_handle.shape
                    self.resize_handle = handle
                    self.resizing = True
                    self.moving = False
                    return True
            
            # 检查是否点击了某个对象
            clicked_shape = None
            for shape in reversed(self.drawing_canvas.shapes):
                if shape.contains_point(touch.pos):
                    clicked_shape = shape
                    break
            
            if clicked_shape:
                if clicked_shape.is_selected:
                    self.selected_shape = clicked_shape
                    self.moving = True
                    self.resizing = False
                    self.last_touch = touch.pos
                else:
                    self.drawing_canvas.select_shape(clicked_shape)
                    self.selected_shape = clicked_shape
                    self.moving = True
                    self.resizing = False
                    self.last_touch = touch.pos
            else:
                self.drawing_canvas.deselect()
                self.selected_shape = None
                self.moving = False
                self.resizing = False
            return True
        
        elif self.tool_mode == 'eraser':
            self.drawing_canvas.erase_at(touch.pos)
            return True
        
        else:
            self.drawing = True
            self.start_pos = list(touch.pos)
            self.temp_points = [touch.x, touch.y]
            return True
    
    def on_touch_move(self, touch):
        if self.tool_mode == 'select' and self.selected_shape:
            if self.resizing and self.resize_handle:
                self.drawing_canvas.resize_shape(self.selected_shape, self.resize_handle, (touch.x, touch.y))
            elif self.moving:
                dx = touch.x - self.last_touch[0]
                dy = touch.y - self.last_touch[1]
                self.drawing_canvas.move_shape(self.selected_shape, dx, dy)
                self.last_touch = touch.pos
            return True
        
        elif self.tool_mode == 'eraser':
            self.drawing_canvas.erase_at(touch.pos)
            return True
        
        elif self.drawing:
            self.temp_points.extend([touch.x, touch.y])
            if self.shape_mode == 'free':
                # 复制列表避免引用问题
                preview_end = list(self.temp_points)
            else:
                preview_end = [touch.x, touch.y]
            preview = DraggableShape(
                self.shape_mode, self.start_pos, preview_end,
                color=list(self.current_color), line_width=self.line_width, line_style=self.line_style
            )
            self.drawing_canvas.render_shape(preview, is_preview=True)
            return True
        
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        if self.tool_mode == 'select':
            self.moving = False
            self.resizing = False
            self.resize_handle = None
            return True
        
        elif self.tool_mode == 'eraser':
            return True
        
        elif self.drawing:
            self.drawing = False
            
            if hasattr(self.drawing_canvas, 'preview_instruction') and self.drawing_canvas.preview_instruction:
                self.drawing_canvas.canvas.remove(self.drawing_canvas.preview_instruction)
                self.drawing_canvas.preview_instruction = None
            
            # 复制列表避免引用问题
            final_points = list(self.temp_points) if self.shape_mode == 'free' else list(touch.pos)
            shape = DraggableShape(
                self.shape_mode, self.start_pos, final_points,
                color=list(self.current_color), line_width=self.line_width, line_style=self.line_style
            )
            self.drawing_canvas.add_shape(shape)
            self.temp_points = []
            return True
        
        return super().on_touch_up(touch)
    
    def _check_ui_collision(self, pos):
        if hasattr(self, 'top_menu') and self.top_menu.collide_point(*pos):
            return True
        if hasattr(self, 'color_palette') and self.color_palette.collide_point(*pos):
            return True
        return False
    
    def save_screenshot(self):
        try:
            self.export_to_png('edited_screenshot.png')
            print("已保存到 edited_screenshot.png")
        except Exception as e:
            print(f"保存失败: {e}")
    
    def show_about(self):
        font_name = get_font()
        popup = Popup(
            title='关于',
            content=Label(text='截图编辑器 v1.0\n一款简单易用的截图编辑工具', font_name=font_name),
            size_hint=(0.6, 0.4),
            title_font=font_name
        )
        popup.open()
    
    def show_help(self):
        font_name = get_font()
        content = Label(
            text='工具说明：\n✏️ 画笔 - 自由绘制\n🧽 橡皮 - 擦除内容\n👆 选择 - 移动/调整大小\n\n调整大小：\n• 拖动手柄精确控制\n• 支持镜像翻转',
            font_name=font_name
        )
        popup = Popup(title='帮助', content=content, size_hint=(0.6, 0.5), title_font=font_name)
        popup.open()
    
    def close_editor(self, instance=None):
        Window.set_system_cursor('arrow')
        Clock.unschedule(self.update_time)
        Window.fullscreen = False
        
        if self.screenshot_path and os.path.exists(self.screenshot_path):
            try:
                os.remove(self.screenshot_path)
            except:
                pass
        
        if self.parent:
            self.parent.remove_widget(self)
        
        if self.on_complete:
            Clock.schedule_once(lambda dt: self.on_complete(), 0.1)


def create_screenshot_editor(on_complete=None):
    return ScreenshotEditor(on_complete=on_complete)
