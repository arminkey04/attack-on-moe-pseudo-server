# Attack on Moe - C/S 交互 API 完整文档

## 概述

本文档详细记录了 Attack on Moe 游戏客户端与服务端之间的所有网络交互 API。

### 服务架构

游戏使用以下服务：

| 服务类型 | 描述 |
|---------|------|
| Parse Server | 主要后端服务，处理用户认证、数据存储等 |
| 优惠券服务 | 独立的优惠券兑换服务 |
| CDN 资源服务器 | 游戏资源包下载服务 |

### 服务器地址配置

**Parse Server:**
| 环境 | URL | Application ID |
|------|-----|----------------|
| 本地开发 | `http://192.168.1.134:1337/parse/` | `aom-parse-local` |
| 开发环境 | `http://aom-parse-dev.herokuapp.com/parse/` | `game.ignite.aom.dev` |
| 生产环境 | `http://server.aom.ignite-ga.me/parse/` | `game.ignite.aom.prd` |

**其他服务:**
| 服务 | URL |
|------|-----|
| 优惠券服务 | `https://aom-coupon.herokuapp.com/` |
| CDN 资源服务器 | `http://aomcdn.ignite-ga.me/asset_bundle/AssetBundles/` |
| 备用 CDN | `https://s3-ap-southeast-1.amazonaws.com/attack-on-moe/asset_bundle/AssetBundles/` |

---

## 通用请求规范

### 通用请求头

所有 Parse Server API 请求需要包含以下请求头：

```
X-Parse-Application-Id: {applicationId}
Content-Type: application/json
```

登录后的请求还需要：
```
X-Parse-Session-Token: {sessionToken}
```

### Parse 数据类型

**Pointer 类型:**
```json
{
  "__type": "Pointer",
  "className": "_User",
  "objectId": "用户ID"
}
```

**Date 类型:**
```json
{
  "__type": "Date",
  "iso": "2024-01-01T12:00:00.000Z"
}
```

**日期字符串格式:** `yyyy-MM-ddTHH:mm:ss.fffZ`

---

## 一、用户认证 API

### 1.1 用户注册

**客户端调用:** `ParseUser.SignUpAsync()`

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/users`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
Content-Type: application/json
```

**请求体:**
```json
{
  "username": "{随机生成的GUID}",
  "password": "{随机生成的GUID}",
  "googleUserId": "{可选，Google用户ID}",
  "email": "{可选，Google邮箱}"
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| username | string | 是 | 用户名，客户端自动生成GUID |
| password | string | 是 | 密码，客户端自动生成GUID |
| googleUserId | string | 否 | Google用户ID |
| email | string | 否 | 用户邮箱 |

**成功响应 (200):**
```json
{
  "objectId": "a1b2c3d4e5",
  "createdAt": "2024-01-01T12:00:00.000Z",
  "sessionToken": "r:abcdef123456"
}
```

| 字段 | 类型 | 描述 |
|------|------|------|
| objectId | string | 用户唯一ID (10位) |
| createdAt | string | 创建时间 |
| sessionToken | string | 会话令牌 |

**错误响应:**
```json
{
  "code": 202,
  "error": "Username already taken"
}
```

---

### 1.2 用户登录（邮箱密码）

登录流程分两步：先清除旧Session，再登录。

#### 步骤1：清除 Session Token

**客户端调用:** `ParseCloud.CallFunctionAsync<string>("clearSessionToken", params)`

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/functions/clearSessionToken`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
Content-Type: application/json
```

**请求体:**
```json
{
  "username": "{用户邮箱}",
  "password": "{密码}"
}
```

**成功响应 (200):**
```json
{
  "result": "success"
}
```

#### 步骤2：登录

**客户端调用:** `ParseUser.LogInAsync(username, password)`

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/login`

**GET 请求参数:**
```
?username={用户邮箱}&password={密码}
```

**POST 请求体:**
```json
{
  "username": "{用户邮箱}",
  "password": "{密码}"
}
```

**成功响应 (200):**
```json
{
  "objectId": "a1b2c3d4e5",
  "username": "user@example.com",
  "email": "user@example.com",
  "sessionToken": "r:abcdef123456",
  "createdAt": "2024-01-01T12:00:00.000Z",
  "updatedAt": "2024-01-02T12:00:00.000Z"
}
```

