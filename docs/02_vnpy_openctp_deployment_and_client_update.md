# vn.py + OpenCTP 本机服务器安装与 Windows 客户端更新报告

- **版本：** 1.0
- **日期：** 2026-11-08
- **工作分支：** `vnpy-opt-setup`
- **目标分支：** `master`
- **依据：** [01 号可行性报告](01_vnpy_linux_server_windows_client_feasibility.md)

## 1. 本次交付和验证结论

本次已在当前 Linux 主机完成 vn.py 服务端开发环境、CTP 网关和 RPC 组件安装，并用 OpenCTP TTS 6.7.11 动态库替换了匹配版本的官方 CTP 动态库。已验证以下项目：

- 本机系统为 Rocky Linux 9.3 x86_64，Python 3.11.8，GCC 11.5，磁盘可用约 129 GB。
- 本机实际开发虚拟环境位于 `/home/chao/.venvs/vnpy-opt-setup`，与 Git worktree 分开，避免仓库切换或合并时污染源码目录。后文用 `.venv` 表示新服务器/Windows PC 上可自行选择的固定 venv 路径。
- vn.py 以 editable 方式安装，版本 4.5.0；`vnpy_ctp` 版本 6.7.11.4；PyPI 可获得的 `vnpy_rpcservice` 版本为 1.1.0。
- OpenCTP TTS 6.7.11 Linux x86_64 SDK 已下载并通过版本/ELF 检查；交易和行情动态库均包含 `openctp-tts v6.7.11` 标识。
- `vnpy`、`vnpy_ctp`、`vnpy_rpcservice`、`CtpGateway`、`RpcGateway` 和 `RpcServiceApp` 均可导入。
- OpenCTP 7x24 交易前置 `tcp://trading.openctp.cn:30001`、行情前置 `tcp://trading.openctp.cn:30011` 的 TCP 端口从本机可达。
- 本地 `RpcService` 与 `RpcClient` 请求链路通过：客户端能查询服务端的空合约快照；此测试没有连接柜台账户。
- 未完成 OpenCTP 登录、实时行情订阅、委托、撤单和成交验证，因为本机没有 OpenCTP 公众号注册的用户名/密码。报告把这一项明确保留为后续验收，不伪造成功结果。

服务端启动器、Windows 客户端启动器、TTS 库安装助手和 Windows 更新脚本已加入仓库。服务器默认只绑定 `127.0.0.1`，不会把 vn.py 原始 ZeroMQ RPC 端口暴露到所有网卡。

## 2. 分支规则：统一使用 master

官方 vn.py 使用 `master` 作为默认分支。本项目也统一使用 `master`：

```bash
git clone --branch master --single-branch https://github.com/charlesbo/vnpy.git C:\vnpy-opt
cd C:\vnpy-opt
git switch master
git pull --ff-only origin master
```

本次交付会先把原 `main` 上的报告内容和 `vnpy-opt-setup` 变更并入 `master` 并推送，再删除本地与远程 `main`。GitHub fork 默认分支保持 `master`。功能分支 `vnpy-opt-setup` 及其 worktree 按要求保留；Windows 客户端更新脚本也会检查当前分支必须是 `master`，避免在错误分支上更新运行环境。

## 3. 本机服务器环境

### 3.1 已发现的主机差异

本机输出如下：

```text
Rocky Linux 9.3 (Blue Onyx)
Linux x86_64
Python 3.11.8
gcc 11.5.0
```

vn.py 官方 README 明确列出 Ubuntu 22.04 LTS 以上为推荐 Linux 环境；Rocky Linux 9.3 并不是该条推荐环境。因此本次安装结果是“当前机器上的可运行验证”，不能把它扩展为官方对所有 Rocky Linux 版本的兼容承诺。正式生产部署仍建议使用 Ubuntu LTS，或者对 Rocky 的 libc、编译器、Qt、CTP 动态库、systemd 和网络条件做单独验收。

### 3.2 一次性创建虚拟环境

以下命令在服务器仓库根目录执行。生产环境应使用固定的 Python 次版本、依赖版本和 Git 提交号；不要直接使用系统 Python 或 root pip。

```bash
cd /path/to/vnpy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -e .
python -m pip install vnpy_ctp==6.7.11.4 vnpy_rpcservice==1.1.0
```

