"""工具层：无业务语义、无状态、可独立单测的纯函数。

- image.py   图像转换（dataURL / base64、格式转换、缩放裁剪、像素化、落盘）
- files.py   文件名校验、扩展名白名单、大小校验、防路径穿越

约束：不 import services / pipeline / database / api；不抛 HTTPException；
配置以参数传入而非函数内读全局，便于单测。CPU 密集调用由 pipeline 用 to_thread 包装。

详见 docs/backend-standards.md 第 8 节。
"""