---

### 1.3 Google 登录

**客户端调用:** `ParseCloud.CallFunctionAsync<IDictionary<string, object>>("getUserSessionToken", params)`

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/functions/getUserSessionToken`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
Content-Type: application/json
```

**请求体:**
```json
{
  "authCode": "{Google OAuth授权码}"
}
```

**成功响应 (200):**
```json
{
  "result": {
    "sessionToken": "r:abcdef123456"
  }
}
```

**用户不存在时的错误响应 (400):**
```json
{
  "code": 101,
  "error": "{\"code\":101,\"googleId\":\"google_user_id\",\"email\":\"user@gmail.com\"}"
}
```

> 注意: 客户端收到用户不存在错误后，会自动调用注册接口创建新用户

---

### 1.4 使用 Session Token 登录

**客户端调用:** `ParseUser.BecomeAsync(sessionToken)`

**协议:** HTTP/HTTPS
**方法:** GET
**URL:** `/parse/users/me`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**成功响应 (200):**
```json
{
  "objectId": "a1b2c3d4e5",
  "username": "user@example.com",
  "sessionToken": "r:abcdef123456",
  "createdAt": "2024-01-01T12:00:00.000Z",
  "updatedAt": "2024-01-02T12:00:00.000Z"
}
```

---

### 1.5 关联 Google 账号

**客户端调用:** `ParseCloud.CallFunctionAsync<string>("linkGoogleID", params)`

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/functions/linkGoogleID`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "authCode": "{Google OAuth授权码}"
}
```

**成功响应 (200):**
```json
{
  "result": "success"
}
```

---

### 1.6 关联邮箱账号

**客户端调用:** `ParseUser.SaveAsync()`

**协议:** HTTP/HTTPS
**方法:** PUT
**URL:** `/parse/users/{objectId}`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "username": "{用户邮箱}",
  "password": "{密码}",
  "email": "{用户邮箱}"
}
```

**成功响应 (200):**
```json
{
  "updatedAt": "2024-01-02T12:00:00.000Z"
}
```

---

### 1.7 用户登出

**客户端调用:** `ParseUser.LogOutAsync()`

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/logout`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**成功响应 (200):**
```json
{}
```

---

## 二、服务器配置 API

### 2.1 获取服务器配置

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/config`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
```

**成功响应 (200):**
```json
{
  "params": {
    "Version_Android": "2.5.2",
    "Version_iOS": "2.5.0",
    "maintenanceMode": false,
    "maintenanceMessage": "",
    "serverVersion": "1.0.0"
  }
}
```

| 字段 | 类型 | 描述 |
|------|------|------|
| Version_Android | string | Android客户端最新版本号 |
| Version_iOS | string | iOS客户端最新版本号 |
| maintenanceMode | boolean | 是否维护模式 |
| maintenanceMessage | string | 维护消息 |
| serverVersion | string | 服务器版本 |

---

## 三、用户数据 API

### 3.1 查询用户摘要 (UserSummary)

**客户端调用:** `ParseQuery<UserSummary>.FirstOrDefaultAsync()`

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/UserSummary`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**查询参数:**
```
where={"user":{"__type":"Pointer","className":"_User","objectId":"{userId}"}}
```

**成功响应 (200):**
```json
{
  "results": [
    {
      "objectId": "b2c3d4e5f6",
      "user": {
        "__type": "Pointer",
        "className": "_User",
        "objectId": "a1b2c3d4e5"
      },
      "displayName": "玩家名称",
      "friendPoint": 100,
      "friendLimit": 10,
      "ruby": 500,
      "gem": 1000,
      "moecrystal": 250,
      "createdAt": "2024-01-01T12:00:00.000Z",
      "updatedAt": "2024-01-02T12:00:00.000Z"
    }
  ]
}
```

**UserSummary 字段说明:**

| 字段 | 类型 | 描述 |
|------|------|------|
| objectId | string | 对象ID |
| user | Pointer | 关联的用户 |
| displayName | string | 显示名称 |
| friendPoint | integer | 好友点数 |
| friendLimit | integer | 好友上限 |
| ruby | integer | 萌魂数量 |
| gem | integer | 宝石数量 |
| moecrystal | integer | 萌水晶数量 |
| createdAt | string | 创建时间 |
| updatedAt | string | 更新时间 |

---

### 3.2 创建用户摘要

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/classes/UserSummary`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "user": {
    "__type": "Pointer",
    "className": "_User",
    "objectId": "{userId}"
  },
  "displayName": "玩家名称",
  "friendPoint": 0,
  "friendLimit": 5,
  "ruby": 0,
  "gem": 0,
  "moecrystal": 0
}
```

**成功响应 (200):**
```json
{
  "objectId": "b2c3d4e5f6",
  "createdAt": "2024-01-01T12:00:00.000Z"
}
```

---

### 3.3 更新用户摘要

**协议:** HTTP/HTTPS
**方法:** PUT 或 POST (带 `_method: "PUT"`)
**URL:** `/parse/classes/UserSummary/{objectId}`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "displayName": "新名称",
  "friendPoint": 150,
  "friendLimit": 15
}
```

