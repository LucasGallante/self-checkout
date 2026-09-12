# Self-Checkout Snack Bar — Product Spec

## Summary

A self-service ordering kiosk for a snack bar. A customer walks up to a
counter-mounted tablet, browses the menu, builds an order, pays, and walks
away — no cashier, no one to ask for help. The system has two parts: a web
client (React) that runs on the tablet — a customer-facing menu/checkout flow
plus an admin route for editing the menu and reviewing orders — and a web API
(Python) that serves the menu and accepts orders into a PostgreSQL database.
Payment is not processed for real; submitting an order only persists it.

## The Problem

A snack bar's throughput is bottlenecked by a cashier taking one order at a
time. Lines form at peak, and every order needs a human to relay it to the
kitchen. This service removes that human from the critical path:

- **No queue.** Any number of customers can build an order at once; each
  tablet is a register.
- **No transcription errors.** The customer picks exactly what they want; the
  order that reaches the kitchen is the one they built, not a re-typed one.
- **Always-on ordering.** The kiosk never takes a break, gets busy with a
  side task, or mishears "two, no, three."

The hard part is not the happy path — it's that the person using it is alone,
in a hurry, and will do things we didn't plan for.

## Persona

**The solo customer in a hurry.**

They are standing at the screen alone. They have a limited window (a lunch
break, a meeting in ten minutes) and no one to ask. They are not "a user of
our software" — they are a hungry person who wants a sandwich.

That means:

- They will not read instructions. They will tap the screen and expect it to
  respond correctly.
- They will tap the wrong thing and want to fix it. Often.
- They will add too many of something, then try to change it.
- They will start an order, get distracted or change their mind, and walk
  away mid-flow.
- They will press "Submit" twice because it didn't look like it worked.
- They will fat-finger quantity, price, and payment fields.

We design for the unplanned, not against it: undo before confirm, clear
confirmation after, no dead ends, no state that silently disappears.

## User Journey

1. **Arrive.** Customer walks up. The tablet shows a "Start" screen — the
   menu is visible, but ordering begins when they tap "Start". This tap is
   when we generate the idempotency key and mark the session start, which is
   what the completion/abandonment metrics measure against.
2. **Browse.** They scroll categories (e.g. Snacks, Drinks, Sweets), see
   item name, description, price, and availability. Out-of-stock items are
   visible but disabled with a clear "sold out" label, never silently missing.
3. **Build the order.** They tap an item to add it. A running order summary
   (items + total) is always visible — they never wonder "what did I pick
   again?". They can change quantities, remove items, or clear the whole
   order from that summary. A **Reset** button is always visible: it clears
   the whole cart and returns to the Start screen, so a customer can start
   over at any point.
4. **Review.** They tap "Checkout" and see the full order with quantities,
   line totals, the total, and any selected options (e.g. almond milk). This
   is their one chance to catch a fat-fingered quantity before paying.
5. **Pay.** They enter payment details on a form that feels like payment but
   is not processed for real. Submitting simulates success.
6. **Submit & confirm.** One tap submits. The screen confirms with a clear
   order number ("Order #4 — the kitchen is on it") and a total. No
   ambiguity about whether it went through.
7. **Walk away.** The screen resets to the menu for the next customer after
   a short confirmation, so the next person isn't looking at the previous
   customer's order.

### Edge cases the journey must survive

- **Mid-order abandonment.** An idle order must not block the next customer.
  A **Reset** button clears the cart and returns to the Start screen at any
  time — the next customer never has to remove the previous one's items by
  hand. On top of that, the tablet auto-resets to the Start screen after a
  timeout; an abandoned order is simply dropped (never persisted, never
  charged).
- **Double submit.** A tap on "Submit" that is retried must not create two
  orders. One order per submission attempt (idempotency).
- **Tapping an unavailable item.** Disabled before it can be added, or the
  order is corrected server-side and the customer told clearly.
- **Network hiccup.** If the API is unreachable, the client shows it plainly
  ("can't reach the kitchen") and lets them retry, never a frozen screen.

## Business Metrics

These are what we'd instrument to know the kiosk is working:

| Metric | Why it matters |
| --- | --- |
| **Order completion rate** (started → submitted) | The core measure of the flow working. Abandonment is money walked out the door. |
| **Time to submit** (arrival → order placed) | Throughput per tablet; a slow flow is a hidden line. |
| **Abandonment rate at each step** | Tells us where in the journey people give up (review? payment?). |
| **Items per order / average order value** | Revenue per visit; good for upsell/cross-sell later. |
| **Failed or errored submissions** | Reliability; every error is a customer who may have paid or may walk away confused. |
| **Double-submissions prevented** | Idempotency working; each one is a customer who would otherwise be double-charged. |
| **"Sold out" incidents / stale menu served** | How fresh the menu is; a customer told "sold out" after ordering is a lost order. |

## Business Impact

- **Throughput** scales with tablets, not headcount: one staff member can
  oversee many kiosks instead of running one register.
- **Lower labor cost** at the counter; staff time shifts to food prep where
  it adds more value.
- **Higher order accuracy** (orders come from the customer, not a relay),
  reducing remakes and waste.
- **Shorter perceived wait**: the customer is *doing* something the moment
  they arrive rather than waiting to be served.
- **Consistent upselling**: every order is offered the same items with
  correct prices, no cashier variance.

The main risk to note: a bad kiosk (slow, confusing, error-prone) is worse
than no kiosk — it frustrates a captive customer and loses the sale entirely.
This is why the spec treats the unplanned tap as a first-class case, not an
afterthought.

