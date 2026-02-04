# Attack on Moe - Private Server

基于 FastAPI 实现的 Parse Server 兼容后端，用于运行已停服的 Attack on Moe (进击的巨萌) 游戏。

## 功能特性

- 完整的 Parse Server API 兼容层
- 用户注册/登录（支持用户名密码和 Google 登录）
- 云存档同步
- 好友系统
- PvP 战斗记录
- 邮箱系统（DropBox）
- 公告系统
- 优惠券兑换
- 货币管理（萌魂、钻石、萌水晶、金币）

## 快速开始

### 1. 安装依赖

```bash
cd server
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python admin.py init
```

这将创建数据库表并添加示例优惠券。

### 3. 启动服务器

```bash
python main.py
```

服务器将在 `http://0.0.0.0:1337` 启动。

## 配置

可以通过环境变量或 `.env` 文件配置服务器：

```env
# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./aom.db

# Parse 兼容配置
APPLICATION_ID=game.ignite.aom.prd

# 服务器配置
HOST=0.0.0.0
PORT=1337
```

## 客户端配置

要让游戏客户端连接到私服，需要修改客户端的服务器地址。

### 方法1：修改 hosts 文件

将以下内容添加到系统 hosts 文件：

```
<服务器IP> server.aom.ignite-ga.me
```

- Windows: `C:\Windows\System32\drivers\etc\hosts`
- Linux/Mac: `/etc/hosts`

### 方法2：使用代理

使用 Fiddler 或其他代理工具，将 `server.aom.ignite-ga.me` 的请求重定向到本地服务器。

### 方法3：修改客户端

如果可以修改客户端，将 Parse Server URL 改为：

```
http://<服务器IP>:1337/parse/
```

## 管理命令

### 基础命令

```bash
# 初始化数据库
python admin.py init

# 列出所有用户
python admin.py list-users

# 查看用户详细信息
python admin.py user-info <user_id>
```

### 公告管理

```bash
# 添加公告（需要有效的图片URL，推荐尺寸 900x921）
python admin.py add-notice <image_url>

# 清除所有公告
python admin.py clear-notices
```

### 优惠券管理

```bash
# 添加示例优惠券
python admin.py add-coupon
```

### 货币管理

```bash
# 设置货币（覆盖原有值）
python admin.py set-ruby <user_id> <amount>        # 萌魂
python admin.py set-gem <user_id> <amount>         # 钻石
python admin.py set-moecrystal <user_id> <amount>  # 萌水晶
python admin.py set-gold <user_id> <amount>        # 金币（云存档）
python admin.py set-fp <user_id> <amount>          # 好友点

# 增加货币（在原有基础上增加）
python admin.py add-ruby <user_id> <amount>
python admin.py add-gem <user_id> <amount>
python admin.py add-moecrystal <user_id> <amount>
python admin.py add-gold <user_id> <amount>
python admin.py add-fp <user_id> <amount>
```

### 邮箱系统 (DropBox)

邮箱系统用于向玩家发送奖励，玩家可以在游戏内领取。

```bash
# 发送邮件给单个用户
python admin.py send-mail <user_id> <type> <amount> [title] [msg]

# 发送邮件给所有用户
python admin.py send-mail-all <type> <amount> [title] [msg]

# 查看用户邮件
python admin.py list-mail <user_id>

# 清除用户邮件
python admin.py clear-mail <user_id>
```

**支持的邮件类型：**

| 类型 | 说明 |
|------|------|
| `Gold` | 金币 |
| `Gems` | 宝石/钻石 |
| `MoeCrystal` | 萌水晶 |
| `AdFree` | 免广告特权 |
| `MoetanPackages` | 角色礼包 |
| `Moetifacts` | 神器 |

**示例：**

```bash
# 给用户发送 1000 钻石
python admin.py send-mail abc123 Gems 1000 "欢迎奖励" "感谢游玩！"

# 给所有用户发送 500 萌水晶
python admin.py send-mail-all MoeCrystal 500 "维护补偿"
```

## API 端点

### Parse 兼容 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/parse/users` | POST | 用户注册 |
| `/parse/login` | POST/GET | 用户登录 |
| `/parse/logout` | POST | 用户登出 |
| `/parse/users/me` | GET | 获取当前用户 |
| `/parse/classes/{className}` | GET/POST/PUT/DELETE | 数据类操作 |
| `/parse/functions/{functionName}` | POST | Cloud Functions |
| `/parse/batch` | POST | 批量操作 |
| `/parse/config` | GET/POST | 服务器配置 |

