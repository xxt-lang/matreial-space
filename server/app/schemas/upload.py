"""上传接口的响应模型"""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """上传成功后前端把 url 写入节点 data.image"""

    url: str = Field(description="上传后的可访问地址")
    name: str = Field(description="原始文件名")
    size: int = Field(description="文件大小（字节）")
    type: str = Field(description="MIME 类型")