## Technical Architecture

### Components

- **Client (React)** — a single-page app running on the counter tablet.
  Fetches the menu, builds the order locally, submits to the API. Two routes:
  - **Customer route** (default) — menu browsing, order building, checkout.
  - **Admin route** (`/admin`) — edit the menu (add/edit/remove items, set
    price, set stock, reorder categories) and see placed orders.
    No login — this is a demo, simplicity over security.
  Built with **Vite** for fast dev + build.
- **API (Python)** — a web service that exposes the menu and accepts orders,
  plus the admin endpoints. **FastAPI** (over Flask/Django): async, Pydantic
  request validation for free, auto-generated OpenAPI docs.
- **Database (PostgreSQL)** — stores the menu (categories, items, prices,
  stock) and submitted orders.
- **Docker / docker-compose** — run PostgreSQL (and the API) locally without
  installing anything, and to match prod parity.

### API surface

Customer-facing:

- `GET /menu` → categories → items (id, name, description, image_url, price,
  stock, and their
  `option_groups: [{ id, name, options: [{ id, name, price_delta, image_url }] }]`).
  Availability is derived: an item is "available" when `stock > 0`; the client
  renders `stock == 0` items as sold out.
- `POST /checkout` → creates and persists an order.
  - Request: `{ idempotency_key, items: [{ item_id, quantity, options: [option_id, ...] }] }`.
  - Response: `{ order_number, total }` (and a `201` on create, or the
    existing order's details when the key is a repeat).
  - Accepts an **idempotency key** so a retried submit doesn't create a
    duplicate order.
  - Server re-validates every line item against the current menu (price,
    stock, and that each `option_id` actually belongs to one of the item's
    option groups), and returns the authoritative total — the client's total
    is never trusted. The unit price is `item.price + Σ option.price_delta`.
    Creating the order decrements each item's stock atomically (in the same
    transaction), so two customers can't oversell the last one.

Admin (menu management):

- `GET /menu` → the full menu (same shape as the customer endpoint, including
  stock), so the admin can see and edit every category and item.
- `POST /menu/categories` · `PATCH /menu/categories/{id}` · `DELETE /menu/categories/{id}`
- `POST /menu/items` · `PATCH /menu/items/{id}` · `DELETE /menu/items/{id}`
- `POST /menu/option-groups` · `PATCH /menu/option-groups/{id}` · `DELETE /menu/option-groups/{id}`
- `POST /menu/option-groups/{id}/options` · `PATCH /menu/options/{id}` · `DELETE /menu/options/{id}`
  - Option groups are attached to items (an item offers zero or more groups);
    attaching/detaching a group is done via the item edit.
  - Editing price or stock (or an option's `price_delta`) takes effect on the
    next customer's menu fetch; it never rewrites already-persisted orders
    (those snapshot their own price and options at order time).
  - Deleting a category that still has items (or an item/option referenced by
    past orders) is rejected with a `409` — nothing referenced is ever
    deleted; set its stock to 0 instead.

Admin (orders):

- `GET /orders` → list of placed orders (newest first).
- `GET /orders/{id}` → full detail of one order (items, quantities, totals).

### Data model

- `category` — id, name, description, sort_order (integer; the priority it's
  shown at on the display, lower first).
- `item` — id, category_id (FK → category), name, description, image_url
  (nullable), price (integer cents), stock (integer; 0 = sold out).
- `option_group` — id, name (e.g. "Milk"), sort_order (integer; global
  display priority, applied consistently wherever the group appears).
- `item_option_group` — item_id (FK → item), option_group_id (FK →
  option_group); which groups an item offers (many-to-many).
- `option` — id, option_group_id (FK → option_group), name (e.g. "Almond
  milk"), image_url (nullable), price_delta (integer cents; non-negative
  upcharge added to the item price, 0 = free).
- `order` — id, number (the count of orders placed today, human-facing),
  status, created_at, total.
- `order_item` — order_id (FK → order), item_id (FK → item), item_name
  (snapshot), quantity, unit_price (integer cents; the final per-unit price =
  item price + selected option deltas). `item_name` and `unit_price` are
  snapshotted at order time so later menu edits don't rewrite history.
- `order_item_option` — order_item_id (FK → order_item), option_id (FK →
  option), option_name (snapshot), price_delta (snapshot); records which
  options the customer chose on that line.

Prices stored as integer cents; no floats for money. `order.total` = Σ
(`order_item.quantity × unit_price`).

### Order flow & idempotency

The client generates an idempotency key (a UUID) when the customer taps
**Start** — the beginning of an ordering session — and sends it with
`POST /checkout`. A new session (after Reset or auto-timeout) gets a fresh
key. The API stores the key against the order; a repeat with the same key
returns the *existing* order instead of creating a second one. This makes
double-taps and network retries safe.

An order's human-facing `number` is a per-day counter: the first order after
midnight is #1. It's assigned atomically within the checkout transaction
(count of today's orders + 1), so the idempotency key prevents duplicates and
the counter gives a friendly sequential number for the day.

Order status is a two-value enum — `PLACED` and `COMPLETED`. Every order is
created as `PLACED`; `COMPLETED` is reserved for a future fulfillment flow.
There is no endpoint to change status for now. The admin app lists orders
newest first.

### What we are deliberately not building (yet)

- No auth/users/accounts — the admin route has no login; it's a demo,
  simplicity over security.
- No real payment processing — simulated success only.
- No real-time kitchen display/printing — out of scope for this spec.
