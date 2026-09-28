# JevChat-Windows 开发环境

这个分支用于当前 Jev 私人自用版本的持续开发与测试。

现在项目已经不是早期的 `main.py / app / core` 三块结构。开发环境采用：

- `JevChat-Dev.exe + _internal/`：冻结 Python 运行时与第三方依赖
- `main.py / app/ / core/ / vendor/`：外置业务源码和上游知识/算法快照
- `runtime-generation.txt`：冻结运行时代际
- `runtime-sync.txt`：V2 同步清单
- `更新开发源码.exe`：按同步清单更新，不再把目录写死在更新器里

## 第一次使用

1. 到 GitHub Actions 下载最新成功的 `JevChat-Windows-Dev`。
2. 解压到固定目录，例如 `D:\JevChat-Windows-Dev\`。
3. 双击 `JevChat-Dev.exe`。

不需要另外安装 Python。

## 目录结构

```text
JevChat-Windows-Dev/
├─ JevChat-Dev.exe
├─ _internal/                    冻结 Python 运行时和第三方依赖
├─ main.py                       外置业务入口
├─ app/                          UI、持久化、服务层
├─ core/                         分析链、微信历史、人格画像
├─ vendor/                       完整/版本化的外部项目快照
├─ runtime-generation.txt        当前冻结运行时代际
├─ runtime-sync.txt              当前源码同步范围说明
├─ requirements.txt              用于判断冻结运行时是否需要重下
├─ 更新开发源码.exe               V2 图形源码更新器
└─ 用户数据                      更新器不会覆盖
```

长期关系记忆数据库现在放在用户数据目录，不依赖程序目录；普通配置、会话资料等现有用户文件同样不在 V2 同步清单里，因此不会被源码更新器覆盖。

## V2 源码同步

关闭 Jev 后运行 `更新开发源码.exe`。

更新器会：

1. 从 `Mr47Forge/jev-chat-windows` 的 `dev-external-source` 下载最新源码；
2. 读取仓库里的 `dev/runtime-sync.txt`；
3. 先把待更新内容复制到临时 staging；
4. 校验新结构必须存在的模块；
5. 备份本地现有业务源码；
6. 按清单替换；
7. 更新失败时自动回滚。

当前同步范围：

- `main.py`
- `app/`
- `core/`
- `vendor/`
- `DEV使用说明.md`

更新器不再假定项目永远只有 app/core。以后新增业务目录，只改 `dev/runtime-sync.txt` 即可。

## 什么情况下不能只点“更新开发源码”

如果出现下面任意情况，更新器会直接拒绝覆盖，并要求重新下载完整开发环境：

- `runtime-generation.txt` 代际变化；
- `requirements.txt` 发生变化；
- Python 版本变化；
- PySide6、OCR、onnxruntime、模型 SDK 等冻结依赖变化；
- 开发启动器或底层打包结构发生不兼容变化。

这是为了避免“新业务代码 + 旧冻结运行时”混跑。

## 外部项目同步

上游项目不再靠人工挑文件复制。

配置：

`vendor/upstreams.json`

同步器：

`tools/sync_upstreams.py`

支持：

```powershell
python tools/sync_upstreams.py --check
python tools/sync_upstreams.py --sync all
python tools/sync_upstreams.py --sync goutoujunshi kinkdirectory
```

完整同步会保留每个上游仓库的所有受 Git 跟踪文件，只去掉它自己的 `.git` 元数据，并把实际 commit 写入：

`vendor/UPSTREAMS.lock.json`

GitHub Actions 里的 `vendor-sync` 也可以执行同一套逻辑。

Jev 自己的融合逻辑放在 `app/` 与 `core/`，不要直接魔改 vendor 原件。这样上游更新时可以整仓覆盖，Jev 的适配层不会被冲掉。
