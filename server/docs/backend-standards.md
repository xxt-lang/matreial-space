# Python 后端开发规范（material-space / server）

适用范围：`server/` 下所有 Python 代码。

目标：**分层清晰、依赖单向、职责单一**，让「模型换实现、存储换对象存储、数据库换 MySQL」都只动一层。

---

## 1. 分层总览（五层）

```
                         HTTP 请求
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │ Controller      app/api/               │  协议转换层
        │ 路由 / 参数校验 / 状态码 / 响应模型      │  不含业务逻辑
        └───────────────────┬────────────────────┘
                            ▼
        ┌────────────────────────────────────────┐
        │ Service         app/services/          │  业务编排层
        │ 用例实现 / 事务边界 / 领域异常           │  不感知 HTTP / SQL
        └────────┬──────────────────────┬────────┘
                 ▼                      ▼
   ┌───────────────────────┐  ┌───────────────────────────┐
   │ Pipeline              │  │ Database                  │
   │ app/pipeline/         │  │ app/database/             │
   │ 模型流程 / 推理编排     │  │ ORM / SQL / 仓储           │
   │ 不感知 HTTP / DB       │  │ 不感知 HTTP / 业务规则      │
   └──────────┬────────────┘  └─────────────┬─────────────┘
              └──────────────┬──────────────┘
                             ▼
        ┌────────────────────────────────────────┐
        │ Utils           app/utils/             │  叶子层
        │ 图像转换 / 编解码 / 纯工具函数           │  无状态、纯函数
        └────────────────────────────────────────┘
```

**依赖方向（严格单向，禁止反向）**

| 调用方 | 允许调用 | 禁止调用 |
| --- | --- | --- |
| Controller | Service、Schemas | Database、Pipeline、Utils（如需转换请下沉到 Service） |
| Service | Pipeline、Database、Utils、Config | Controller |
| Pipeline | Utils、Config、模型 SDK | Database、Service、Controller |
| Database | Utils、Config | Pipeline、Service、Controller |
| Utils | 标准库、Config（只读） | 以上任何一层 |

> `app/schemas/` 是横切的 DTO 定义，各层都可以 import（纯数据模型，无副作用）。
> `app/config.py` 同理，只读配置。

**判断某段代码该放哪一层，依次问：**

1. 是 HTTP 协议细节（状态码、Header、请求体解析）？→ Controller
2. 是无业务语义的通用转换（bytes ↔ dataURL、缩放、裁剪）？→ Utils
3. 是「模型怎么跑、提示词怎么编排、步骤怎么串」？→ Pipeline
4. 是「SQL / 表结构 / 存取数据」？→ Database
5. 其余（用例编排、多个组件协作、事务、权限判断）→ Service

---

## 2. 目录结构

```
server/
├─ app/
│  ├─ main.py                 # 入口：CORS、路由挂载、lifespan（模型加载 / 资源初始化）
│  ├─ config.py               # 配置（pydantic-settings，读 .env）
│  ├─ exceptions.py           # 领域异常定义 + 统一异常处理器
│  ├─ api/                    # ① Controller 层
│  │  ├─ router.py            #   路由汇总挂载
│  │  ├─ health.py
│  │  ├─ gen.py
│  │  └─ upload.py
│  ├─ schemas/                # 横切：请求 / 响应 / DTO
│  ├─ services/               # ② Service 层
│  ├─ pipeline/               # ③ Pipeline 模型流程层
│  ├─ database/               # ④ Database 层
│  │  ├─ base.py              #   Base / engine / session 工厂
│  │  ├─ models.py            #   ORM 表定义
│  │  └─ repositories/        #   仓储（数据访问）
│  └─ utils/                  # ⑤ Utils 工具层
│     ├─ image.py             #   图像转换
│     └─ files.py             #   文件 / 路径 / 校验
├─ tests/
├─ uploads/                   # 上传产物（运行时生成）
├─ data/                      # SQLite 数据库文件（运行时生成，仅保留 .gitkeep）
└─ docs/backend-standards.md  # 本文档
```

> 关于命名：Controller 层当前目录名是 `app/api/`，语义上等价于 `controller/`。
> 保持 `app/api/` 是为了与前端 `web/src/**/api/` 的命名一致、避免无谓的批量改 import；
> 若团队统一要求字面量 `controller/`，一次性重命名即可（涉及 `main.py`、`api/router.py`、`tests/`）。

---

