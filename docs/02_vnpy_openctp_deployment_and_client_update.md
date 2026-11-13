# vn.py OpenCTP 服务与 Windows 客户端操作指南

- 更新日期：2026-11-13
- 默认分支：`master`；开发分支/worktree：`vnpy-opt-setup`（保留）。
- 设计依据：[01 号可行性报告](01_vnpy_linux_server_windows_client_feasibility.md)。

## 1. 当前服务端

服务已部署在本机 `skjl221`，使用你的 OpenCTP **7x24 账户**，交易接口与行情接口均已登录。当前没有切换到交易时段仿真账户。

| 项目 | 当前值 |
| --- | --- |
| 主机 | `skjl221`，Rocky Linux 9.3，x86_64 |
| 局域网地址 | `192.168.20.221`（客户端须能经局域网/VPN/SSH 访问） |
| Python / vn.py | Python 3.11.8 / vn.py 4.5.0，editable 安装 |
| 网关依赖 | `vnpy_ctp==6.7.11.4`、`vnpy_rpcservice==1.1.0` |
| 原生接口 | OpenCTP TTS CTPAPI 6.7.11，交易与行情库均已安装 |
| 交易前置 | `tcp://trading.openctp.cn:30001` |
| 行情前置 | `tcp://trading.openctp.cn:30011` |
| BrokerID | `9999`，AppID / AuthCode 留空 |
| 服务 | 用户级 systemd 单元 `vnpy-openctp.service`，已启动并启用 |
| 会话持久化 | `Linger=yes`，服务无需保持 SSH 会话；用户服务随系统启动 |
| RPC 请求 / 推送 | `tcp://127.0.0.1:2014` / `tcp://127.0.0.1:4102` |
| 源码目录 | `/home/chao/projs/worktrees/trd_opt_vnpy/vnpy-opt-setup` |
| 虚拟环境 | `/home/chao/.venvs/vnpy-opt-setup` |
| 凭据配置 | `/home/chao/.config/vnpy-opt-setup/openctp.env`，权限 `600`，在仓库外 |
| 状态及日志 | `/home/chao/.local/share/vnpy-opt-setup` |

OpenCTP 7x24 是历史行情循环回放和模拟撮合环境，报价时间可能是前一交易日。它适合开发测试，不能把回放报价当成当前实盘报价。服务端 `柜台环境=测试` 是原生 API 参数；实际模拟环境由 **TTS 动态库、OpenCTP 前置和账户**共同确定，该参数本身不是禁止下单的风控开关。

本次验证结果：

- 交易登录、行情登录、结算确认及合约查询均通过。
- 共加载 **27024** 个期货/期权合约（当次环境快照），已取得 1 个账户快照。
- 通过 RPC 订阅并收到 `au2612.SHFE` 和 `au2612C1000.SHFE` 的推送报价，期货和期权两条行情链路均通过。
- 重启 systemd 服务后，重新登录、合约查询、账户查询及两条行情推送复验通过。
- 本次只执行登录、查询、订阅，**未提交或撤销任何订单**；成交及组合执行能力另行验收。
- Windows 安装脚本已在 GitHub Windows runner 上通过真实 Windows PowerShell/bat 安装验证；Qt Trader 窗口离屏启动也通过。你的 PC 到本机服务器的 SSH 网络与实际界面操作按下面步骤验收。

服务端已加入本项目专用 `OpenCtpGateway` 适配层，只接收中金所、上期所、郑商所、大商所、能源中心、广期所的期货和期权合约；OpenCTP 返回的其他市场合约会被过滤，查询最后一条被过滤时也能正确完成初始化。

## 2. 你现在应在 Windows 上执行的步骤

所有命令在 **PowerShell** 中执行。本指南使用固定虚拟环境和自动检测脚本，不依赖 Python Launcher。无需安装 VeighNa Studio 或再次克隆已有仓库。

### 2.1 更新你已经克隆的目录

先关闭正在运行的 Trader，再执行：

```powershell
cd C:\vnpy-opt
git switch master
git pull --ff-only origin master
```

如果是在一台尚未克隆的 PC 上，先执行下面两行，然后继续第 2.2 节：

```powershell
git clone --branch master --single-branch https://github.com/charlesbo/vnpy.git C:\vnpy-opt
cd C:\vnpy-opt
```

