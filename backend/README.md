# Tortobaza Backend

REST API for the Tortobaza cake shop. Public catalog, anonymous server-side cart, and guest checkout with mock payments. Staff manage cakes, **`Product.delivery_schedule_tier`** (earliest fulfilment dates per product — strictest across the cart wins), option groups, promo codes, pickup locations, and orders through Django admin.

## Stack

- Python 3.12, Poetry
- Django 5.2 + Django REST Framework 3.17
- SQLite (dev)
- `django-cors-headers`, `Pillow`

## Project layout

- `tortobaza/` — Django project (settings, root urls, wsgi/asgi).
- `catalog/` — `Category`, `Product`, `ProductImage`, `OptionGroup`, `Option`, `ProductOptionGroup`.
- `cart/` — `Cart`, `CartItem`, `CartItemOption` and `CartTokenMiddleware`.
- `orders/` — `Order`, `OrderItem`, `OrderItemOption`, `DeliveryAddress`, `PromoCode`, `PickupLocation`, plus checkout and auto-generated fulfilment schedules.

`OptionGroup`s are global and reusable: created once in admin (e.g. "Filling", "Size", "Sponge") and attached to products through `ProductOptionGroup`, which carries per-product `position` and an optional `is_required` override. Pricing for an item is `Product.base_price + Σ Option.price_delta` of the selected options. At order placement, item names, prices, and option labels are snapshotted onto `OrderItem` / `OrderItemOption` so historical orders survive catalog edits.

## Running

```bash
cd backend
poetry install
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
```

- Admin: `http://localhost:8000/admin/`
- Health: `GET http://localhost:8000/health/`
- API base: `http://localhost:8000/api/`
- Uploaded images (DEBUG only): `http://localhost:8000/media/...`

## Cart token