## 3. Controller 层（`app/api/`）

**只做四件事：**

1. 声明路由与 HTTP 方法，用 `response_model` 约束响应
2. 通过 `schemas` 校验入参（类型、必填、默认值交给 Pydantic）
3. 调用 Service，把结果转成响应模型
4. 把领域异常映射为 HTTP 状态码

**禁止：**

- 写业务分支（`if mode == "hd": ...` 这类判断放 Service / Pipeline）
- 直接操作数据库、Session、ORM 对象
- 直接调用模型或 Pipeline
- 读写文件、做图像转换
- 出现 SQL 字符串

**写法约定：**

- 一个业务资源一个文件，模块级 `router = APIRouter()`，在 `api/router.py` 统一挂载
- 路由函数命名用动词短语：`create_generation`、`upload_image`
- 路由函数保持「三行式」：取参 → 调 service → 组装响应
- 异常统一映射，不要在路由里 `try/except` 撒网

```python
# app/api/gen.py
@router.post("", response_model=GenResponse)
async def create_generation(payload: GenRequest) -> GenResponse:
    image = await generate_image(payload)          # 只转发，不含逻辑
    return GenResponse(image=image)
```

异常统一映射（推荐做法，见 `app/exceptions.py`）：业务异常基类 `AppError` 携带 `status_code`，
在 `main.py` 注册一次处理器，路由层就完全不需要 `try/except`：

```python
# app/main.py
app.add_exception_handler(AppError, app_error_handler)
```

---

## 4. Schemas 层（`app/schemas/`）

- 只放 Pydantic 模型，不放逻辑、不 `import` 业务模块
- 命名：入参 `XxxRequest`，出参 `XxxResponse`，层间传递 `XxxDTO`
- 字段描述用 `Field(description=...)`，会直接出现在 `/docs`，与前端契约一一对应
- **ORM 模型不得作为接口出入参**，Service 负责 ORM ↔ Schema 的转换
- 前端字段名保持 snake_case 对齐，不做无意义的重命名

---

## 5. Service 层（`app/services/`）

业务用例的唯一实现处，一个用例一个函数（复杂用例可用类，构造函数注入依赖）。

**职责：**

- 编排：组合 Pipeline、Database、Utils 完成一个完整用例
- **事务边界**：一个用例一个事务，`async with session.begin()` 在这里；Repository 不负责 commit
- 领域异常抛出（`GenerationCancelled`、`NodeNotFound` 等）
- 业务规则校验（配额、权限、状态流转）

**禁止：**

- `import fastapi`（尤其不要传 `Request` / `HTTPException` 进来）
- 写 SQL、直接 `session.execute`
- 直接调用模型 SDK（必须经 Pipeline）

**关于「取消 / 进度」这类请求上下文：**
不要直接把 `fastapi.Request` 传进 Service，改用 Protocol 抽象，Service 才可独立测试、也可复用于任务队列：

```python
# app/services/generator.py
class CancelToken(Protocol):
    """取消信号：HTTP 场景由请求连接状态实现，队列场景由任务状态实现"""
    async def cancelled(self) -> bool: ...


async def generate_image(payload: GenRequest, cancel: CancelToken) -> str:
    result = await ImageGenPipeline().run(
        prompt=payload.text,
        setting=payload.setting,
        refs=[node.image for node in payload.nodes],
        cancel=cancel,
    )
    return result.url
```

---

## 6. Pipeline 层 —— 模型流程层（`app/pipeline/`）

把「一次模型调用」拆成可组合、可复用、可测试的**步骤链**，是本项目与模型强耦合的唯一位置。

**职责：**

- 提示词组装（模板、`@#序号` 引用解析、负向提示词）
- 输入预处理（参考图解码、尺寸归一、mask 生成）—— 具体转换调用 `utils/image.py`
- 模型调用（加载、推理、采样参数、批处理）
- 输出后处理（编码、落盘、返回统一结果对象）
- 取消检查、超时控制、重试

**禁止：**

- `import fastapi`、操作数据库、写业务规则（如"用户有没有额度"）
- 直接使用 HTTP Schema 作为内部入参（用 dataclass / DTO，解耦前端字段变动）

**约定：**

- 文件命名 `*_pipeline.py`，主类/函数名 `XxxPipeline`，入口方法统一 `run()`
- 步骤用统一签名，便于增删与单测：
  ```python
  class Step(Protocol):
      name: str
      async def run(self, ctx: GenContext) -> GenContext: ...
  ```