这里使用 `vnpy_rpcservice==1.1.0` 是因为 PyPI 当前可安装最高版本为 1.1.0；其 GitHub 主分支源码版本声明为 1.1.1。正式锁版本时应统一使用已经发布、经过验证的组合，不能把源码声明版本和 PyPI 安装版本混用而不测试。

本机实际使用虚拟环境 `/home/chao/.venvs/vnpy-opt-setup`（与 worktree 分开），精确安装命令为：

```bash
cd /home/chao/projs/worktrees/trd_opt_vnpy/vnpy-opt-setup
python3 -m venv /home/chao/.venvs/vnpy-opt-setup
/home/chao/.venvs/vnpy-opt-setup/bin/python -m pip install --upgrade pip wheel
/home/chao/.venvs/vnpy-opt-setup/bin/python -m pip install -e . vnpy_ctp==6.7.11.4 vnpy_rpcservice==1.1.0
```

本机 PyPI 没有适用于 `vnpy_ctp==6.7.11.4` 的 wheel，pip 从官方源码包构建了 CPython 3.11/Linux x86_64 wheel，GCC 构建成功后安装。这里的 `-e .` 指向当前 worktree，因此迭代修改 Python 服务端和客户端代码时不必重复安装 core。

### 3.3 下载和替换 OpenCTP TTS 动态库

OpenCTP 官方说明要求连接其模拟环境时使用相应版本的 TTS CTPAPI 动态库；直接使用 CTP 官方动态库可能得到 4097。当前安装的 `vnpy_ctp==6.7.11.4` 使用 6.7.11 ABI，因此下载 OpenCTP 官网的 TTS 6.7.11 SDK：

```bash
mkdir -p /tmp/openctp
cd /tmp/openctp
curl -fL -o tts_6.7.11.zip \
  http://www.openctp.cn/download/CTPAPI/TTS/tts_6.7.11.zip
sha256sum tts_6.7.11.zip
```

本次实际下载文件的 SHA-256 为：

```text
f9d4aec4aa3b3d1ec9f0587d37a447f6bfe4158745226279cc078257faa3a6ee
```

在 vn.py worktree 根目录运行安装助手：

```bash
source /home/chao/.venvs/vnpy-opt-setup/bin/activate
python scripts/install_openctp_tts_api.py /tmp/openctp/tts_6.7.11.zip
```

新服务器如使用仓库内虚拟环境，将第一行改为 `source .venv/bin/activate`。

脚本会做四项保护：只接受 x86_64 Linux；检查 SDK 中的 ELF 文件和 `openctp-tts v6.7.11` 标识；将 SDK 三段版本与已安装 `vnpy_ctp` 版本比较；替换前把原始库保存为 `.official.bak`。如果版本不匹配，脚本在写入前拒绝操作。升级 `vnpy_ctp` 或换 TTS API 时必须重新执行匹配检查，不要手工混用动态库。

### 3.4 安装结果和检查命令

在本机重跑真实检查：

```bash
/home/chao/.venvs/vnpy-opt-setup/bin/python examples/client_server/run_openctp_server.py --check
```

在新服务器上如使用仓库内 `.venv`，可以改用：

```bash
source .venv/bin/activate
python - <<'PY'
import vnpy
import vnpy_ctp
import vnpy_rpcservice
from vnpy_ctp import CtpGateway
from vnpy_rpcservice import RpcGateway, RpcServiceApp

print(vnpy.__version__)
print(vnpy_ctp.__version__)
print(vnpy_rpcservice.__version__)
print(CtpGateway, RpcGateway, RpcServiceApp)
PY

python examples/client_server/run_openctp_server.py --check
```

本次 `--check` 输出确认：

```text
vn.py=4.5.0; vnpy_ctp=6.7.11.4; vnpy_rpcservice=1.1.0
Trader API runtime reports openctp-tts v6.7.11
Market-data API native library loaded without login
TCP reachable: tcp://trading.openctp.cn:30001
TCP reachable: tcp://trading.openctp.cn:30011
Install/front connectivity checks passed; no account login or orders were attempted.
```

`--check` 不读取账户密码，不登录，不下单，只检查 Python/native 模块、TTS 动态库和两个公开 TCP 前置端口。它可以用于部署后的健康检查，但不是交易验收。

## 4. OpenCTP 服务器启动方法

### 4.1 OpenCTP 环境参数

当前采用 OpenCTP 7x24 环境：