The cart is anonymous and identified by a UUID4 token. The token is set as the HttpOnly cookie `cart_token` on the first cart write and is also accepted via the `X-Cart-Token` request header (useful for cross-origin SPAs that can't rely on cookies). Tokens live for 30 days. No user authentication is required for any cart or order endpoint.

The middleware (`cart.middleware.CartTokenMiddleware`) attaches `request.cart` lazily; on `GET /api/cart/` an empty cart is created automatically and the cookie is set in the response.

## API

All endpoints live under `/api/`. Catalog endpoints are public read-only. Cart and order endpoints rely on the cart token (cookie or header).

### Catalog

#### `GET /api/categories/`

Returns all active categories ordered by `position`.

```json
[
  { "id": 1, "slug": "simple-cake", "name": "Simple cake", "position": 0 }
]
```

#### `GET /api/products/`

Paginated product list. Query params:

- `category=<slug>` — filter by category slug.
- `search=<q>` — substring match on `name` and `description`.
- `page`, `page_size` — pagination (default `page_size=20`).

```json
{
  "count": 42,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "slug": "raspberry-dream",
      "name": "Raspberry Dream",
      "base_price": "1500.00",
      "primary_image": "http://localhost:8000/media/products/x.jpg",
      "category": { "id": 1, "slug": "simple-cake", "name": "Simple cake", "position": 0 }
    }
  ]
}
```

#### `GET /api/products/<slug>/`

Full product detail for the item page. `option_groups` is built from the product's `ProductOptionGroup` rows ordered by `position`; `is_required` resolves the per-product override or the group default.

```json
{
  "id": 1,
  "slug": "raspberry-dream",
  "name": "Raspberry Dream",
  "description": "...",
  "base_price": "1500.00",
  "category": { "id": 1, "slug": "simple-cake", "name": "Simple cake", "position": 0 },
  "images": [
    { "id": 10, "image": "http://localhost:8000/media/products/x.jpg", "alt": "", "position": 0 }
  ],
  "option_groups": [
    {
      "id": 3,
      "name": "Filling",
      "slug": "filling",
      "selection_type": "single",
      "is_required": true,
      "position": 0,
      "options": [
        { "id": 11, "name": "Raspberry", "price_delta": "0.00", "position": 0 },
        { "id": 12, "name": "Strawberry", "price_delta": "150.00", "position": 1 }
      ]
    }
  ]
}
```

### Cart

#### `GET /api/cart/`

Returns the current cart, creating an empty one (and setting `cart_token` cookie) if none exists.

```json
{
  "token": "8f1a...uuid",
  "items": [
    {
      "id": 7,
      "product": {
        "id": 1, "slug": "raspberry-dream", "name": "Raspberry Dream",
        "base_price": "1500.00", "primary_image": "http://..."
      },
      "quantity": 2,
      "comment": "С Днём Рождения!",
      "options": [
        { "id": 21, "name": "Raspberry", "price_delta": "0.00", "group_id": 3, "group_name": "Filling" }
      ],
      "unit_price": "1500.00",
      "line_total": "3000.00",
      "added_at": "2026-04-26T10:00:00Z"
    }
  ],
  "subtotal": "3000.00",
  "created_at": "...",
  "updated_at": "..."
}
```

#### `POST /api/cart/items/`

Add a line. Server validates that every selected option's group is linked to the product, that required groups have at least one selection, and that `single` groups have at most one. `unit_price` is computed server-side.

```json
{
  "product_id": 1,
  "quantity": 2,
  "option_ids": [11, 25],
  "comment": "С Днём Рождения!"
}
```

#### `PATCH /api/cart/items/<id>/`

Update `quantity`, `comment`, and/or `option_ids` for a cart line. Replacing `option_ids` re-runs the same validation.

#### `DELETE /api/cart/items/<id>/`

Remove a single line. Returns `204`.

#### `DELETE /api/cart/`

Empty the current cart. Returns `204`.

### Orders

#### `GET /api/pickup-locations/`

List active pickup locations.

```json
[
  { "id": 1, "name": "Main shop", "address": "ул. Пушкина 1", "lat": "...", "lng": "..." }
]
```

#### `GET /api/fulfillment-options/?type=delivery|pickup`

Returns bookable fulfilment choices for **the current cart**, using the strictest (`latest`) `delivery_schedule_tier` across all cart lines (`same_day`, `next_day`, `plus_2`, `plus_3`). All times use `Asia/Tbilisi`. Requires a non-empty cart; returns `400` if empty.

Slots are hourly (`11:00`–last start before `20:00` local); same-day hourly windows respect a `15:00` cut-off and “from now rounded up to the next hour”. When allowed, **`express_available`** is `true`: the client may place the order with `schedule_mode: "express"` (delivery within ~2 hours from server `now`). There are no per-slot capacity limits.

```json
{
  "timezone": "Asia/Tbilisi",
  "express_available": false,
  "dates": [
    {
      "date": "2026-05-22",
      "slots": [{ "start_time": "11:00", "end_time": "12:00" }]
    }
  ]
}
```

#### `POST /api/promo-codes/validate/`

Validate a promo code against the current cart and return discount/total preview.

Request:

```json
{ "code": "WELCOME10" }
```

Response:

```json
{
  "valid": true,
  "code": "WELCOME10",
  "discount_type": "percent",
  "discount_value": "10.00",
  "subtotal": "3000.00",
  "discount_total": "300.00",
  "total": "2700.00"
}
```

`400` is returned if the cart is empty, the code does not exist, is not active, is outside its validity window, has reached `max_uses`, or the order subtotal is below `min_order_amount`.

#### `POST /api/orders/preview/`

Returns the fully priced breakdown without creating an order — drives the order confirmation page.

```json
{
  "fulfillment_type": "delivery",
  "promo_code": "WELCOME10"
}
```

Response:

```json
{
  "fulfillment_type": "delivery",
  "subtotal": "3000.00",
  "discount_total": "300.00",
  "total": "2700.00",
  "promo_code": "WELCOME10"
}
```

#### `POST /api/orders/`

Place an order from the current cart. Inside one transaction: snapshots items + options into `OrderItem` / `OrderItemOption`, marks the cart `is_ordered=True`, increments `PromoCode.uses_count` if applicable, and returns the new order.

```json
{
  "fulfillment_type": "delivery",
  "address": {
    "street": "ул. Пушкина",
    "building": "10",
    "apartment": "5",
    "city": "Москва",
    "postal_code": "101000",
    "notes": "Домофон 5К"
  },
  "schedule_mode": "slot",
  "schedule_date": "2026-05-02",
  "schedule_start_time": "14:00",
  "schedule_end_time": "15:00",
  "payment_method": "card",
  "customer_name": "Иван Иванов",
  "customer_phone": "+7 999 123 45 67",
  "customer_email": "ivan@example.com",
  "comment": "Без надписи на торте",
  "promo_code": "WELCOME10"
}
```

For **express**, send `schedule_mode: "express"` and omit date/time fields. For **scheduled** fulfilment send `schedule_mode: "slot"` plus `schedule_date`, `schedule_start_time`, and `schedule_end_time` matching a slot from `GET /api/fulfillment-options/`.

For pickup orders pass `fulfillment_type: "pickup"` and `pickup_location_id` instead of `address`. Validation rejects an empty cart, missing address for delivery, missing pickup location for pickup, a schedule combination not allowed by the cart’s tiers, or an invalid promo code.

Response (`201`):

```json
{
  "number": "A1B2C3D4",
  "lookup_token": "uuid-...",
  "fulfillment_type": "delivery",
  "status": "pending",
  "payment_method": "card",
  "payment_status": "unpaid",
  "customer_name": "Иван Иванов",
  "customer_phone": "+7 999 123 45 67",
  "customer_email": "ivan@example.com",
  "comment": "Без надписи на торте",
  "pickup_location": null,
  "delivery_address": { "...": "..." },
  "timeslot_start": "2026-05-01T10:00:00Z",
  "timeslot_end": "2026-05-01T12:00:00Z",
  "subtotal": "3000.00",
  "discount_total": "300.00",
  "total": "2700.00",
  "items": [
    {
      "id": 1,
      "product_name": "Raspberry Dream",
      "unit_price": "1500.00",
      "quantity": 2,
      "comment": "С Днём Рождения!",
      "line_total": "3000.00",
      "options": [
        { "group_name": "Filling", "option_name": "Raspberry", "price_delta": "0.00" }
      ]
    }
  ],
  "created_at": "2026-04-26T10:00:00Z"
}
```

The client should store `lookup_token` to fetch order status later.

#### `GET /api/orders/<number>/?token=<lookup_token>`

Public order status lookup. The `token` query parameter is required and must match `Order.lookup_token` to prevent enumeration. Returns the same shape as the order creation response.

## Admin

`http://localhost:8000/admin/`

- **Catalog → Categories** — manage header filters.
- **Catalog → Option groups** — define reusable groups (Filling, Size, Sponge, ...) with their options inline. Created once and reused across products.
- **Catalog → Products** — set `category`, `name`, `description`, `base_price`, **`delivery_schedule_tier`** (controls earliest bookable fulfilment dates for orders containing this product — strictest tier wins across the cart). Inlines: `ProductImage` (carousel) and `ProductOptionGroup` (pick existing groups, set per-product `position`, optional `is_required` override).
- **Cart → Carts / Cart items** — for debugging anonymous carts.
- **Orders → Orders** — read-only snapshot inlines (`OrderItem`, `OrderItemOption`, `DeliveryAddress`); mutate `status` / `payment_status`.
- **Orders → Promo codes / Pickup locations** — operational data.
