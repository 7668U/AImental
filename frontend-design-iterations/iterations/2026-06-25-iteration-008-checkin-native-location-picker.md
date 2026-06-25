# Iteration 008 - Checkin Native Location Picker

日期：2026-06-25

## 背景

用户反馈每日打卡中自研定位页底部信息过于简陋，只显示“地图中心位置”一类兜底内容，不能像微信原生选择位置一样弹出可选择的地点名称列表。

## 调整

修改 `AImental_frontend/pkgDailyCheckin/record.js`：

- 将“写下今天的小记忆”中的定位 chip 点击行为改回 `wx.chooseLocation`。
- 原生位置页返回后，优先显示 `name`，其次使用 `address`。
- 如果用户已经选择过位置，再次打开时将已有经纬度传给 `wx.chooseLocation` 作为初始位置。
- 历史只读记录仍不允许重新选择位置。

修改 `AImental_frontend/app.json`：

- 从 `pkgDailyCheckin` 子包页面注册中移除自定义 `location-picker`。
- 将 `requiredPrivateInfos` 保持为 `chooseLocation`。

清理文件：

- 删除 `AImental_frontend/pkgDailyCheckin/location-picker.js`。
- 删除 `AImental_frontend/pkgDailyCheckin/location-picker.wxml`。
- 删除 `AImental_frontend/pkgDailyCheckin/location-picker.wxss`。
- 删除 `AImental_frontend/pkgDailyCheckin/location-picker.json`。

## 结果

- 用户点击定位 chip 后进入微信原生地点选择页，可看到原生地点候选列表并选择具体地点名称。
- 不再出现“地图中心位置”或“当前地图中心点”这类兜底文案。
- 当前地点仍只保存在前端页面状态；后端尚未新增 location 字段，暂不随打卡接口提交。

## 验证

- `node --check AImental_frontend/pkgDailyCheckin/record.js`：通过。
- `node -e "JSON.parse(require('fs').readFileSync('AImental_frontend/app.json','utf8'))"`：通过。
- 前端主流程中无 `地图中心位置`、`当前地图中心点`、`getLocation`、`location-picker` 残留。