> 注意: 服务端保护了 ruby, gem, moecrystal 字段，客户端无法直接修改

**成功响应 (200):**
```json
{
  "updatedAt": "2024-01-02T12:00:00.000Z"
}
```

---

### 3.4 保存游戏数据 (GameData)

**客户端调用:** `ParseObject.SaveAsync()`

**协议:** HTTP/HTTPS
**方法:** POST (创建) 或 PUT (更新)
**URL:** `/parse/classes/GameData` 或 `/parse/classes/GameData/{objectId}`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "user": {
    "__type": "Pointer",
    "className": "_User",
    "objectId": "{userId}"
  },
  "data": "{SaveData的JSON字符串}"
}
```

**SaveData JSON 结构:**
```json
{
  "playerName": "玩家名称",
  "golds": 0.0,
  "diamonds": 0,
  "relics": 0,
  "stage": 1,
  "wave": 1,
  "tutorialCompleted": false,
  "avatarLevel": 1,
  "avatarSkillList": [],
  "heroList": [],
  "aliveHeroList": [],
  "heroReviveTimeList": {},
  "pp_ReviveTime": "",
  "heroPassiveList": [],
  "artifactOrderList": [],
  "artifactList": [],
  "moespiritList": [],
  "touchCredit": 0,
  "touchCredit_Max": 0,
  "lastTouch": 0.0,
  "creditRechargeTime": 0,
  "girlStatusList": [],
  "girlExpList": [],
  "girlReachedBreakLevelList": [],
  "achievementList": [],
  "pp_FBInvitedList": "",
  "inviteFriends": 0.0,
  "reachHighestStage": 0.0,
  "collectRelic": 0.0,
  "tap": 0.0,
  "collectGold": 0.0,
  "killMonster": 0.0,
  "ownArtifact": 0.0,
  "reachHeroDPS": 0.0,
  "killBoss": 0.0,
  "prestige": 0.0,
  "lostGoldFromPrestige": 0.0,
  "levelUpHeroTimes": 0.0,
  "openChest": 0.0,
  "getFairyPresent": 0.0,
  "useJumpAttack": 0.0,
  "getCriticalHit": 0.0,
  "firstPlayTime": 0.0,
  "playingDuration": 0.0,
  "currentTotalHeroLevel": 0.0,
  "currentTapChance": 0.0,
  "currentDPSMultiplier": 0.0,
  "currentCriticalHitMultiplier": 0.0,
  "currentTotalGoldMultiplier": 0.0,
  "lastPrestigeTime": 0.0,
  "appRated": false,
  "facebookLiked": false,
  "twitterFollowed": false,
  "noAdmob": false,
  "key001Purchased": false,
  "key002Purchased": false,
  "key003Purchased": false,
  "key004Purchased": false,
  "key005Purchased": false,
  "key006Purchased": false,
  "pvpGiftKey001Purchased": false,
  "pvpGiftKey002Purchased": false,
  "goldPackPurchased": false,
  "silverPackPurchased": false,
  "bronzePackPurchased": false
}
```

**SaveData 字段说明:**

| 字段 | 类型 | 描述 |
|------|------|------|
| playerName | string | 玩家名称 |
| golds | double | 金币数量 |
| diamonds | integer | 钻石数量 |
| relics | integer | 遗物数量 |
| stage | integer | 当前关卡 |
| wave | integer | 当前波次 |
| tutorialCompleted | boolean | 是否完成教程 |
| avatarLevel | integer | 头像等级 |
| avatarSkillList | int[] | 头像技能列表 |
| heroList | int[] | 英雄列表 |
| aliveHeroList | bool[] | 存活英雄列表 |
| heroReviveTimeList | dict | 英雄复活时间 |
| heroPassiveList | int[] | 英雄被动技能列表 |
| artifactOrderList | int[] | 神器顺序列表 |
| artifactList | int[] | 神器列表 |
| moespiritList | int[] | 萌灵列表 |
| touchCredit | integer | 触摸点数 |
| girlStatusList | int[] | 女孩状态列表 |
| girlExpList | int[] | 女孩经验列表 |
| achievementList | int[] | 成就列表 |
| prestige | double | 转生次数 |
| noAdmob | boolean | 是否去广告 |
| key001Purchased ~ key006Purchased | boolean | 钥匙购买状态 |

**成功响应 (200):**
```json
{
  "objectId": "c3d4e5f6g7",
  "createdAt": "2024-01-01T12:00:00.000Z"
}
```

或更新时：
```json
{
  "updatedAt": "2024-01-02T12:00:00.000Z"
}
```

---

### 3.5 加载游戏数据

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/GameData`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**查询参数:**
```
where={"user":{"__type":"Pointer","className":"_User","objectId":"{userId}"}}
&order=updatedAt
&limit=1
```

