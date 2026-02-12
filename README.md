# リンクラ工具箱

## 项目概览

リンクラ工具箱是面向《Link Like ラブライブ！》ライブグランプリ（LGP）赛事的非官方数据采集与辅助分析工具。项目提供一套基于 PyQt5 的桌面界面，配合多线程采集脚本，帮助玩家或社团快速获取个人战、公会战以及赛季等级（grade）榜单数据，并导出为 Excel 便于后续统计、留档或分享。

> ⚠️ 本项目仅供学习与个人研究使用，所有接口均来自官方移动端 API。请尊重游戏运营方的服务条款，避免滥用导致账号或 IP 限制。

## 核心能力

- **桌面 GUI**：模块化 PyQt5 组件（Header、ControlCard、ButtonGroup、LogWidget），提供一键采集、实时日志、客户端版本管理等功能。
- **自动化配置**：启动时支持自动检测最新客户端版本；GUI 会尝试解析官网公告取得 LGP 期数、举办时间并更新配置。
- **多线程采集**：`multicatch.py` 与 `catchgraderank.py` 内置线程池，加速排行榜批量请求、玩家详细信息抓取，并输出进度日志。
- **数据导出**：所有排行榜、粉丝等级、历史记录等结果默认写入 `X月个人战/`、`data/` 等目录下的 Excel 文件。
- **账号与版本管理**：`login.py` 负责登录获取 token/资源版本，`update_client_version.py` / `update_res_version.py` 用于独立更新配置。
- **工具脚本**：`get_info.py`、`linkura_version_checker.py` 等脚本帮助开发者快速调试新接口或校验版本。

## 目录结构

```
├─main.py                     # GUI 入口，负责 QApplication 生命周期管理
├─ui/                         # 界面层：组件、样式、后台线程
│  ├─components/              # Header、ControlCard、ButtonGroup、LogWidget 等子组件
│  ├─utils/                   # 样式、图片加载、GUI 日志处理等工具
│  └─workers/logger_thread.py # 采集任务线程，负责执行脚本并回传日志
├─config.py                   # 全局配置中心（API 端点、headers、保存路径、活动 ID 计算等）
├─utils.py                    # 网络请求封装、重试机制、玩家信息解析、版本获取工具
├─multicatch.py               # 个人战/公会战排行榜采集器
├─catchgraderank.py           # 赛季等级（grade）排行榜采集器
├─login.py                    # 登录流程，刷新 token / 资源版本
├─update_client_version.py    # 独立更新客户端版本脚本
├─update_res_version.py       # 独立更新资源版本脚本
├─linkura_version_checker.py  # App Store & API 双通道版本检查工具
├─get_info.py                 # 单接口调试脚本
├─fanlv.py                    # 粉丝等级数据格式化输出
├─data/                       # 历史归档示例（按期数划分）
├─X月个人战 / X月公会战       # GUI 运行后生成的月度数据目录
├─account.json                # 当前账号、token、版本号配置（运行时自动维护）
└─requirements.txt            # Python 依赖清单
```

## 环境要求

- Python 3.10 及以上（推荐在 Windows 10/11 环境运行，已考虑 PyInstaller 打包场景）
- 依赖包见 `requirements.txt`：`requests`、`pandas`、`openpyxl`、`PyQt5`
- 访问网络（需要可以访问游戏 API 及 App Store 页面）

### 安装依赖

```bash
python -m venv venv
venv\Scripts\activate          # PowerShell / CMD
pip install -r requirements.txt
```

如需打包为 Windows 可执行文件，可参考 PyInstaller 基本流程，自行配置 spec 脚本并复制 `icon.ico`。

## 初始化与运行

1. **准备账号信息**  
   - 编辑项目根目录下的 `account.json`，至少填入一个账号的 `player_id`、`device_id`。
   - 如果是首次使用，可直接运行 `python login.py`，脚本会在必要时调用 `register.py` 生成测试账号。

2. **刷新认证与版本号**  
   - `python login.py`：登录后写入最新 `token`、`resource_version`。  
   - `python update_client_version.py`：从 App Store 抓取最新版客户端号并同步到 `account.json` / `config.py`。  
   - `python update_res_version.py`：通过登录接口刷新资源版本号。

3. **启动 GUI**  
   ```bash
   python main.py
   ```
   - 首次启动会自动抓取官网公告更新 LGP 开始日期，并生成当月的保存目录。  
   - 在「控制面板」输入或确认客户端版本，选择 LGP 类型（个人战/公会战/grade）与榜单类型（当前/前日）。  
   - 点击「开始获取」，日志栏会显示采集进度、错误与成功提示。采集完成后可在左侧目录查看生成的 Excel。

4. **命令行采集（可选）**  
   - `python multicatch.py 21`：获取当日个人战排行榜（21 表示个人当日榜，20 为前日榜）。  
   - `python catchgraderank.py`：获取赛季等级排行榜。  
   - 采集脚本会自动在对应月度目录下生成 `...排行榜基础数据.xlsx`、`...排行榜完整数据.xlsx` 等文件。

## 配置与扩展

### account.json