| 项目 | 值 |
| --- | --- |
| BrokerID | `9999` |
| 交易前置 | `tcp://trading.openctp.cn:30001` |
| 行情前置 | `tcp://trading.openctp.cn:30011` |
| AppID/AuthCode | 官方页面说明无须填写 |
| 行情和撮合 | 7x24 循环回放；部分成交测试使用 TEST/BTC/MINUS 等官方指定合约 |

服务端启动配置显式使用 `"柜台环境": "测试"`。vn.py CTP Gateway 未提供该字段时默认选择“实盘”模式；模拟环境必须显式选择测试，防止 API 使用错误的运行模式。

OpenCTP 页面说明模拟账号通过公众号注册，并可在那里注册更多 7x24/仿真账号、调整资金或重置账户。账号和密码不写入 Git、代码、文档或聊天消息。

### 4.2 设置凭据并启动

在服务器当前 shell 中设置凭据：

```bash
export OPENCTP_USER_ID='公众号注册得到的用户名'
read -rsp 'OpenCTP password: ' OPENCTP_PASSWORD
export OPENCTP_PASSWORD
echo
export OPENCTP_BROKER_ID=9999
export OPENCTP_TD_FRONT='tcp://trading.openctp.cn:30001'
export OPENCTP_MD_FRONT='tcp://trading.openctp.cn:30011'
export OPENCTP_RPC_BIND_IP=127.0.0.1
```

启动无 GUI 服务：

```bash
source .venv/bin/activate
python examples/client_server/run_openctp_server.py
```

服务端使用 `MainEngine + CtpGateway + RpcServiceApp`，RPC 请求端口为 `127.0.0.1:2014`，行情/事件发布端口为 `127.0.0.1:4102`。如果 Windows 客户端在另一台机器上访问，应把 `OPENCTP_RPC_BIND_IP` 改成服务器的 VPN/私网 IP，并在主机防火墙只允许客户端 IP 访问 2014/4102；不要设置为 `0.0.0.0` 或直接映射公网。当前启动器会拒绝 wildcard bind。

未设置 `OPENCTP_USER_ID` 或 `OPENCTP_PASSWORD` 时，启动器会明确失败，不会使用示例账户或隐含密码：

```text
Set OPENCTP_USER_ID and OPENCTP_PASSWORD from your OpenCTP account before connecting.
```

本次实际执行 `/home/chao/.venvs/vnpy-opt-setup/bin/python examples/client_server/run_openctp_server.py`，启动器按预期在连接前拒绝缺少凭据；没有启动无人值守的空账户会话，也没有发送任何交易请求。你已确认稍后会在本机注册并设置 OpenCTP 账户环境变量，设置后可直接重跑同一命令。

### 4.3 本机 RPC 冒烟测试

没有柜台账户时仍可验证服务端和客户端协议链路：

```bash
source .venv/bin/activate
python scripts/smoke_test_local_rpc.py
```

本机对应命令为：

```bash
/home/chao/.venvs/vnpy-opt-setup/bin/python scripts/smoke_test_local_rpc.py
```

本次结果：

```text
PASS: local RpcClient queried RpcService; no CTP account was connected.
```

该测试只验证本机 RPC 请求/响应，不产生行情、持仓、委托或成交。账户设置完成后，应在仿真时段运行服务端，再由 Windows 客户端订阅合约，执行小规模人工下单/撤单验收，并保存日志和柜台回报。

## 5. Windows 客户端首次安装

目标是让客户端第一次安装后直接使用 Git checkout 和 editable 安装。这样纯 Python 的 UI、Trader 和客户端脚本更新时，新的 Python 进程会从 checkout 导入新代码，不需要反复重新打包或重新执行 `install.bat`。客户端仍需安装一次匹配的 Python、Qt、RPC 和应用依赖。

### 5.1 前置条件

- Windows 11 或 Windows Server 2022 以上，64 位。
- Git for Windows。
- 64 位 CPython 3.11（与服务器和已验证依赖保持一致）。
- 能通过 VPN/私网访问服务器的 RPC 2014/4102 端口。
- 已从 `charlesbo/vnpy` fork 获取访问权限；生产应使用组织内私有远程并配置 SSH key 或受控 HTTPS token。

### 5.2 首次安装命令

在 PowerShell 中执行：