**成功响应 (200):**
```json
{
  "results": [
    {
      "objectId": "c3d4e5f6g7",
      "user": {
        "__type": "Pointer",
        "className": "_User",
        "objectId": "a1b2c3d4e5"
      },
      "data": "{SaveData的JSON字符串}",
      "createdAt": "2024-01-01T12:00:00.000Z",
      "updatedAt": "2024-01-02T12:00:00.000Z"
    }
  ]
}
```

---

## 四、好友系统 API

### 4.1 添加好友

**客户端调用:** `ParseCloud.CallFunctionAsync<FriendRelation>("addFriend", params)`

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/functions/addFriend`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "targetUserID": "目标用户的objectId"
}
```

**成功响应 (200):**
```json
{
  "result": {
    "objectId": "d4e5f6g7h8",
    "users": [
      {"__type": "Pointer", "className": "_User", "objectId": "用户1ID"},
      {"__type": "Pointer", "className": "_User", "objectId": "用户2ID"}
    ],
    "createdAt": "2024-01-01T12:00:00.000Z",
    "updatedAt": "2024-01-01T12:00:00.000Z"
  }
}
```

---

### 4.2 查询所有好友关系

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/FriendRelation`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**查询参数:**
```
where={"users":{"__type":"Pointer","className":"_User","objectId":"{userId}"}}
&order=createdAt
```

**成功响应 (200):**
```json
{
  "results": [
    {
      "objectId": "d4e5f6g7h8",
      "users": [
        {"__type": "Pointer", "className": "_User", "objectId": "用户1ID"},
        {"__type": "Pointer", "className": "_User", "objectId": "用户2ID"}
      ],
      "createdAt": "2024-01-01T12:00:00.000Z",
      "updatedAt": "2024-01-01T12:00:00.000Z"
    }
  ]
}
```

---

### 4.3 查询好友的用户摘要

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/UserSummary`

**查询参数:**
```
where={"user":{"$in":[
  {"__type":"Pointer","className":"_User","objectId":"好友1ID"},
  {"__type":"Pointer","className":"_User","objectId":"好友2ID"}
]}}
&order=createdAt
```

---

### 4.4 删除好友关系

**协议:** HTTP/HTTPS
**方法:** DELETE
**URL:** `/parse/classes/FriendRelation/{objectId}`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**成功响应 (200):**
```json
{}
```

---

## 五、PvP 挑战系统 API

### 5.1 查询每个好友的最新战斗记录

