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


def get_emoji_font():
    """获取系统中的 Emoji 字体"""
    if platform.system() == 'Windows':
        emoji_path = "C:/Windows/Fonts/seguiemj.ttf"
        if os.path.exists(emoji_path):
            return emoji_path
    return None


CHINESE_FONT = get_chinese_font()
EMOJI_FONT = get_emoji_font()

if CHINESE_FONT:
    try:
        LabelBase.register(name='ChineseFont', fn_regular=CHINESE_FONT)
    except:
        pass

if EMOJI_FONT:
    try:
        LabelBase.register(name='EmojiFont', fn_regular=EMOJI_FONT)
    except:
        pass


def get_font():
    return CHINESE_FONT if CHINESE_FONT else 'Roboto'


def get_star_font():
    return EMOJI_FONT if EMOJI_FONT else get_font()


PRESET_COLORS = [
    '#010101', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
    '#FFFF00', '#00FFFF', '#FF00FF', '#FFA500', '#800080',
    '#FFC0CB', '#A52A2A', '#808080', '#FFD700', '#32CD32',
]


class TransparentButton(Button):
    """具有亮丽外观、圆角和悬停效果的按钮"""
    is_hovered = NumericProperty(0)
    
    icon_source = StringProperty('')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = get_font()
        self.font_size = dp(20)  # 默认较大，适合图标
        self.bind(pos=self.update_canvas, size=self.update_canvas, 
                  is_hovered=self.update_canvas, icon_source=self.update_canvas)
        Window.bind(mouse_pos=self.on_mouse_pos)
        
    def on_mouse_pos(self, window, pos):
        if self.get_root_window():
            inside = self.collide_point(*pos)
            if inside and not self.is_hovered:
                self.is_hovered = 1
            elif not inside and self.is_hovered:
                self.is_hovered = 0

    def update_canvas(self, *args):
        self.canvas.before.clear()
        self.canvas.clear()
        with self.canvas.before:
            # 亮丽半透明背景 (玻璃拟态效果)
            # 提高基础透明度以增强对比度，让图标更突出
            alpha = 0.65 + (0.2 * self.is_hovered)
            Color(0.2, 0.2, 0.2, alpha)
            # 使用 Ellipse 绘制圆形背景
            Ellipse(pos=self.pos, size=self.size)
            
            # 高亮边框
            border_alpha = 0.3 + (0.4 * self.is_hovered)
            Color(1, 1, 1, border_alpha)
            # Line(circle=(x, y, radius))
            # 中心点坐标
            cx, cy = self.center_x, self.center_y
            radius = min(self.width, self.height) / 2
            Line(circle=(cx, cy, radius), width=1.1)
            
            # 顶部光泽 (圆形裁剪)
            if self.is_hovered:
                Color(1, 1, 1, 0.1)
                # 绘制一个较小的半椭圆表示光泽
                Ellipse(pos=(self.x + self.width*0.1, self.y + self.height*0.5), 
                        size=(self.width*0.8, self.height*0.4),
                        angle_start=0, angle_end=180)
            
        # 绘制图标 (如果有)
        if self.icon_source:
            # 增加防御性代码，确保 icon_size 为正
            # 减小 padding 以增大图标，使其更清晰 (从 12dp 减为 8dp)
            padding = dp(8)
            icon_size = max(0, min(self.width, self.height) - padding * 2)
            
            if icon_size > 0:
                with self.canvas: # 移出 before 以确保图标在背景和边框之上
                    # 显式设置颜色以确保高亮度，并根据悬停状态调整
                    # 基础亮度 0.85，悬停时 1.0 (全亮度)
                    icon_alpha = 0.85 + (0.15 * self.is_hovered)
                    Color(1, 1, 1, icon_alpha)
                    
                    # 使用 Image 来加载图标，它能更好地处理 SVG (如果安装了依赖)
                    from kivy.core.image import Image as CoreImage
                    try:
                        # 自动探测策略：优先寻找同名 PNG，因为 Kivy 对 PNG 的支持最稳定
                        actual_source = self.icon_source
                        if actual_source.lower().endswith('.svg'):
                            png_source = actual_source.rsplit('.', 1)[0] + '.png'
                            if os.path.exists(png_source):
                                actual_source = png_source
                        
                        # 检查文件是否存在
                        if os.path.exists(actual_source):
                            # 使用 CoreImage 加载并显式启用 mipmap 和平滑过滤
                            image = CoreImage(actual_source, mipmap=True)
                            texture = image.texture
                            if texture:
                                # 设置纹理过滤为线性过滤，提高缩放质量
                                texture.min_filter = 'linear'
                                texture.mag_filter = 'linear'
                                
                                Rectangle(texture=texture,
                                          pos=(self.x + (self.width - icon_size) / 2, 
                                               self.y + (self.height - icon_size) / 2),
                                          size=(icon_size, icon_size))
                                # 成功加载图片后，清除备用文本以防止重叠显示
                                self.text = ''
                            else:
                                raise Exception(f"Empty texture for {actual_source}")
                        else:
                            raise Exception(f"File not found: {actual_source}")
                    except Exception as e:
                        # 如果加载失败，且没有文本，则尝试显示备用文本
                        if not self.text:
                            # 预定义的简单映射（根据文件名猜测图标含义）
                            fallback_map = {
                                'brush': '✏️', 'palette': '🎨', 'shapes': '📐', 
                                'line': '➖', 'undo': '↩️', 'redo': '↪️', 
                                'trash': '🗑️', 'settings': '⚙️', 'x': '❌'
                            }
                            # 绘制备用文本时也显式设置颜色
                            Color(1, 1, 1, icon_alpha)
                            name = os.path.basename(self.icon_source).split('.')[0]
                            self.text = fallback_map.get(name, '❓')
                            self.font_name = get_font()
                            self.font_size = dp(24)


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
        # 隐藏图标，如果是 Emoji
        if value and any(ord(c) > 127 for c in value):
             self.icon_source = ''
             # 如果图标显示在 canvas 中，我们需要强制重绘以清除它
             self.canvas.clear()
             self.update_canvas()
        if self.dropdown:
            self.dropdown.dismiss()
            self.dropdown = None
        for callback in self._callbacks:
            callback(self, value)


