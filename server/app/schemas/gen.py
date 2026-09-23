"""生成接口的请求 / 响应模型

与前端字段一一对应（见 web/src/views/workSpace/nodesComponent/GenImageNode/GenImageNode.vue
的 onGenerate payload，以及 web/src/views/workSpace/api/gen.js）
"""

from pydantic import BaseModel, Field


class GenSetting(BaseModel):
    """生成配置：对应节点工具栏 + 提示词输入区的设置项"""

    model: str = Field(default="flux-schnell", description="模型标识")
    mode: str = Field(default="hd", description="hd 高清像素画 / perfect 完美像素画")
    size: int = Field(default=64, description="像素画边长")
    image: str = Field(default="", description="参考图地址（上传结果或 dataURL）")


class GenUpstreamNode(BaseModel):
    """上游节点信息（通过连线指向当前节点的节点）"""

    id: str = Field(description="节点 id")
    index: int | None = Field(default=None, description="节点序号")
    label: str = Field(default="", description="节点名称")
    image: str = Field(default="", description="节点图片地址")


class GenRequest(BaseModel):
    """生成请求体"""

    id: str = Field(description="发起生成的节点 id")
    setting: GenSetting = Field(default_factory=GenSetting)
    text: str = Field(default="", description="提示词文本（@ 引用已序列化为 @#序号）")
    nodes: list[GenUpstreamNode] = Field(default_factory=list, description="上游节点列表")


class GenResponse(BaseModel):
    """生成响应：前端拿到 image 后写入节点 data.image"""

    image: str = Field(description="生成结果图片地址")