**客户端调用:** `ParseCloud.CallFunctionAsync<IList<BattleLog>>("findLatestBattleLogPerFriend", null)`

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/functions/findLatestBattleLogPerFriend`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:** 无参数或 `{}`

**成功响应 (200):**
```json
{
  "result": [
    {
      "objectId": "e5f6g7h8i9",
      "sender": {"__type": "Pointer", "className": "_User", "objectId": "发送者ID"},
      "receiver": {"__type": "Pointer", "className": "_User", "objectId": "接收者ID"},
      "senderScore": 12345,
      "receiverScore": 54321,
      "senderWin": false,
      "senderClaim": false,
      "receiverClaim": false,
      "expired": false,
      "receivedAt": {"__type": "Date", "iso": "2024-01-01T12:00:00.000Z"},
      "createdAt": "2024-01-01T12:00:00.000Z",
      "updatedAt": "2024-01-02T12:00:00.000Z"
    }
  ]
}
```

---

### 5.2 查询发送给特定好友的最新挑战

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/BattleLog`

**查询参数:**
```
where={
  "sender":{"__type":"Pointer","className":"_User","objectId":"{当前用户ID}"},
  "receiver":{"__type":"Pointer","className":"_User","objectId":"{好友ID}"}
}
&order=-createdAt
&limit=1
```

---