```json
{
  "current_account": "新注册",
  "accounts": {
    "新注册": {
      "device_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "player_id": "XXXXXXXXX"
    }
  },
  "auth": {
    "token": "Bearer token",
    "resource_version": "R25XXXXX",
    "client_version": "4.x.x"
  }
}
```

- `login.py` 在成功登录后会自动覆盖 `auth.token`、`auth.resource_version`。  
- 若存在多个账号，可新增条目并修改 `current_account`。  
- 该文件默认位于项目根目录，打包后会改为保存在用户临时目录下（参见 `config.save_account_config`）。

### config.py 重点

- **API 端点与请求头**：`BASE_URL`、`HEADERS` 集中管理所有接口及认证参数。  
- **活动 ID / 赛季 ID**：`calculate_event_id()`、`calculate_grade_id()` 根据月份与 LGP 类型生成请求所需的标识。  
- **保存路径策略**：`generate_save_directory()`、`get_save_path()` 会依据当前月份和个人战/公会战自动生成诸如 `10月个人战` 的目录。  
- **自动更新时间**：`update_lgp_start_date()` / `set_gui_event_id()` 与 GUI 协作，将公告解析结果反向写入配置并在运行时重载。  
- **目标排名列表**：`target_ranks` 默认覆盖至 99999 名，可通过 `TARGET_RANK` / `TEST_MODE` 调整范围。

如需新增榜单类型或调整导出文件命名规则，可修改 `FILE_NAMES` 与 `RankingDataCollector.ranking_types` 映射。

### utils.py 亮点

- `retry_request` 装饰器：提供指数退避、错误码检查（含非比赛期间的强制退出）。
- `fetch_player_profile`：整合玩家基础信息、粉丝等级、DR 等指标并按角色输出列。  
- `get_client_version` / `get_resource_version`：分别从 App Store、登录接口获取最新版本号。  
- `log_progress`：统一日志入口，配合 `logging_config.py` 输出到 GUI / 控制台。

## 数据导出规则

- **目录命名**：默认使用「`{月份}{个人战|公会战}`」或 `data/{期数}` 格式，GUI 会根据最新公告自动更新。  
- **文件命名**：`config.FILE_NAMES` 定义了基础榜单、完整榜单、缺失档案、粉丝等级等 Excel 文件的命名模板。  
- **Excel 结构**：
  - 基础榜单：包含 rank、point、player_id 等核心字段。  
  - 完整榜单：在基础数据基础上追加玩家详细信息（昵称、角色粉丝等级、A/B/C/音游榜等）。  
  - 粉丝等级：`fanlv.py` 将数据拆分为「总览」「历史记录」两个 sheet。  
  - 赛季等级：输出基础信息与详细信息两份表格。

## 常见问题（FAQ）

1. **无法登录 / token 过期**  
   - 确认 `account.json` 中的 `player_id`、`device_id` 正确无误。  
   - 重新运行 `python login.py`，如仍失败请检查网络或是否被官方限制访问。

2. **采集时提示“非比赛期间”**  
   - 官方服务器会在非比赛期返回错误码 `21001_210102`，脚本会直接中止。请等待新一轮 LGP 开启。  
   - 如果确定已开赛，可先手动点击 GUI 的“刷新 LGP 信息”按钮以更新活动 ID。

3. **导出目录为空或 Excel 未生成**  
   - 查看日志中是否有“无数据”“接口返回空列表”等提示；若多线程任务遇到异常，会在 GUI 日志中直接展示。  
   - 建议先用较小的 `TARGET_RANK` 进行测试，确认账号是否有权限访问对应排行榜。

4. **图片加载失败**  
   - LGP 公告图来自官网，若请求被阻断或证书异常，`HeaderWidget` 会在日志栏写出错误信息。可尝试切换网络或手动填入图片。  

5. **访问频率限制 / 429 错误**  
   - 多线程会对 API 造成高并发压力，建议合理设置查询范围，或分批次执行采集脚本。  
   - 必要时在 `RankingDataCollector` 中降低 `max_workers`。

## 开发与扩展建议

- **模块化 UI**：`ui/components` 采用轻耦合设计，可按需增加新的控制面板、图表组件。  
- **线程输出**：`LoggerThread.StreamRedirector` 对高频日志做了采样（每 500 条输出一次），若需更细粒度进度，可调整阈值。  
- **安全性**：项目中存在硬编码 `x-api-key`、`verify=False` 等实现，为了安全请在私有环境中使用，勿将敏感配置上传公开仓库。  
- **打包部署**：`config.save_account_config` 已处理 PyInstaller `sys._MEIPASS` 场景，如需进一步封装请同步调整资源路径。

## 许可证

本项目采用 [MIT License](LICENSE)。在遵守协议的前提下，欢迎二次开发或集成到自己的工作流中。

---

如在使用过程中遇到问题，建议先查看 GUI 日志输出或 `logs/`（如自行扩展）中的详细记录，再结合 `utils.retry_request` 的异常信息定位问题。欢迎通过 Issue / PR 分享改进方案，共同完善工具链。祝使用愉快！
