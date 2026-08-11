"""常量定义。

DOMAIN 是 HA 集成的唯一标识, 一经发布不可更改(改了已装用户的实体会全部失效)。
host 在配置流程里可改写, 便于指向不同部署环境。
"""
from datetime import timedelta

# HA 集成域(唯一标识，勿改)
DOMAIN = "vaysunic"

# 配置项 key
CONF_HOST = "host"          # 云端网关 base URL，形如 https://application.vaysunic.com/ha
CONF_TOKEN = "token"        # App 里生成的 HA 令牌(不透明、可禁用)

# 默认网关; 配置流程里可改写
DEFAULT_HOST = "https://application.vaysunic.com/ha"

# 实时数据轮询间隔。
# 设备约每 3 分钟上报一次, 2 分钟拉一次仍有余量, 且不会像 30 秒那样绝大多数请求
# 都取回同一份数据(过采样 6 倍)。
UPDATE_INTERVAL = timedelta(minutes=2)

# 电站/设备清单的刷新间隔。
# 这份清单几个月才变一次(电站改名、新增设备), 没必要跟实时数据同频。
# 单独降频后, 每轮通常只打 1 个请求而不是 2 个。
STATIONS_INTERVAL = timedelta(minutes=10)

# 令牌请求头(与网关约定一致)
HEADER_TOKEN = "X-HA-Token"

# 网关响应体的成功码
CODE_SUCCESS = 200
CODE_UNAUTHORIZED = 401