### 5.3 查询收到的所有挑战

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/BattleLog`

**查询参数:**
```
where={
  "receiver":{"__type":"Pointer","className":"_User","objectId":"{当前用户ID}"},
  "receiverClaim":false
}
&order=createdAt
```

---

### 5.4 发起挑战

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/classes/BattleLog`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "sender": {"__type": "Pointer", "className": "_User", "objectId": "{发送者ID}"},
  "receiver": {"__type": "Pointer", "className": "_User", "objectId": "{接收者ID}"},
  "senderScore": 12345,
  "receiverScore": 0,
  "senderWin": false,
  "receivedAt": {"__type": "Date", "iso": "0001-01-01T00:00:00.000Z"},
  "senderClaim": false,
  "receiverClaim": false,
  "expired": false
}
```

**BattleLog 字段说明:**

| 字段 | 类型 | 描述 |
|------|------|------|
| sender | Pointer | 发送者用户指针 |
| receiver | Pointer | 接收者用户指针 |
| senderScore | integer | 发送者分数 |
| receiverScore | integer | 接收者分数 |
| senderWin | boolean | 发送者是否获胜 |
| senderClaim | boolean | 发送者是否已领取奖励 |
| receiverClaim | boolean | 接收者是否已领取奖励 |
| expired | boolean | 挑战是否已过期 |
| receivedAt | Date | 接收时间 |

**成功响应 (200):**
```json
{
  "objectId": "e5f6g7h8i9",
  "createdAt": "2024-01-01T12:00:00.000Z"
}
```

---

### 5.5 批量发起挑战

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/parse/batch`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
Content-Type: application/json
```

**请求体:**
```json
{
  "requests": [
    {
      "method": "POST",
      "path": "/parse/classes/BattleLog",
      "body": {
        "sender": {"__type": "Pointer", "className": "_User", "objectId": "{发送者ID}"},
        "receiver": {"__type": "Pointer", "className": "_User", "objectId": "{接收者1ID}"},
        "senderScore": 12345,
        "receiverScore": 0,
        "senderWin": false,
        "senderClaim": false,
        "receiverClaim": false,
        "expired": false
      }
    },
    {
      "method": "POST",
      "path": "/parse/classes/BattleLog",
      "body": {
        "sender": {"__type": "Pointer", "className": "_User", "objectId": "{发送者ID}"},
        "receiver": {"__type": "Pointer", "className": "_User", "objectId": "{接收者2ID}"},
        "senderScore": 12345,
        "receiverScore": 0,
        "senderWin": false,
        "senderClaim": false,
        "receiverClaim": false,
        "expired": false
      }
    }
  ]
}
```

**成功响应 (200):**
```json
[
  {
    "success": {
      "objectId": "e5f6g7h8i9",
      "createdAt": "2024-01-01T12:00:00.000Z"
    }
  },
  {
    "success": {
      "objectId": "f6g7h8i9j0",
      "createdAt": "2024-01-01T12:00:00.000Z"
    }
  }
]
```

---

### 5.6 接受挑战（提交分数）

**协议:** HTTP/HTTPS
**方法:** PUT 或 POST (带 `_method: "PUT"`)
**URL:** `/parse/classes/BattleLog/{objectId}`

**请求体:**
```json
{
  "receivedAt": {"__type": "Date", "iso": "2024-01-01T12:00:00.000Z"},
  "receiverScore": 54321,
  "senderWin": true
}
```

> 注意: `senderWin` 根据分数比较结果设置，`receiverScore > senderScore` 时为 `false`

---

### 5.7 领取挑战奖励

**协议:** HTTP/HTTPS
**方法:** PUT 或 POST (带 `_method: "PUT"`)
**URL:** `/parse/classes/BattleLog/{objectId}`

**发送者领取:**
```json
{
  "senderClaim": true
}
```

**接收者领取:**
```json
{
  "receiverClaim": true
}
```

---

### 5.8 设置挑战过期

**协议:** HTTP/HTTPS
**方法:** PUT 或 POST (带 `_method: "PUT"`)
**URL:** `/parse/classes/BattleLog/{objectId}`

**请求体:**
```json
{
  "expired": true
}
```

---

### 5.9 删除战斗记录

**协议:** HTTP/HTTPS
**方法:** DELETE
**URL:** `/parse/classes/BattleLog/{objectId}`

**成功响应 (200):**
```json
{}
```

---

## 六、公告系统 API

### 6.1 查询所有公告

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/Notice`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
```

**成功响应 (200):**
```json
{
  "results": [
    {
      "objectId": "g7h8i9j0k1",
      "imageURL": "https://example.com/notice1.png",
      "order": 1,
      "text": {
        "en": "English announcement text",
        "zh": "中文公告文本",
        "ja": "日本語のお知らせ"
      },
      "url": "https://example.com/link",
      "createdAt": "2024-01-01T12:00:00.000Z",
      "updatedAt": "2024-01-02T12:00:00.000Z"
    }
  ]
}
```

**Notice 字段说明:**

| 字段 | 类型 | 描述 |
|------|------|------|
| objectId | string | 公告ID |
| imageURL | string | 公告图片URL |
| order | integer | 显示顺序 |
| text | object | 多语言文本 {en, zh, ja, ...} |
| url | string | 点击跳转URL |

---

## 七、掉落箱/邮箱系统 API

### 7.1 查询掉落箱物品

**协议:** HTTP/HTTPS
**方法:** GET 或 POST
**URL:** `/parse/classes/DropBox`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**查询参数:**
```
where={"user":{"__type":"Pointer","className":"_User","objectId":"{userId}"}}
```

**成功响应 (200):**
```json
{
  "results": [
    {
      "objectId": "h8i9j0k1l2",
      "user": {"__type": "Pointer", "className": "_User", "objectId": "用户ID"},
      "type": "Gems",
      "title": {
        "en": "Daily Reward",
        "zh": "每日奖励"
      },
      "value": "100",
      "msg": "Congratulations!",
      "createdAt": "2024-01-01T12:00:00.000Z",
      "updatedAt": "2024-01-01T12:00:00.000Z"
    }
  ]
}
```

**DropBox 字段说明:**

| 字段 | 类型 | 描述 |
|------|------|------|
| objectId | string | 物品ID |
| user | Pointer | 所属用户 |
| type | string | 物品类型 |
| title | object | 多语言标题 |
| value | string | 物品值/数量 |
| msg | string | 消息 |

**支持的物品类型 (DropBoxItemType):**

| 类型 | 描述 |
|------|------|
| Gold | 金币 |
| Gems | 宝石 |
| MoeCrystal | 萌水晶 |
| Ruby | 萌魂 |
| Moetifacts | 神器 |
| MoetanPackages | 角色包 |
| AdFree | 去广告特权 |

---

### 7.2 删除掉落箱物品（领取奖励后）

**协议:** HTTP/HTTPS
**方法:** DELETE 或 POST (带 `_method: "DELETE"`)
**URL:** `/parse/classes/DropBox/{objectId}`

**请求头:**
```
X-Parse-Application-Id: {applicationId}
X-Parse-Session-Token: {sessionToken}
```

**成功响应 (200):**
```json
{}
```

---

## 八、优惠券服务 API

### 8.1 兑换优惠券

**协议:** HTTPS
**方法:** POST
**URL:** `https://aom-coupon.herokuapp.com/api/redeemCoupon`