class SemiCircleColorButton(Button):
    """半圆形状的颜色选择按钮，带有光影、半透明和悬停效果"""
    color = ListProperty([1, 0, 0, 1])
    is_hovered = NumericProperty(0)
    is_active = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.bind(pos=self.update_canvas, size=self.update_canvas, 
                  color=self.update_canvas, is_hovered=self.update_canvas,
                  is_active=self.update_canvas)
        Window.bind(mouse_pos=self.on_mouse_pos)
        
    def on_mouse_pos(self, window, pos):
        if self.get_root_window():
            local_pos = self.to_widget(*pos)
            # 简化碰撞检测：判断是否在矩形范围内，且在半圆内（大致）
            inside = self.collide_point(*pos)
            if inside and not self.is_hovered:
                self.is_hovered = 1
            elif not inside and self.is_hovered:
                self.is_hovered = 0

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # 基础透明度
            alpha = 0.8 + (0.15 * self.is_hovered)
            
            # 圆心和尺寸 (向下偏移一个半径，使顶部边缘贴合 self.y + self.height)
            # 圆心应该是 (self.center_x, self.y)
            # 绘图位置应为 (self.x, self.y - self.height)
            draw_pos = (self.x, self.y - self.height)
            draw_size = (self.width, self.height * 2)
            
            # 1. 绘制底层阴影
            Color(0, 0, 0, 0.4)
            Ellipse(
                pos=(draw_pos[0] - 2, draw_pos[1] - 2),
                size=(draw_size[0] + 4, draw_size[1] + 4),
                angle_start=-90, angle_end=90,
                segments=60
            )
            
            # 2. 绘制边框
            border_color = [max(0, c - 0.3) for c in self.color[:3]] + [alpha]
            Color(*border_color)
            Ellipse(
                pos=(draw_pos[0] - 1, draw_pos[1] - 1),
                size=(draw_size[0] + 2, draw_size[1] + 2),
                angle_start=-90, angle_end=90,
                segments=60
            )
            
            # 3. 绘制主体半圆
            main_color = list(self.color[:3]) + [alpha]
            Color(*main_color)
            Ellipse(
                pos=draw_pos,
                size=draw_size,
                angle_start=-90, angle_end=90,
                segments=60
            )
            
            # 4. 绘制高亮/光泽
            Color(1, 1, 1, 0.3 * alpha)
            Ellipse(
                pos=(draw_pos[0] + self.width * 0.15, draw_pos[1] + self.height * 0.1),
                size=(self.width * 0.7, self.height * 0.7),
                angle_start=-90, angle_end=90,
                segments=60
            )
            
            # 底部直径边缘高亮
            Color(1, 1, 1, 0.2 * alpha)
            Line(points=[self.x + 2, self.y, self.right - 2, self.y], width=1.1)

            # 5. 如果是当前选中颜色，绘制星星
            if self.is_active:
                # 计算反转颜色以确保在色盘上清晰可见
                r, g, b = self.color[:3]
                # 计算亮度 (YIQ 转换公式的简化版)
                brightness = (r * 0.299 + g * 0.587 + b * 0.114)
                star_color = (1, 1, 1, 1) if brightness < 0.5 else (0.1, 0.1, 0.1, 1)
                
                Color(*star_color)
                # 绘制一个简单的几何五角星，避免字体渲染问题
                # 星星中心点
                star_cx, star_cy = self.center_x, self.y + self.height * 0.45
                # 星星外径和内径
                outer_r = self.height * 0.25
                inner_r = outer_r * 0.4
                
                # 计算五角星的 10 个顶点坐标
                points = []
                for i in range(10):
                    angle_deg = i * 36 - 90 # 从正上方开始，每 36 度一个点
                    angle_rad = math.radians(angle_deg)
                    dist = outer_r if i % 2 == 0 else inner_r
                    px = star_cx + dist * math.cos(angle_rad)
                    py = star_cy + dist * math.sin(angle_rad)
                    points.extend([px, py])
                
                # 使用 Line 闭合路径绘制星星轮廓并填充 (Kivy 没有直接填充多边形指令，
                # 但 Line 结合宽度或 Triangle 组可以，这里先用 Line 配合 segments 闭合)
                # 为简单起见且效果稳定，这里用 Triangle 扇形绘制 5 个部分
                for i in range(0, 10, 2):
                    # 第 i 个外点，第 i+1 个内点，第 i+2 个外点 (mod 10)
                    p1 = [star_cx, star_cy]
                    p2 = [points[i*2], points[i*2+1]]
                    p3 = [points[((i+1)%10)*2], points[((i+1)%10)*2+1]]
                    Triangle(points=[p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]])
                    
                    p1 = [star_cx, star_cy]
                    p2 = [points[((i+1)%10)*2], points[((i+1)%10)*2+1]]
                    p3 = [points[((i+2)%10)*2], points[((i+2)%10)*2+1]]
                    Triangle(points=[p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]])

    def collide_point(self, x, y):
        # 圆心在按钮底边的中点
        cx, cy = self.center_x, self.y
        # 半径是按钮的高度
        radius = self.height
        # 计算点到圆心的距离
        distance = math.sqrt((x - cx)**2 + (y - cy)**2)
        # 点必须在半径内，且在圆心上方（y >= cy）
        return distance <= radius and y >= cy

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # 视觉反馈
            self.is_hovered = 0.5
            return super().on_touch_down(touch)
        return False

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
        self.color_buttons = []
        
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
        
        # 初始更新颜色指示器
        self.bind(current_color=self.update_active_color_indicator)
        self.update_active_color_indicator()
    
    def setup_top_menu(self):
        # 菜单栏背景美化
        self.top_menu = BoxLayout(
            size_hint=(None, None),
            size=(dp(750), dp(60)),
            pos=(dp(20), Window.height - dp(80)),
            spacing=dp(10),
            padding=[dp(10), dp(5)]
        )
        
        # 1. 工具切换按钮 (图标模式)
        self.tool_btn = TransparentButton(text='', icon_source='assets/brush.png', width=dp(50), height=dp(50), size_hint=(None, None))
        self.tool_btn.bind(on_press=self.toggle_tool)
        self.top_menu.add_widget(self.tool_btn)
        
        # 2. 颜色选择 (增加图标按钮)
        self.color_btn = TransparentButton(text='', icon_source='assets/palette.png', width=dp(50), height=dp(50), size_hint=(None, None))
        self.color_btn.bind(on_press=self.show_color_picker)
        self.top_menu.add_widget(self.color_btn)
        
        # 3. 形状选择 (Spinner 美化)
        self.shape_spinner = CustomSpinner(
            text='',
            icon_source='assets/shapes.png',
            values=['📐', '⬜', '⭕', '➡️', '📏', '🔺'],
            width=dp(50), height=dp(50), size_hint=(None, None)
        )
        self.shape_spinner.bind(on_select=self.on_shape_select)
        self.top_menu.add_widget(self.shape_spinner)
        
        # 3. 线条样式
        self.line_style_btn = TransparentButton(text='', icon_source='assets/line.png', width=dp(50), height=dp(50), size_hint=(None, None))
        self.line_style_btn.bind(on_press=self.toggle_line_style)
        self.top_menu.add_widget(self.line_style_btn)
        
        # 4. 宽度调节 (紧凑型)
        width_layout = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(120), padding=[0, dp(5)])
        self.width_label = Label(text='宽度: 2', font_name=get_font(), color=(1, 1, 1, 1), size_hint_y=0.4, font_size=dp(11))
        self.width_slider = Slider(min=1, max=20, value=2, size_hint_y=0.6)
        self.width_slider.bind(value=self.on_width_change)
        width_layout.add_widget(self.width_label)
        width_layout.add_widget(self.width_slider)
        self.top_menu.add_widget(width_layout)
        
        # 5. 操作按钮组
        undo_btn = TransparentButton(text='', icon_source='assets/undo.png', width=dp(50), height=dp(50), size_hint=(None, None))
        undo_btn.bind(on_press=self.undo)
        self.top_menu.add_widget(undo_btn)
        
        redo_btn = TransparentButton(text='', icon_source='assets/redo.png', width=dp(50), height=dp(50), size_hint=(None, None))
        redo_btn.bind(on_press=self.redo)
        self.top_menu.add_widget(redo_btn)
        
        clear_btn = TransparentButton(text='', icon_source='assets/trash.png', width=dp(50), height=dp(50), size_hint=(None, None))
        clear_btn.bind(on_press=self.clear_canvas)
        self.top_menu.add_widget(clear_btn)
        
        # 6. 更多/保存
        more_spinner = CustomSpinner(
            text='',
            icon_source='assets/settings.png',
            values=['💾 保存截图', 'ℹ️ 关于', '❓ 帮助'],
            width=dp(50), height=dp(50), size_hint=(None, None)
        )
        more_spinner.bind(on_select=self.on_more_select)
        self.top_menu.add_widget(more_spinner)
        
        # 7. 时间显示
        self.time_label = Label(
            text='00:00:00', font_name=get_font(), 
            color=(1, 1, 1, 0.9), size_hint_x=None, width=dp(80)
        )
        self.top_menu.add_widget(self.time_label)
        
        # 8. 退出
        exit_btn = TransparentButton(text='', icon_source='assets/x.png', width=dp(50), height=dp(50), size_hint=(None, None))
        exit_btn.bind(on_press=self.close_editor)
        self.top_menu.add_widget(exit_btn)
        
        # 强制所有按钮更新一次以触发 fallback 逻辑
        for widget in self.top_menu.walk():
            if isinstance(widget, TransparentButton):
                widget.update_canvas()
        
        self.add_widget(self.top_menu)
        
        Clock.schedule_interval(self.update_time, 1)
        self.update_time()
        Window.bind(on_resize=self.on_window_resize)
    
    def setup_color_palette(self):
        # 调色板宽度：15个颜色 * 40dp (50dp按钮+5dp间距)
        # 调整按钮尺寸为 2:1，例如 50x25，使其看起来像正半圆
        btn_w = dp(50)
        btn_h = dp(25)
        spacing = dp(8)
        palette_width = (btn_w + spacing) * len(PRESET_COLORS) - spacing
        
        self.color_palette = BoxLayout(
            size_hint=(None, None),
            size=(palette_width, btn_h),
            pos=(Window.width / 2 - palette_width / 2, -dp(5)), # 微调，确保边缘整齐，或者设为0
            spacing=spacing
        )
        
        self.color_buttons = []
        for color_hex in PRESET_COLORS:
            btn = SemiCircleColorButton(
                color=get_color_from_hex(color_hex),
                size_hint=(None, None),
                size=(btn_w, btn_h)
            )
            btn.bind(on_press=lambda b, c=color_hex: self.set_color(c))
            self.color_palette.add_widget(btn)
            self.color_buttons.append(btn)
        
        self.add_widget(self.color_palette)
    
    def update_active_color_indicator(self, *args):
        """更新色盘中的当前颜色指示器（星星）"""
        for btn in self.color_buttons:
            # 比较颜色（通常是 4 个分量的列表，我们可以比较前 3 个或者全部）
            # 由于 current_color 和 btn.color 都是 [r, g, b, a]，直接比较
            is_match = True
            for i in range(3): # 主要比较 RGB
                if abs(self.current_color[i] - btn.color[i]) > 0.01:
                    is_match = False
                    break
            btn.is_active = 1 if is_match else 0
    
    def on_window_resize(self, instance, w, h):
        self.top_menu.pos = (dp(20), h - dp(80))
        # 更新调色板位置，保持水平居中在最底部
        if hasattr(self, 'color_palette'):
            self.color_palette.pos = (w / 2 - self.color_palette.width / 2, 0)
    
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
        modes = [('brush', 'assets/brush.svg', 'crosshair'), 
                ('eraser', 'assets/eraser.svg', 'no'),
                ('select', 'assets/select.svg', 'size_all')]
        current = self.tool_mode
        idx = [m[0] for m in modes].index(current)
        next_idx = (idx + 1) % len(modes)
        self.tool_mode, icon, cursor = modes[next_idx]
        self.tool_btn.icon_source = icon
        Window.set_system_cursor(cursor)
        if self.tool_mode != 'select':
            self.drawing_canvas.deselect()
    
    def toggle_line_style(self, instance):
        self.line_style = 'dashed' if self.line_style == 'solid' else 'solid'
        self.line_style_btn.icon_source = 'assets/line-dashed.svg' if self.line_style == 'dashed' else 'assets/line.svg'
    
    def on_shape_select(self, instance, value):
        mapping = {'📐': 'free', '⬜': 'rect', '⭕': 'circle', 
                  '➡️': 'arrow', '📏': 'line', '🔺': 'triangle'}
        icon_mapping = {
            'free': 'assets/shapes.svg',
            'rect': 'assets/square.svg',
            'circle': 'assets/circle.svg',
            'arrow': 'assets/arrow-right.svg',
            'line': 'assets/line.svg',
            'triangle': 'assets/triangle.svg'
        }
        self.shape_mode = mapping.get(value, 'free')
        self.shape_spinner.icon_source = icon_mapping.get(self.shape_mode, 'assets/shapes.svg')
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
