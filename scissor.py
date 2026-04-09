"""
截图编辑功能模块
点击剪刀按钮后，隐藏主窗口，截取全屏，然后弹出编辑窗口
"""

import os
import sys
import time
from PIL import ImageGrab

# Kivy 导入
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock


class ScreenshotEditor(FloatLayout):
    """截图编辑界面"""
    
    def __init__(self, screenshot_path, on_close_callback=None, **kwargs):
        super(ScreenshotEditor, self).__init__(**kwargs)
        self.screenshot_path = screenshot_path
        self.on_close_callback = on_close_callback
        
        # 设置窗口为全屏
        Window.fullscreen = 'auto'
        
        # 显示截图背景
        self.img = Image(
            source=screenshot_path,
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos=(0, 0)
        )
        self.add_widget(self.img)
        
        # 添加操作按钮栏
        self.setup_toolbar()
        
        # 绑定鼠标事件用于绘制
        self.drawing = False
        self.bind(on_touch_down=self.on_draw_start)
        self.bind(on_touch_move=self.on_draw_move)
        self.bind(on_touch_up=self.on_draw_end)
    
    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = BoxLayout(
            size_hint=(None, None),
            size=(dp(300), dp(50)),
            pos=(dp(20), dp(20)),
            spacing=dp(10)
        )
        
        # 保存按钮
        save_btn = Button(text='保存', size_hint_x=None, width=dp(80))
        save_btn.bind(on_press=self.save_screenshot)
        toolbar.add_widget(save_btn)
        
        # 取消/关闭按钮
        cancel_btn = Button(text='取消', size_hint_x=None, width=dp(80))
        cancel_btn.bind(on_press=self.close_editor)
        toolbar.add_widget(cancel_btn)
        
        self.add_widget(toolbar)
    
    def on_draw_start(self, widget, touch):
        """开始绘制"""
        if touch.y < dp(100):  # 避开工具栏区域
            return
        self.drawing = True
        self.start_pos = touch.pos
        
        # 创建绘制层
        with self.canvas:
            Color(1, 0, 0, 0.5)  # 红色半透明
            self.current_shape = Rectangle(
                pos=touch.pos,
                size=(0, 0)
            )
    
    def on_draw_move(self, widget, touch):
        """绘制中"""
        if not self.drawing:
            return
        
        # 更新矩形大小
        x = min(self.start_pos[0], touch.pos[0])
        y = min(self.start_pos[1], touch.pos[1])
        w = abs(touch.pos[0] - self.start_pos[0])
        h = abs(touch.pos[1] - self.start_pos[1])
        
        self.current_shape.pos = (x, y)
        self.current_shape.size = (w, h)
    
    def on_draw_end(self, widget, touch):
        """结束绘制"""
        self.drawing = False
    
    def save_screenshot(self, instance):
        """保存截图"""
        print("保存截图...")
        # TODO: 实现保存逻辑
        self.close_editor(None)
    
    def close_editor(self, instance):
        """关闭编辑器"""
        Window.fullscreen = False
        if self.on_close_callback:
            self.on_close_callback()
        # 关闭编辑窗口
        App.get_running_app().stop()


class ScissorApp(App):
    """截图编辑应用"""
    
    def __init__(self, screenshot_path, on_close_callback=None, **kwargs):
        super(ScissorApp, self).__init__(**kwargs)
        self.screenshot_path = screenshot_path
        self.on_close_callback = on_close_callback
    
    def build(self):
        return ScreenshotEditor(
            screenshot_path=self.screenshot_path,
            on_close_callback=self.on_close_callback
        )


def start_screenshot_edit(on_close_callback=None):
    """
    启动截图编辑流程
    
    Args:
        on_close_callback: 编辑窗口关闭后的回调函数
    """
    # 等待一小段时间确保主窗口已隐藏
    time.sleep(0.3)
    
    # 截取全屏
    print("正在截取屏幕...")
    screenshot = ImageGrab.grab()
    
    # 保存到临时文件
    temp_path = os.path.join(os.path.dirname(__file__), 'temp_screenshot.png')
    screenshot.save(temp_path)
    print(f"截图已保存到: {temp_path}")
    
    # 启动编辑窗口
    app = ScissorApp(temp_path, on_close_callback)
    app.run()
    
    # 清理临时文件
    if os.path.exists(temp_path):
        os.remove(temp_path)
        print("临时文件已清理")


if __name__ == '__main__':
    # 测试运行
    start_screenshot_edit()
