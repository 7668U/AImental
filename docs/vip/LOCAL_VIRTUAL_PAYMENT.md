# VIP 本地虚拟支付开发说明

## 当前模式

本地开发默认开启：

```env
ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT=true
```

未配置真实微信虚拟支付参数时，`POST /api/v1/vip/orders` 会返回：

```json
{
  "payment": {
    "provider": "wechat",
    "mode": "local_virtual_mock",
    "payload": {
      "signData": "...",
      "paySig": "...",
      "signature": "...",
      "mode": "short_series_goods"
    },
    "local_confirm_endpoint": "/api/v1/vip/orders/{order_id}/virtual-pay/local-confirm"
  }
}
```

前端会弹出本地虚拟支付确认框。确认后调用 `local_confirm_endpoint`，后端把订单标记为已支付并发放会员或加量包权益。

## 真实微信虚拟支付参数

后续需要连微信沙箱或线上虚拟支付时，补齐：

```env
WECHAT_VIRTUAL_PAY_OFFER_ID=
# env=0 时使用现网 AppKey
WECHAT_VIRTUAL_PAY_APP_KEY=
# env=1 时使用沙箱 AppKey
WECHAT_VIRTUAL_PAY_SANDBOX_APP_KEY=
WECHAT_VIRTUAL_PAY_ENV=1
WECHAT_VIRTUAL_PAY_PRODUCT_IDS={"vip_light":"微信后台道具ID"}
```

`WECHAT_VIRTUAL_PAY_PRODUCT_IDS` 要把后端商品码映射到微信虚拟支付后台发布的 `productId`。未配置映射时，默认使用后端商品码本身。

## 上线前必须处理

- 将 `ENABLE_VIP_LOCAL_VIRTUAL_PAYMENT=false`。
- 配置 `WECHAT_VIRTUAL_PAY_CALLBACK_TOKEN`，并在微信小程序后台将消息推送 URL 配置为：
  `https://api.feelyourself.cn/api/v1/vip/wechat/callback`
- 后端已接入 `xpay_goods_deliver_notify` 发货通知，也会在读取 `/vip/me` 和支付成功后主动调用微信 `query_order` 做补偿核验。
- 真实支付成功页必须以后端订单状态 `fulfilled` 为准。
- 道具价格、`productId`、订单号和发货通知都要做服务端校验。

微信前端接口参考：`wx.requestVirtualPayment`，当前使用 `short_series_goods` 道具直购模式。