- 输入输出用 `@dataclass` 的 `GenContext`，贯穿整条链
- 模型实例**单例**：在 `main.py` 的 `lifespan` 里加载/释放，或模块级懒加载 + 锁；不要每次请求加载权重
- **同步阻塞的推理必须 `await asyncio.to_thread(...)`**，禁止阻塞事件循环
- 每个耗时步骤前检查 `cancel.cancelled()`，被取消时抛 `GenerationCancelled`
- 模型路径 / 超时 / 采样默认值全部走 `app/config.py`，不硬编码

```python
# app/pipeline/image_gen.py
@dataclass(slots=True)
class GenContext:
    prompt: str
    size: int
    mode: str
    refs: list[str]          # dataURL 或 /uploads/xxx
    images: list[Image.Image] = field(default_factory=list)
    output: bytes | None = None


class ImageGenPipeline:
    """提示词 → 预处理 → 推理 → 编码，整条流程对 Service 只暴露 run()"""

    async def run(self, ctx: GenContext, cancel: CancelToken) -> bytes:
        ctx = await self._prepare(ctx)
        await self._check(cancel)
        ctx = await self._infer(ctx)            # 内部 asyncio.to_thread(模型)
        await self._check(cancel)
        return await self._encode(ctx)
```

---

## 7. Database 层（`app/database/`）

**唯一允许出现 SQL / ORM 的地方。**

```
app/database/
├─ base.py              # Base、engine、async_session_maker、get_session() 依赖
├─ models.py            # ORM 表定义（有多个实体时可拆成 models/ 包）
└─ repositories/        # 仓储：一个聚合一个文件
   └─ generation.py     # GenerationRepository
```

**职责：**

- `base.py`：创建 engine / session 工厂，提供 FastAPI 依赖 `get_session()`
- `models.py`：表结构，字段用 `Mapped[...]` 注解；时间戳、主键等公共列抽 `TimestampMixin`
- `repositories/`：封装数据访问，方法返回 ORM 对象或 DTO

**约定：**

- 仓储方法命名固定几类：`get_by_id` / `get_xxx` / `list_xxx` / `add` / `update` / `delete`
- **仓储不 commit**，事务由 Service 控制：`async with session.begin():`
- 查询参数化（ORM 表达式 / 绑定参数），禁止字符串拼接 SQL
- 表名、列名 `snake_case`；迁移后续引入 Alembic 统一管理，禁止上线手改表结构
- 数据库连接串放 `config.py`（`database_url`），默认 `sqlite+aiosqlite:///./data/app.db`

```python
# app/database/repositories/generation.py
class GenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, gen_id: str) -> Generation | None:
        return await self._session.get(Generation, gen_id)

    async def add(self, record: Generation) -> Generation:
        self._session.add(record)
        await self._session.flush()      # 不 commit，交给 Service 的事务
        return record
```

---

## 8. Utils 层 —— 工具函数层（`app/utils/`）

放**无业务语义、无状态、可独立单测**的通用函数。本项目的重点是图像转换。

**图像相关（`app/utils/image.py`）：**

- dataURL ↔ bytes 互转、base64 编解码
- 格式转换（PNG / JPEG / WebP）、RGB 化、alpha 处理
- 缩放、裁剪、等比适配、九宫格切图、像素化
- 读取 `/uploads/xxx` 或外链为 `PIL.Image`
- 保存到上传目录（统一 uuid 命名）

**其他常用（`app/utils/files.py`）：**

- 安全文件名校验、扩展名白名单、大小校验、防路径穿越

**约定：**

- 纯函数：输入明确、输出明确，除显式的「写文件」函数外无副作用
- **不 import** `services` / `pipeline` / `database` / `api`
- 配置以**参数**传入（如 `max_bytes`）而不是在函数内直接读全局，便于单测
- 抛 `ValueError` 之类的标准异常，或统一用 `app/exceptions.py` 的 `ErrInvalidImage`；**不要抛 HTTPException**
- 图像处理是 CPU/IO 计算，调用方（Pipeline）负责用 `asyncio.to_thread` 包起来

