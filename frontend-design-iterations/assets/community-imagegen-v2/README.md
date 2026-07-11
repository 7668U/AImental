# 心灵社区 Image-gen V2 素材

本目录保存本轮由内置 `image_gen` 直接生成的高保真设计稿、背景原图、
图标总表和拆分后的正式素材。

## 原图

- `originals/community-main-design.png`
  - 心灵社区首页高保真设计稿。
- `originals/community-hero-background.png`
  - 无文字、无控件的阳光会客厅背景原图。
- `originals/community-ui-icons-green-screen.png`
  - 九宫格图标绿幕原图。
- `originals/community-ui-icons-transparent.png`
  - 去除绿幕后保留透明通道的九宫格图标总表。

## 正式素材

`icons/` 中包含小程序直接使用的压缩背景和九枚透明 PNG：

- `community-hero-sunroom.jpg`
- `welcome-plant.png`
- `coffee-sprout.png`
- `affinity-heart.png`
- `leaf-sparkle.png`
- `tab-heart-sprout.png`
- `tab-assessment.png`
- `tab-community.png`
- `tab-journal.png`
- `tab-profile.png`

前端实际引用路径为：

`AImental_frontend/images/community-premium/`

## 生成提示词摘要

背景图：以高保真设计稿为构图参考，生成成熟、温暖的晨光阅读室；
左侧保留标题负空间，右侧集中扶手椅、鼠尾草绿靠垫、橙色毯子、
木桌、热饮、花瓶、窗户和书架；禁止文字、按钮、人物和设备边框。

图标总表：生成统一暖橙、象牙白、鼠尾草绿和雾蓝色系的 3x3 图标板，
包括植物徽章、发芽咖啡杯、关系心形、五枚功能线性图标和叶片装饰；
使用纯绿色背景，之后通过本地 chroma-key 工具去除背景并逐格裁切。
