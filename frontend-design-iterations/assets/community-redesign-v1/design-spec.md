# 心灵社区视觉方案 V1

## 设计方向

- 气质：温柔、成熟、有人情味，避免幼态化和过度医疗化。
- 主色：暖橙 `#FF6B16`，用于主操作、未读提醒和关系升温。
- 基底：奶油白 `#FFF7EF`、纸张白 `#FFFDFA`。
- 辅色：鼠尾草绿 `#78906F`、雾蓝 `#8CA6AD`、柔玫瑰 `#D88F7D`。
- 正文：深褐黑 `#352D28`；次级文字 `#736963`；弱提示 `#A49B95`。

## 字体层级

- 页面主标题：48-52rpx，800。
- 区块标题：34-36rpx，800。
- 角色姓名：31-34rpx，800。
- 正文与聊天内容：27-29rpx，行高 1.55-1.65。
- 辅助信息：19-23rpx。

## 组件规范

- 页面左右边距：24-32rpx。
- 重复内容卡：16rpx 圆角，轻描边与低浓度暖褐阴影。
- 主按钮：胶囊形，暖橙实色；禁用态使用低饱和浅橙。
- 标签：胶囊形，使用橙、绿、蓝、玫瑰的低饱和浅底。
- 资料卡：16rpx 圆角，顶部暖橙浅底，内容区保持纸张白。

## 页面拆解

### 社区主界面

- 顶部使用会客厅氛围插画，左侧保留标题与说明的安全区域。
- 首屏突出“有人愿意听你说”，下方进入角色列表。
- 角色条目展示头像、未读、消息摘要、最近出现时间、关系阶段和温度。
- 空状态使用独立对话插画，错误与加载状态保持同一视觉体系。

### 聊天界面

- 导航栏同时承载角色身份、当前状态和好感度。
- 关系温度独立成一条轻量信息带，不挤进消息气泡。
- AI 气泡为纸张白，用户气泡为柔橙色。
- 底部输入区包含额度状态、表情入口、文本输入和发送按钮。
- 空会话使用独立插画，提醒用户一句真诚问候即可开始。

### 资料卡

- 顶部展示头像、身份、格言和关系温度。
- 标签使用多色低饱和色板，避免页面被单一橙色占满。
- 资料字段按“标签 + 详细内容”纵向排列，长文本可滚动。
- 时间回溯位于固定底部，使用克制的危险操作样式。

## 交付文件

### 高保真设计稿

- `mockups/community-main-mockup.png`
- `mockups/community-chat-mockup.png`
- `mockups/community-profile-mockup.png`
- `mockups/community-mockups-contact-sheet.png`

### 单图素材

- `assets/community-hero-atmosphere.png`：社区首页顶部会客厅氛围图。
- `assets/community-empty-conversation.png`：社区或聊天空状态插画。
- `assets/community-paper-texture.png`：聊天页低对比纸张背景。
- `assets/community-soft-decoration.png`：可选的透明弧线、叶片与星点装饰。

### 源文件

- `source/mockups.html`：三张设计稿的可编辑 HTML 源。
- `source/generate_assets.py`：单图素材生成脚本。

## 已集成路径

正式页面使用的素材已复制到：

`AImental_frontend/images/community-redesign/`

其中两张不透明背景在正式目录中压缩为
`community-hero-atmosphere.jpg` 和 `community-paper-texture.jpg`，
当前实现已接入首页氛围图、聊天纸张纹理和空会话插画。