**Content-Type:** `application/x-www-form-urlencoded`

**请求体:**
```
coupon_code={优惠券码}&redeemed_by={玩家名称}
```

| 字段 | 类型 | 描述 |
|------|------|------|
| coupon_code | string | 优惠券码 |
| redeemed_by | string | 兑换者名称（玩家名） |

**成功响应 (200):**
```json
{
  "relics": 100,
  "gems": 50,
  "unlockAdFree": false
}
```

| 字段 | 类型 | 描述 |
|------|------|------|
| relics | integer | 获得的遗物数量 |
| gems | integer | 获得的宝石数量 |
| unlockAdFree | boolean | 是否解锁去广告 |

**失败响应 (400):**
```json
{
  "error": {
    "message": "Invalid coupon code"
  }
}
```

**可能的错误消息:**
- `Invalid coupon code` - 无效的优惠券码
- `Coupon is no longer active` - 优惠券已失效
- `Coupon has reached maximum redemptions` - 优惠券已达到最大兑换次数
- `You have already redeemed this coupon` - 您已经兑换过此优惠券

---

## 九、CDN 资源 API

### 9.1 下载资源包

**协议:** HTTP
**方法:** GET
**URL:** `http://aomcdn.ignite-ga.me/asset_bundle/AssetBundles/{platform}/{bundleName}`

**平台值:**
| 平台 | 值 |
|------|-----|
| Android | `Android` |
| iOS | `iOS` |
| Windows | `StandaloneWindows` |
| macOS | `StandaloneOSX` |

**示例:**
```
http://aomcdn.ignite-ga.me/asset_bundle/AssetBundles/Android/characters
```

**响应:** 二进制资源包文件

---

## 十、Parse Cloud Functions 汇总

| 函数名 | 描述 | 请求参数 | 返回类型 |
|--------|------|----------|----------|
| `clearSessionToken` | 清除用户的 Session Token | `{username, password}` | `{result: "success"}` |
| `getUserSessionToken` | 通过 Google 授权码获取 Session Token | `{authCode}` | `{result: {sessionToken}}` |
| `linkGoogleID` | 关联 Google 账号 | `{authCode}` | `{result: "success"}` |
| `addFriend` | 添加好友 | `{targetUserID}` | `{result: FriendRelation}` |
| `findLatestBattleLogPerFriend` | 查询每个好友的最新战斗记录 | 无 | `{result: BattleLog[]}` |

---

## 十一、Parse Classes 汇总

| Class 名称 | 描述 | 主要字段 |
|------------|------|----------|
| `_User` | 用户表 | `objectId`, `username`, `password`, `email`, `googleUserId`, `createdAt`, `updatedAt` |
| `UserSummary` | 用户摘要 | `objectId`, `user`, `displayName`, `friendPoint`, `friendLimit`, `ruby`, `gem`, `moecrystal` |
| `GameData` | 游戏存档 | `objectId`, `user`, `data` |
| `FriendRelation` | 好友关系 | `objectId`, `users` (数组包含两个用户指针) |
| `BattleLog` | PvP 战斗记录 | `objectId`, `sender`, `receiver`, `senderScore`, `receiverScore`, `senderWin`, `senderClaim`, `receiverClaim`, `expired`, `receivedAt` |
| `Notice` | 公告 | `objectId`, `imageURL`, `order`, `text`, `url` |
| `DropBox` | 掉落箱/邮箱 | `objectId`, `user`, `type`, `title`, `value`, `msg` |
| `Coupon` | 优惠券 (服务端) | `objectId`, `code`, `relics`, `gems`, `unlockAdFree`, `maxRedemptions`, `currentRedemptions`, `isActive`, `redeemedBy` |

---

## 十二、错误码

