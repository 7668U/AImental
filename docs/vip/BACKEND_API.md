# VIP 后端 API 合同

更新日期：2026-07-13

基础路径：

```text
/api/v1/vip
```

除商品目录外，所有接口都需要登录 Token，并要求用户已同意当前隐私政策。

## 1. 商品与功能代码

功能代码：

```text
tree_hole
community
mood_analysis
assessment_analysis
```

会员商品：

```text
vip_light
vip_knowing
vip_companion
```

加量包商品：

```text
addon_tree_500
addon_community_500
addon_mood_50
addon_assessment_50
```

价格、名称、额度和有效期全部以后端商品目录为准，前端不得硬编码为支付依据。

## 2. 商品目录

```http
GET /api/v1/vip/catalog
```

无需登录。返回：

- 当前价格阶段。
- 四项功能定义。
- 免费月度额度。
- 三档会员商品。
- 四种加量包。
- 本地模拟支付是否可用。

## 3. 当前权益

```http
GET /api/v1/vip/me
Authorization: Bearer <token>
```

核心响应结构：

```json
{
  "user_type": "free",
  "membership": null,
  "entitlements": {
    "tree_hole": {
      "feature": "tree_hole",
      "name": "心情树洞",
      "unit": "次",
      "total": 100,
      "remaining": 100,
      "sources": [
        {
          "bucket_id": "uuid",
          "source_type": "free",
          "source_ref": "free:user:2026-07:tree_hole",
          "total": 100,
          "remaining": 100,
          "valid_from": 0,
          "expires_at": 0
        }
      ]
    }
  },
  "server_time": 0
}
```

`source_type` 可能为：

```text
free
membership
addon
```

前端应分别展示不同来源和到期时间，不要只保存合并后的总数。

## 4. 创建订单

```http
POST /api/v1/vip/orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "product_code": "addon_community_500"
}
```

响应：

```json
{
  "order": {
    "id": "uuid",
    "product_code": "addon_community_500",
    "product_type": "addon",
    "amount_fen": 299,
    "status": "pending",
    "product_snapshot": {},
    "payment_provider": "wechat",
    "created_at": 0
  },
  "payment": {
    "provider": "wechat",
    "mode": "wechat_not_configured",
    "payload": null,
    "mock_pay_endpoint": null
  }
}
```

正式接入微信支付后，`payment.payload` 返回小程序调起支付所需参数。前端订单页面不需要改变数据结构。

## 5. 订单查询

```http
GET /api/v1/vip/orders
GET /api/v1/vip/orders/{order_id}
```

订单状态：

```text
pending
paid
fulfillment_pending
fulfilled
closed
refunded
```

前端只有在后端订单状态为 `fulfilled` 时，才能展示权益已到账。

## 6. 本地模拟支付

后端环境变量：

```env
ENABLE_VIP_MOCK_PAYMENT=true
```

仅限本地开发环境：

```http
POST /api/v1/vip/orders/{order_id}/mock-pay
Authorization: Bearer <token>
```

生产环境必须保持关闭。

## 7. 权益与购买记录

```http
GET /api/v1/vip/records
```

返回额度流水和购买订单，用于“额度明细”和“购买记录”两个页面。

额度事件包括：

```text
grant
reserve
confirm
release
expire
```

## 8. AI 接口扣额

已接入：

| 功能 | 接口 | 扣额代码 |
| --- | --- | --- |
| 心情树洞 | `POST /api/v1/chats/{chat_id}/respond` | `tree_hole` |
| 心灵社区 | `POST /api/v1/community/chats/{character_id}/messages` | `community` |
| 单项心情分析 | `GET /api/v1/report/ai/...` | `mood_analysis` |
| 历史测评综合分析 | `POST /api/v1/history-analysis/synthesize` | `assessment_analysis` |

社区旧版 `GET /api/v1/community/chats/status` 接口仍保留
`daily_count/limit` 字段以兼容现有前端，但 `limit` 已映射为当前社区权益可用量，
不再使用固定每天 50 条作为套餐限制。Redis 计数只用于异常请求安全阈值。

前端调用 AI 接口时建议提供：

```http
X-Request-ID: <每次用户操作唯一的 UUID>
```

后端会将其与用户和功能组合成幂等键。相同请求不能重复预占和扣除额度。

扣额顺序：

1. 校验登录、输入和额度。
2. 预占 1 次。
3. 调用模型并保存结果。
4. 成功后确认扣除。
5. 失败、安全拦截或保存失败时释放额度。

缓存命中的分析报告不会进入预占流程。

## 9. 常见错误

额度不足：

```json
{
  "detail": {
    "code": "quota_exhausted",
    "message": "当前功能额度已用完。",
    "feature": "community",
    "vip_state": {}
  }
}
```

HTTP 状态为 `402`。前端应保留用户当前输入，并展示升级或对应加量包入口。

其他错误代码：

```text
input_empty
input_too_large
duplicate_request
invalid_product
membership_change_not_supported
addon_purchase_limit
mock_payment_disabled
model_generation_failed
```

## 10. 当前边界

- 免费额度按自然月自动创建和重置。
- 会员额度按购买周期创建，不结转。
- 同套餐续费会延长会员到期时间。
- 不同会员等级之间的升级和降级暂未开放。
- 加量包购买后 90 天有效，免费用户也可以购买和使用。
- 同一加量包近 30 天最多购买 5 个。
- 正式微信支付下单参数、回调验签和退款尚未接入。