```powershell
cd C:\
git clone --branch master --single-branch https://github.com/charlesbo/vnpy.git C:\vnpy-opt
cd C:\vnpy-opt

py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip wheel
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m pip install vnpy_rpcservice==1.1.0
```

如果客户端使用 CTA、组合或 OptionMaster 界面，在同一个 `.venv` 中一次性安装已经验收过的应用包，例如：

```powershell
.venv\Scripts\python.exe -m pip install vnpy_ctastrategy vnpy_optionmaster
```

客户端只加入 `RpcGateway`，不安装或连接 `CtpGateway`，所以柜台账户密码只在 Linux 服务端。将 [run_windows_client.py](../examples/client_server/run_windows_client.py) 放在 checkout 中，启动：

```powershell
.venv\Scripts\python.exe examples\client_server\run_windows_client.py
```

在 Trader 的 RPC 网关连接设置中填入服务器的 RPC 请求地址和发布地址，例如：

```text
主动请求地址：tcp://10.0.0.10:2014
推送订阅地址：tcp://10.0.0.10:4102
```

将 `10.0.0.10` 替换成服务器的 VPN/私网地址。必须先由网络管理员确认防火墙只允许授权客户端；不要使用公网裸 IP。

### 5.3 依赖和原生扩展变化的边界

纯 Python UI 和客户端代码可以按下一节直接 `git pull` 更新。以下变化不属于只拉代码就能可靠完成的范围：

- `pyproject.toml` 增加或改变依赖时，需要执行一次 `python -m pip install -e .` 或指定的依赖安装命令。
- `vnpy_rpcservice`、`vnpy_ctastrategy`、`vnpy_optionmaster` 等独立仓库发生变化时，需在对应仓库单独更新或重新安装匹配版本。
- `.pyd`、Qt、CTP 或其他原生扩展变化时，必须安装匹配二进制；不能仅靠主仓库 `git pull` 替换。
- RPC 数据结构或协议不兼容时，必须先升级客户端再升级服务端，或者提供向后兼容期。

客户端进程运行时不会热加载已 import 的模块。任何 UI 更新都必须先正常关闭 Trader，再更新并重新启动。

## 6. Windows 客户端后续更新方法

仓库根目录的 `update_client.bat` 是日常更新入口。它会从临时副本运行，避免 `git pull` 替换正在执行的 bat 文件；检查虚拟环境、当前分支和工作区是否干净；检查同一 `.venv` 中是否已有旧的 `run_windows_client.py` 进程；执行 fast-forward 更新；然后重新启动客户端。

### 日常操作

1. 正常关闭 Windows Trader，确认没有未提交的客户端本地改动。
2. 双击 `C:\vnpy-opt\update_client.bat`，或在 PowerShell 执行：

   ```powershell
   cd C:\vnpy-opt
   .\update_client.bat
   ```

3. 脚本实际执行的核心 Git 命令是：

   ```powershell
   git pull --ff-only origin master
   ```

4. 更新完成后，脚本用固定虚拟环境启动：

   ```powershell
   .venv\Scripts\python.exe examples\client_server\run_windows_client.py
   ```

因此，UI 纯 Python 改动的日常流程是“关闭客户端、运行 `update_client.bat`、客户端自动重新启动”。不需要重新打包，也不需要再次运行首次安装命令。若脚本发现 Trader 仍在运行、工作区有本地改动、分支不是 `master`、fast-forward 失败或虚拟环境不存在，它会停止并提示处理，避免覆盖本地修改或在半更新状态启动。

### 依赖变更时

如果本次提交改变了 `pyproject.toml` 或客户端独立应用依赖，更新代码后在客户端执行一次：

```powershell
cd C:\vnpy-opt
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m pip install vnpy_rpcservice==1.1.0
```

之后仍用 `update_client.bat` 启动。不要在 Trader 运行期间更新 `.pyd`、Qt 或 Python 依赖；这类变更应安排维护窗口并重新启动客户端。

## 7. 已执行的测试和结果

### 7.1 BDD/TDD 顺序

本次先添加验收测试 `tests/test_vnpy_openctp_setup.py` 和 helper 单元测试 `tests/test_openctp_server_helpers.py`。在报告、脚本和启动器尚不存在时，BDD 测试按预期失败；实现后再次运行，helper 测试 10 项通过。报告完成后，BDD 测试应全部通过。

```bash
python -m unittest tests/test_openctp_server_helpers.py -v
python -m unittest tests/test_vnpy_openctp_setup.py -v
python -m unittest tests/test_vnpy_opt_setup_report.py -v
```