### 优惠券 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/redeemCoupon` | POST | 兑换优惠券 |
| `/api/admin/coupons` | POST | 创建优惠券 (管理员) |
| `/api/admin/coupons` | GET | 列出优惠券 (管理员) |

## 支持的 Parse Classes

| Class | 描述 | 主要字段 |
|-------|------|----------|
| `_User` | 用户 | username, password, googleUserId |
| `UserSummary` | 用户摘要 | displayName, ruby, gem, moecrystal, friendPoint |
| `GameData` | 游戏存档 | data (JSON 字符串，包含 golds, stage, wave 等) |
| `FriendRelation` | 好友关系 | user1Id, user2Id |
| `BattleLog` | PvP 战斗记录 | senderId, receiverId, senderScore, receiverScore |
| `Notice` | 公告 | imageURL, text, url, order |
| `DropBox` | 邮箱/掉落箱 | userId, type, title, value, msg |

## 支持的 Cloud Functions

| Function | 描述 |
|----------|------|
| `clearSessionToken` | 清除会话令牌（用于解决多设备登录问题） |
| `getUserSessionToken` | 获取用户会话令牌 (Google 登录) |
| `linkGoogleID` | 关联 Google 账号 |
| `addFriend` | 添加好友 |
| `findLatestBattleLogPerFriend` | 查询好友战斗记录 |

## 货币系统说明

游戏中有多种货币，存储位置不同：

| 货币 | 中文名 | 存储位置 | 说明 |
|------|--------|----------|------|
| Ruby | 萌魂 | UserSummary | 服务端管理，客户端只读 |
| Gem | 钻石 | UserSummary | 服务端管理，客户端只读 |
| MoeCrystal | 萌水晶 | UserSummary | 服务端管理，客户端只读 |
| Gold | 金币 | GameData | 存储在云存档中，需要加载存档生效 |
| FriendPoint | 好友点 | UserSummary | 服务端管理 |

**注意：** 金币同时存储在客户端本地和云存档中。通过 admin 命令修改金币后，用户需要从云端加载存档才能生效。

## 项目结构

```
server/
├── main.py              # FastAPI 入口
├── config.py            # 配置
├── database.py          # 数据库连接
├── admin.py             # 管理脚本
├── requirements.txt     # 依赖
├── models/              # 数据模型
│   ├── user.py          # 用户和会话
│   ├── user_summary.py  # 用户摘要（货币等）
│   ├── game_data.py     # 游戏存档
│   ├── friend_relation.py # 好友关系
│   ├── battle_log.py    # 战斗记录
│   ├── notice.py        # 公告
│   ├── drop_box.py      # 邮箱
│   └── coupon.py        # 优惠券
├── routers/             # API 路由
│   ├── users.py         # 用户 API
│   ├── login.py         # 登录 API
│   ├── classes.py       # 数据类 API
│   ├── functions.py     # Cloud Functions
│   ├── batch.py         # 批量操作
│   ├── config.py        # 服务器配置
│   └── coupon.py        # 优惠券 API
└── services/            # 业务逻辑
    └── auth.py          # 认证服务
```

## 注意事项

1. **Google 登录**：当前实现将 `authCode` 直接作为 `googleUserId` 使用。如需真正的 Google OAuth 支持，需要配置 Google OAuth 凭据并实现令牌交换。

2. **安全性**：此服务器主要用于本地测试和私服运行，不建议直接暴露到公网。如需公网部署，请添加适当的安全措施（HTTPS、防火墙等）。

3. **数据持久化**：默认使用 SQLite 数据库。如需更好的性能，可以切换到 PostgreSQL 或 MySQL。

4. **版本检查**：服务器配置中的 `Version_Android` 和 `Version_iOS` 用于版本检查。如果客户端版本与服务器配置不匹配，可能会提示更新。可以在 `routers/config.py` 中修改这些值。

5. **公告图片**：添加公告时必须提供有效的图片 URL，否则客户端会卡住。推荐图片尺寸为 900x921 像素。

## 常见问题

### Q: 登录时提示 "Session token invalid"
A: 使用 `clearSessionToken` 功能清除旧的会话令牌，或者在游戏中使用"清除会话"功能。

### Q: 货币修改后不生效
A:
- 萌魂/钻石/萌水晶：重新登录游戏即可
- 金币：需要在游戏中从云端加载存档

### Q: 邮件领取失败
A: 检查邮件类型是否正确。不支持 `Ruby` 类型（客户端枚举中没有）。

### Q: 公告不显示或卡住
A: 确保公告有有效的图片 URL。可以使用 `clear-notices` 命令清除所有公告。

## License

仅供学习和研究使用。