| 错误码 | 描述 |
|--------|------|
| 1 | 内部错误 / 不支持的操作 |
| 101 | 对象未找到 / 无效凭证 |
| 105 | 无效的指针 |
| 119 | 权限被拒绝 |
| 200 | 缺少用户名或密码 |
| 202 | 用户名已被占用 |
| 205 | 用户不存在 (UserNotFound) |
| 209 | 无效的 Session Token (InvalidSessionToken) |

---

## 十三、客户端代码位置参考

| 功能 | 客户端文件 |
|------|-----------|
| Parse 初始化 | `clientcs/Assembly-CSharp/Ignite/AOM/ExtraParseInitialization.cs` |
| 用户服务 | `clientcs/Assembly-CSharp/Ignite/AOM/UserService.cs` |
| 好友服务 | `clientcs/Assembly-CSharp/Ignite/AOM/FriendService.cs` |
| PvP 挑战服务 | `clientcs/Assembly-CSharp/Ignite/AOM/PvPChallengeService.cs` |
| 公告服务 | `clientcs/Assembly-CSharp/Ignite/AOM/NoticeService.cs` |
| 优惠券服务 | `clientcs/Assembly-CSharp/Ignite/AOM/AOMCouponService.cs` |
| 资源包加载 | `clientcs/Assembly-CSharp/Ignite/AOM/AssetBundleLoader.cs` |
| 云存档管理 | `clientcs/Assembly-CSharp/Ignite/AOM/CloudDataManager.cs` |
| 游戏存档数据 | `clientcs/Assembly-CSharp/Ignite/AOM/SaveData.cs` |

---

## 十四、服务端代码位置参考

| 功能 | 服务端文件 |
|------|-----------|
| 主入口 | `server/main.py` |
| 用户路由 | `server/routers/users.py` |
| 登录路由 | `server/routers/login.py` |
| Classes 路由 | `server/routers/classes.py` |
| Cloud Functions | `server/routers/functions.py` |
| 批量操作 | `server/routers/batch.py` |
| 优惠券服务 | `server/routers/coupon.py` |
| 配置服务 | `server/routers/config.py` |
| 用户模型 | `server/models/user.py` |
| 用户摘要模型 | `server/models/user_summary.py` |
| 游戏数据模型 | `server/models/game_data.py` |
| 好友关系模型 | `server/models/friend_relation.py` |
| 战斗记录模型 | `server/models/battle_log.py` |
| 公告模型 | `server/models/notice.py` |
| 掉落箱模型 | `server/models/drop_box.py` |
| 优惠券模型 | `server/models/coupon.py` |

---

## 十五、管理员 API (仅服务端)

### 15.1 创建优惠券

**协议:** HTTP/HTTPS
**方法:** POST
**URL:** `/api/admin/coupons`

**Content-Type:** `application/x-www-form-urlencoded`

**请求体:**
```
code={优惠券码}&relics={遗物数量}&gems={宝石数量}&unlock_ad_free={是否解锁去广告}&max_redemptions={最大兑换次数}
```

**成功响应 (200):**
```json
{
  "objectId": "i9j0k1l2m3",
  "code": "TESTCODE",
  "relics": 100,
  "gems": 50,
  "unlockAdFree": false,
  "maxRedemptions": 100,
  "currentRedemptions": 0,
  "isActive": true,
  "createdAt": "2024-01-01T12:00:00.000Z",
  "updatedAt": "2024-01-01T12:00:00.000Z"
}
```

---

### 15.2 列出所有优惠券

**协议:** HTTP/HTTPS
**方法:** GET
**URL:** `/api/admin/coupons`

**成功响应 (200):**
```json
{
  "results": [
    {
      "objectId": "i9j0k1l2m3",
      "code": "TESTCODE",
      "relics": 100,
      "gems": 50,
      "unlockAdFree": false,
      "maxRedemptions": 100,
      "currentRedemptions": 5,
      "isActive": true,
      "createdAt": "2024-01-01T12:00:00.000Z",
      "updatedAt": "2024-01-02T12:00:00.000Z"
    }
  ]
}
```

---

### 15.3 删除优惠券

**协议:** HTTP/HTTPS
**方法:** DELETE
**URL:** `/api/admin/coupons/{coupon_id}`

**成功响应 (200):**
```json
{
  "success": true
}
```