### 2.2 准备 Python 3.13 或 3.11 64 位

如果你电脑上的 **Python 3.13.2 是 64 位 CPython，可以直接使用，不必再装 Python 3.11**。客户端安装脚本接受 CPython 3.13 或 3.11，优先检测 3.13；会检查解释器位数和版本，不依赖 `py` 命令。标准安装路径、注册表或 PATH 中均可查找。若当前 Python 是 32 位，或只有 Microsoft Store 的命令别名，脚本会拒绝该解释器；安装 Python 3.13 x64 官方安装版后再运行即可。

如果电脑上没有这两个版本之一，推荐安装 Python 3.13 64 位：

1. 若 PC 有 `winget`，执行：

   ```powershell
   winget install --exact --id Python.Python.3.13 --architecture x64 --source winget
   ```

2. 或从 [Python 官方 Windows 下载页](https://www.python.org/downloads/windows/)安装 **CPython 3.13 64 位**。不要选择嵌入式包或 32 位安装器。

安装后重新打开 PowerShell。若装在自定义目录，第 2.3 节支持直接指定 `python.exe` 完整路径。

### 2.3 一次性安装客户端环境

```powershell
cd C:\vnpy-opt
.\setup_client.bat
```

这个脚本会：

- 查找并实际执行解释器，验证为 **CPython 3.13 或 3.11、64 位**，跳过 Microsoft Store 的命令别名。
- 创建或复用 `C:\vnpy-opt\.venv`；不兼容的既有环境会保留，并提示你检查。
- 在该环境内升级 pip/wheel，执行 `pip install -e .`，安装 `vnpy_rpcservice==1.1.0`、`vnpy_optionmaster==1.3.0`、`vnpy_spreadtrading==1.4.0`。
- 执行 `pip check`，导入 Trader UI、RPC、OptionMaster 和 SpreadTrading，并核对 vn.py 来自本地源码目录。

如需指定 Python 的位置：

```powershell
.\setup_client.bat -PythonPath "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
```

也可以把参数替换成你的实际路径，例如：

```powershell
.\setup_client.bat -PythonPath "D:\Python313\python.exe"
```

看到 `Client environment is ready` 后即可继续。脚本会在安装步骤失败时停止，不会带着未完成的环境启动界面。该脚本只在首次安装或依赖发生变化时执行。

### 2.4 建立 SSH 隧道（内网或外网）

服务端 RPC 仅监听 `127.0.0.1`。Windows 先用 SSH 转发两个端口，Trader 始终只访问本机地址；不要把 `2014/4102` 直接暴露到公网。

在同一局域网时，PowerShell 中执行：

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:2014:127.0.0.1:2014 -L 127.0.0.1:4102:127.0.0.1:4102 chao@192.168.20.221
```

从外网连接时，先让 Linux 服务器和 Windows PC 都加入同一个获准的 VPN 网络。优先使用单位已有 VPN；也可以在两台设备安装 Tailscale 并登录到同一个 tailnet。Tailscale 默认从 `100.64.0.0/10` CGNAT 共享地址段分配 tailnet 地址。参见 [Tailscale IP 说明](https://tailscale.com/docs/concepts/tailscale-ip-addresses)、[Linux 安装说明](https://tailscale.com/docs/install/linux)和[Windows 安装说明](https://tailscale.com/docs/install/windows)。

服务器加入 VPN 后，在 Linux 上用 `tailscale ip -4` 查看 VPN 地址。在 Windows 上确认两台设备在线，并用 VPN 地址建立隧道：

```powershell
$server = "100.x.y.z"  # 替换成 Linux 上 tailscale ip -4 的实际输出
tailscale ping $server
Test-NetConnection $server -Port 22
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:2014:127.0.0.1:2014 -L 127.0.0.1:4102:127.0.0.1:4102 "chao@$server"
```

若单位 VPN 已能路由到服务器，把 `$server` 换成 VPN 内的服务器地址即可。SSH 目标需要允许 Linux SSH 密钥登录；防火墙仅允许经过 VPN 的 SSH 访问。先确认 Windows 有 OpenSSH Client（Windows“可选功能”），首次连接核对服务器指纹。隧道窗口须保持打开，关闭会断开行情和交易链路。当前没有替你配置 VPN；外网到 Windows 的实际网络路径仍需按上面步骤验证。

### 2.5 启动客户端并连接

在另一个 PowerShell 窗口执行：

```powershell
cd C:\vnpy-opt
.\.venv\Scripts\python.exe examples\client_server\run_windows_client.py
```

在 Trader 的菜单中选择连接 `RPC`，填写：

```text
主动请求地址：tcp://127.0.0.1:2014
推送订阅地址：tcp://127.0.0.1:4102
```

这里的 `127.0.0.1` 指 Windows 上 SSH 隧道的入口，SSH 会把请求传到 Linux 服务。连接完成后先等日志显示合约信息查询成功。输入 `au2612`、交易所 `SHFE` 可订阅期货行情；期权示例为 `au2612C1000`、`SHFE`。这些合约会随到期变化，之后请以客户端当日合约列表为准。

Windows 客户端加载 RpcGateway、OptionMaster 和 SpreadTrading，不持有 OpenCTP 密码；所有柜台连接都在 Linux 服务端。

### 2.6 期权定价、手工交易与期货/期权组合

连接 RPC 并完成合约查询后，在 Trader 的【功能】菜单打开【期权交易】（OptionMaster）。首轮配置按期权产品/期权链选择对应标的期货、年化利率及定价模型。模型要按具体合约规则选：欧式期货期权可用 Black-76，欧式股票/ETF 期权使用 Black-Scholes，美式商品期货期权可用二叉树模型（Binomial-Tree）；不能把一个模型机械套用到所有品种。之后可查看 T 型报价、理论价格和隐含波动率、波动率曲面、持仓 Greeks、情景压力测试，并用快速交易窗口手工发单。配置项见 [vn.py OptionMaster 使用说明](https://github.com/vnpy/vnpy/blob/master/docs/community/app/option_master.md)。

本项目固定的 OptionMaster wheel 带有 Python 3.13 Windows 的 Cython 定价扩展；Python 3.11 没有对应扩展时会自动回退到纯 Python 定价实现（运行时会出现提示，计算功能仍可用）。你的 Python 3.13.2 因而也是推荐版本。CI 会分别验证三种模型均能返回价格和 Greeks。

需要交易期权与期货组成的组合时，在【功能】菜单打开【价差交易】（SpreadTrading），创建自定义价差，把期权腿和期货腿按合约、买卖方向、比例和价差公式配置；先订阅各腿行情，确认价差报价正确，再使用手工价差交易。官方模块支持自定义价差、实时价差行情/持仓以及价差执行算法。它是按腿发送和管理委托的价差执行，不代表交易所原生原子组合单；一个腿部分成交、拒单或断线时，其他腿可能尚未成交，临时暴露单腿方向风险。先在 7x24 模拟环境逐腿验证撤单、部分成交、补腿和重启恢复，不能把“价差下单”视为不可拆分的一笔交易。见 [SpreadTrading 操作说明](https://github.com/vnpy/vnpy/blob/master/docs/community/app/spread_trading.md)。

职责边界：OptionMaster 的模型、报价分析和 Greeks 计算在 Windows 客户端完成；服务器负责柜台连接和最终订单路由。当前 OpenCtpGateway 已向 RPC 发布国内期货/期权合约元数据（标的、行权价、到期日、看涨/看跌类型）、报价、持仓和账户数据，因此服务端不需要重复实现定价模型。客户端离线时这些界面与本地风险分析也会停止。服务器还没有按你的账户规模配置期权净敞口、最大单笔数量、最大活动委托等服务端风控值；这些数值会直接影响可下单范围，需按你的规则定义后再接真实账户。本轮仍只测试 7x24 模拟环境，没有验证下单成交。

## 3. 后续开发中的客户端更新

对于本仓库内的纯 Python UI/客户端代码，首次安装后无需重新打包或再次安装：

1. 正常关闭 Trader。SSH 隧道可以继续保留。
2. 执行：

   ```powershell
   cd C:\vnpy-opt
   .\update_client.bat
   ```

脚本会检查当前分支为 `master`、源码没有本地未提交改动、旧客户端已退出，然后执行：

```powershell
git pull --ff-only origin master
```

随后使用固定 `.venv` 重启客户端。因为首次使用的是 editable 安装，重新启动的进程会导入刚拉取的 Python 代码。

如果本次改动包含依赖版本或新增包，拉取代码后重新执行一次 `setup_client.bat`，再启动客户端。独立仓库中的应用或原生 `.pyd`/Qt 扩展需要更新对应依赖，不能只靠主仓库拉取；客户端和服务器 RPC 数据结构也应保持兼容。

## 4. Linux 服务的日常管理

在本机 `chao` 用户的 shell 中执行：

```bash
systemctl --user status vnpy-openctp.service
systemctl --user restart vnpy-openctp.service
systemctl --user stop vnpy-openctp.service
systemctl --user start vnpy-openctp.service
```

查看日志：

```bash
tail -n 60 ~/.local/share/vnpy-opt-setup/server.log
```

凭据已存入本机受限文件，由 systemd 的 `EnvironmentFile` 读取；修改凭据后需要重启服务。不要把配置文件复制到 Git 或 Windows 客户端。服务配置模板是 [deploy/vnpy-openctp.service](../deploy/vnpy-openctp.service)。服务已启用用户 linger，退出 SSH 后仍可运行。

服务程序在加载 vn.py 前创建独立的 `.vntrader` 运行目录。启动时验证 `zh_CN.GB18030` locale 和 TTS 动态库版本；本机使用 `LOCPATH` 指向 `~/.local/share/vnpy-opt-setup/locale` 内的中文 locale，无需改变系统全局语言。

### 当前健康检查

```bash
cd /home/chao/projs/worktrees/trd_opt_vnpy/vnpy-opt-setup
set -a
source ~/.config/vnpy-opt-setup/openctp.env
set +a
/home/chao/.venvs/vnpy-opt-setup/bin/python -m examples.client_server.run_openctp_server --check
/home/chao/.venvs/vnpy-opt-setup/bin/python -m scripts.check_openctp_server --subscribe au2612.SHFE au2612C1000.SHFE --timeout 90
```

第一条检查安装、原生 API 和前置端口；第二条连接已运行服务，要求交易和行情登录、合约查询完成、有账户快照，并收到所指定两个合约的 **RPC 推送**。输出不包含密码或账户资金。

本次验证的关键输出：

```json
{
  "ready": true,
  "td_logged_in": true,
  "md_logged_in": true,
  "contracts_loaded": true,
  "contracts": 27024,
  "ticks": 2,
  "accounts": 1,
  "environment": "OpenCTP 7x24"
}
```

`ready` 表示登录和合约初始化就绪；行情推送由检查器单独等待确认。RPC 调用能返回、进程处于 active 状态或 TCP 端口可达，均不能单独证明行情已恢复。

### 更新服务器代码

本次服务使用保留的 `vnpy-opt-setup` worktree。通过本对话修改后，测试通过再重启该服务；不要用 Windows 的 bat 脚本管理 Linux。手工更新时先确认没有进行中的交易操作，再执行：

```bash
cd /home/chao/projs/worktrees/trd_opt_vnpy/vnpy-opt-setup
git pull --ff-only origin vnpy-opt-setup
systemctl --user restart vnpy-openctp.service
/home/chao/.venvs/vnpy-opt-setup/bin/python -m scripts.check_openctp_server --timeout 90
```

## 5. 服务器重建依据

本机安装组合固定为：

```bash
cd /home/chao/projs/worktrees/trd_opt_vnpy/vnpy-opt-setup
python3 -m venv /home/chao/.venvs/vnpy-opt-setup
/home/chao/.venvs/vnpy-opt-setup/bin/python -m pip install -e . vnpy_ctp==6.7.11.4 vnpy_rpcservice==1.1.0
```

OpenCTP TTS SDK 使用 [官方 6.7.11 下载](http://www.openctp.cn/download/CTPAPI/TTS/tts_6.7.11.zip)，下载文件 SHA-256 为 `f9d4aec4aa3b3d1ec9f0587d37a447f6bfe4158745226279cc078257faa3a6ee`。用 [安装助手](../scripts/install_openctp_tts_api.py) 安装到对应虚拟环境：

```bash
/home/chao/.venvs/vnpy-opt-setup/bin/python scripts/install_openctp_tts_api.py /path/to/tts_6.7.11.zip
```

本机中文 locale 来自 Rocky 官方 `glibc-langpack-zh` 包，提取 `zh_CN.gb18030` 至私有 locale 目录并创建 `zh_CN.GB18030` 别名，环境文件中配置 `LOCPATH`。重建 Rocky 主机可由管理员安装对应发行版的中文语言包；必须先用 `locale.setlocale` 验证该 locale 可用，再启动原生 CTP API。

安装 systemd 用户单元：

```bash
mkdir -p ~/.config/systemd/user
cp deploy/vnpy-openctp.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now vnpy-openctp.service
loginctl enable-linger "$USER"
```

新主机需要调整单元文件的源码路径和虚拟环境路径，并在仓库外创建权限为 `600` 的凭据配置、对应运行目录与 locale。TTS SDK 必须匹配已安装 CTP API 的三段版本。上述重建步骤供运维使用；当前主机已经配置好，Windows 安装无需重做。

## 6. BDD/TDD 与验收范围

新增场景与测试先出现失败，再实现修复，覆盖：

- 缺少 Python Launcher 时仍能按解释器路径/标准安装位置建立客户端环境。
- Python 版本与位数校验、不完整既有 venv 保留、pip 失败即停止。
- OpenCTP 返回不支持市场的合约、空末条响应、查询失败时的初始化逻辑。
- 无账户或无合约时不误报就绪、运行目录隔离、缺 locale 时启动前拒绝。
- 动态库备份与版本检查使用明确的 Linux 平台条件；不支持的主机在访问安装文件前拒绝，运行目录检查兼容 Windows 长短路径。
- 查询账户和合约后，订阅期货及期权并收到 RPC 推送；无订单调用。
- 客户端支持 Python 3.13 和 3.11，安装 OptionMaster/SpreadTrading，并将两个应用注册进 RPC Trader。
- 内网 SSH 隧道及外网 VPN+SSH 方案、期权估值工具和多腿部分成交风险说明。

本机自动化验证 **54 项通过**，执行命令：

```bash
cd /home/chao/projs/worktrees/trd_opt_vnpy/vnpy-opt-setup
PWSH=/tmp/vnpy-bootstrap-pwsh/pwsh /home/chao/.venvs/vnpy-opt-setup/bin/python -m unittest tests.test_windows_client_bootstrap tests.test_openctp_server_helpers tests.test_openctp_gateway tests.test_openctp_readiness tests.test_vnpy_openctp_setup tests.test_vnpy_opt_setup_report tests.test_options_client_workbench -v
```

其中 PowerShell 流程单元测试在 Linux 上使用真实 PowerShell 7 和模拟 Python/pip 执行。Windows CI 会分别在 CPython 3.11 和 3.13 runner 上真实安装 RPC、OptionMaster 与 SpreadTrading 依赖，并离屏打开/关闭注册这两款应用的 Trader 窗口；结果见 [Windows client setup 工作流](https://github.com/charlesbo/vnpy/actions/workflows/windows-client-setup.yml)。

- 通过 cmd.exe/bat 调用 Windows PowerShell，使用 CPython 3.11/3.13 64 位安装真实依赖和 editable core。
- `pip check`、源码位置校验、UI、RpcGateway、OptionMaster 和 SpreadTrading 导入。
- Qt Trader 主窗口及三项应用服务离屏初始化与退出，不连接账户、不发订单。

对应工作流是 [Windows client setup](../.github/workflows/windows-client-setup.yml)。这证明安装和界面初始化能在 Windows 环境运行；你的 PC 仍需按第 2 节完成 SSH 隧道和远端连接，以确认实际网络、桌面显示和操作效果。OpenCTP 模拟下单、成交、多腿执行和客户端断线恢复仍需单独验收。

## 7. 官方资料

- [Python Windows 安装说明](https://docs.python.org/3/using/windows.html)
- [Python Windows 下载页](https://www.python.org/downloads/windows/)
- [OpenCTP 模拟环境](http://www.openctp.cn/Trading.html)
- [OpenCTP TTS 接口说明](http://www.openctp.cn/TTS-CTPAPI.html)
- [vn.py CTP 网关](https://github.com/vnpy/vnpy_ctp)
- [vn.py RPC 服务](https://github.com/vnpy/vnpy_rpcservice)
- [vn.py OptionMaster](https://github.com/vnpy/vnpy_optionmaster)
- [vn.py SpreadTrading](https://github.com/vnpy/vnpy_spreadtrading)