```python
# app/utils/image.py
def data_url_to_bytes(data_url: str) -> bytes:
    """data:image/png;base64,xxx → 原始字节"""
    _, _, encoded = data_url.partition(",")
    return base64.b64decode(encoded)


def to_png(image: Image.Image, *, size: int | None = None) -> bytes:
    """统一转成 PNG 字节；size 给定时按像素画模式做最近邻缩放"""
    if size:
        image = image.resize((size, size), Image.Resampling.NEAREST)
    buffer = BytesIO()
    image.convert("RGBA").save(buffer, format="PNG")
    return buffer.getvalue()
```

**与 Utils 划清界限：**
「把图转成 PNG」是 Utils；「按节点 mode 决定转成什么样、再喂给哪个模型」是 Pipeline；
「生成完成后落库 + 返回给前端」是 Service。

---

## 9. 横切规范

**配置**：所有配置集中在 `app/config.py` 的 `Settings`，取用一律 `get_settings()`；
新增配置项时同步更新 `.env.example`。禁止在业务代码里 `os.getenv`。

**异常**：`app/exceptions.py` 定义 `AppError(code, message, status_code)` 及子类
（`NotFoundError`、`InvalidInputError`、`GenerationCancelled`…）；
在 `main.py` 注册处理器统一转成 `{"code", "message"}` 响应，并记录日志。
业务层抛领域异常，Controller 层不写状态码。

**日志**：`logging.getLogger("material_space.<模块>")`；用 `%s` 惰性格式化；
禁止 `print`；异常路径必须带上下文（`node=%s`、`gen_id=%s`）。

**异步**：IO 全 async；阻塞/CPU 密集用 `asyncio.to_thread` 或进程池；
不要在 `async def` 里做重计算，也不要 `time.sleep`。

**类型与风格**：

- 所有函数（含私有函数）写完整类型注解；`-> None` 不省略
- 模块、函数、变量 `snake_case`；类 `PascalCase`；常量 `UPPER_SNAKE_CASE`
- 模块首行必写模块 docstring（说明该文件职责），公开函数写 docstring
- 绝对导入 `from app.xxx import ...`；禁止相对导入跨层
- 私有函数/常量以 `_` 前缀
- 建议接入 `ruff`（lint + format）与 `mypy`，统一在 `pyproject.toml` 配置

**安全**：上传只信任扩展名白名单 + 大小上限；落盘文件名一律 uuid + 安全扩展名；
不接受用户提供的路径片段。

---

## 10. 测试规范

```
tests/
├─ api/           # 路由层：TestClient 打接口，断言状态码与响应体
├─ services/      # 业务层：mock 掉 pipeline / repository，测编排与事务
├─ pipeline/      # 流程层：mock 模型，测步骤顺序、取消、参数组装
└─ utils/         # 工具层：纯函数输入输出对拍，不碰网络 / 磁盘
```

- 分层测试：哪一层的测试只 mock 它的**下游**，上级用真实实现
- 不允许测试里下载模型或调外网；模型必须可注入/可替换
- 命名 `test_<行为>`，断言具体值而不是 `assert result`

---

## 11. 新增一个能力时的落地清单

1. `app/schemas/` 定义 Request / Response（对齐前端字段）
2. 需要新表 → `app/database/models.py` + `repositories/` 仓储方法
3. 涉及模型 / 推理 → `app/pipeline/xxx_pipeline.py` 组装步骤
4. `app/services/` 写用例：编排 + 事务 + 领域异常
5. `app/api/xxx.py` 加路由，并在 `api/router.py` 挂载
6. `tests/` 按层补测试
7. 更新 `server/README.md` 接口表

---

## 12. 现有代码的对照与迁移建议

| 现状 | 目标位置 | 说明 |
| --- | --- | --- |
| `api/gen.py`、`api/upload.py` | Controller | 已符合；`gen.py` 的 `try/except` 后续可被统一异常处理器取代 |
| `services/generator.py` 的编排 | Service | `generate_image(payload, request)` → 改收 `CancelToken`，去掉对 `Request` 的依赖 |
| `services/generator.py::_mock_image` | Utils | SVG/dataURL 生成是纯转换，应下沉 `utils/image.py` |
| 真实推理调用（未来） | Pipeline | 新增 `pipeline/image_gen.py`，模型单例在 `lifespan` 加载 |
| `GenerationCancelled` | `app/exceptions.py` | 继承 `AppError`，由处理器映射为 499 |
| 上传落盘逻辑 | Service + Utils | 校验/路径处理进 `utils/files.py`，落盘编排留在 Service |
| 数据库（尚未使用） | Database | 建 `database/base.py` 与首个仓储，节点/生成记录优先落库 |