测试覆盖：

- OpenCTP TCP endpoint 解析和无效协议拒绝。
- 缺少用户名/密码时拒绝启动，凭据只从环境变量读取。
- wildcard RPC bind 拒绝，默认绑定 loopback。
- TTS SDK 版本匹配、ELF/标识检查、官方库备份和不匹配时不写入。
- Windows 更新脚本使用 `git pull --ff-only origin master`、固定 `.venv` 和客户端启动脚本。
- 报告包含实际版本、端口、TTS、公众号注册、安装和更新命令，并明确未登录状态。

### 7.2 已验证与未验证边界

已验证：

- 本机 Python 包和 C++ 扩展可导入。
- vn.py CTP gateway 加载的交易接口运行时报告版本 `openctp-tts v6.7.11`，行情接口 native library 加载通过。
- OpenCTP 前置端口网络可达。
- 本机 RpcService/RpcClient 查询链路。
- OpenCTP 启动器在没有凭据时安全失败。

尚未验证：

- OpenCTP 账户登录和认证回报。
- OpenCTP 期货/商品期权合约查询及实时行情。
- 真实仿真下单、撤单、部分成交、成交回报和结算恢复。
- 两台不同主机之间经过 VPN/防火墙的 RPC 连接。
- Windows 图形界面在实际 PC 上的 Qt 渲染和更新。

这些未验证项需要用户先通过 OpenCTP 公众号取得账户，并在测试时段提供可访问的 Windows PC 和服务器网络。没有账户时不能宣称“全部部署、安装、执行”已完成交易层验收；本报告准确记录了当前可执行结果。

## 8. 账户到位后的验收步骤

在服务器设置环境变量后启动：

```bash
source .venv/bin/activate
export OPENCTP_USER_ID='你的OpenCTP用户名'
read -rsp 'OpenCTP password: ' OPENCTP_PASSWORD; export OPENCTP_PASSWORD; echo
python examples/client_server/run_openctp_server.py
```

在 Windows 客户端运行 `update_client.bat`，连接 RPC 后按顺序验收：

1. 客户端能取得合约列表，连接状态和最后更新时间正常。
2. 订阅一个有权限的期货或期权合约，确认行情来源是服务器而非本地 CTP。
3. 使用最小手数限价单测试报单、撤单和回报；先使用 OpenCTP 官方建议的测试品种和规则。
4. 重启服务端，观察客户端断线状态、重新连接和账户/持仓/活动委托快照恢复。
5. 保存服务端日志、客户端日志和柜台回报；确认凭据没有出现在日志或 Git diff 中。

OpenCTP 官方页面特别说明：其仿真环境行情可能需要直连实盘行情前置，且 TTS API 动态库必须匹配；这些条件应在行情验收失败时优先检查。实盘行情前置、券商权限和公网访问不属于本次本机安装授权范围。

## 9. 相关文件

- [OpenCTP 无 GUI 服务端](../examples/client_server/run_openctp_server.py)
- [Windows RPC 客户端](../examples/client_server/run_windows_client.py)
- [Windows 更新脚本](../update_client.bat)
- [TTS 动态库安装助手](../scripts/install_openctp_tts_api.py)
- [本机 RPC 冒烟测试](../scripts/smoke_test_local_rpc.py)
- [BDD 验收测试](../tests/test_vnpy_openctp_setup.py)
- [TDD helper 测试](../tests/test_openctp_server_helpers.py)

## 10. 官方资料

1. [OpenCTP 模拟交易环境](http://www.openctp.cn/Trading.html)
2. [OpenCTP TTS CTPAPI 说明](https://github.com/openctp/openctp/blob/master/TTS-CTPAPI/readme.md)
3. [OpenCTP CTPAPI-Python 说明](https://github.com/openctp/openctp/blob/master/ctpapi-python/readme.md)
4. [OpenCTP 官方组织和代码](https://github.com/openctp)
5. [vn.py 主仓库](https://github.com/vnpy/vnpy)
6. [vn.py CTP Gateway](https://github.com/vnpy/vnpy_ctp)
7. [vn.py RPC Service](https://github.com/vnpy/vnpy_rpcservice)
8. [vn.py client/server 示例](https://github.com/vnpy/vnpy/blob/master/examples/client_server/run_client.py)
