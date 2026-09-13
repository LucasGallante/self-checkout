import { useEffect, useMemo, useRef, useState } from 'react';
import { api, formatPrice } from '../api.js';

const STEPS = ['start', 'browse', 'review', 'pay', 'done'];

export default function CustomerFlow() {
  const [step, setStep] = useState('start');
  const [menu, setMenu] = useState([]);
  const [error, setError] = useState(null);
  const [cart, setCart] = useState([]); // [{ item, quantity, options: [] }]
  const [sessionKey, setSessionKey] = useState(null);
  const [orderNumber, setOrderNumber] = useState(null);
  const [orderTotal, setOrderTotal] = useState(null);
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    api.getMenu().then(setMenu).catch((e) => setError(e.message));
  }, []);

  // auto-reset to Start after 60s idle
  useEffect(() => {
    if (step === 'start' || step === 'done') return;
    const t = setTimeout(() => reset(), 60000);
    return () => clearTimeout(t);
  }, [step, cart]);

  const total = useMemo(
    () => cart.reduce((sum, line) => {
      const unit = line.item.price + line.options.reduce((s, o) => s + o.price_delta, 0);
      return sum + unit * line.quantity;
    }, 0),
    [cart],
  );

  function reset() {
    setCart([]);
    setSessionKey(null);
    setOrderNumber(null);
    setOrderTotal(null);
    setStep('start');
  }

  function start() {
    setSessionKey(crypto.randomUUID());
    setStep('browse');
  }

  function addItem(item) {
    setCart((c) => {
      const existing = c.find((l) => l.item.id === item.id && !l.options.length);
      if (existing && item.option_groups.length === 0) {
        return c.map((l) => (l === existing ? { ...l, quantity: l.quantity + 1 } : l));
      }
      return [...c, { item, quantity: 1, options: [] }];
    });
  }

  function updateQuantity(index, delta) {
    setCart((c) =>
      c
        .map((l, i) => (i === index ? { ...l, quantity: l.quantity + delta } : l))
        .filter((l) => l.quantity > 0),
    );
  }

  function setLineOptions(index, option) {
    setCart((c) =>
      c.map((l, i) => {
        if (i !== index) return l;
        const has = l.options.some((o) => o.id === option.id);
        const next = has ? l.options.filter((o) => o.id !== option.id) : [...l.options, option];
        return { ...l, options: next };
      }),
    );
  }

  async function submit() {
    setPaying(true);
    setError(null);
    try {
      const payload = {
        idempotency_key: sessionKey,
        items: cart.map((l) => ({
          item_id: l.item.id,
          quantity: l.quantity,
          options: l.options.map((o) => o.id),
        })),
      };
      const res = await api.checkout(payload);
      setOrderNumber(res.order_number);
      setOrderTotal(res.total);
      setStep('done');
    } catch (e) {
      setError(e.message);
    } finally {
      setPaying(false);
    }
  }

  if (error && step !== 'pay') {
    return (
      <div className="full-screen center">
        <div className="card error-card">
          <h2>Can't reach the kitchen</h2>
          <p>{error}</p>
          <button className="btn primary" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="full-screen kiosk">
      {step === 'start' && (
        <div className="center">
          <div className="card start-card">
            <h1>Snack Bar</h1>
            <p className="subtitle">Order. Pay. Go.</p>
            <button className="btn primary huge" onClick={start}>
              Start
            </button>
          </div>
        </div>
      )}

      {step === 'browse' && (
        <Browse
          menu={menu}
          cart={cart}
          total={total}
          onAdd={addItem}
          onAddWithOptions={(item, options) =>
            setCart((c) => [...c, { item, quantity: 1, options }])
          }
          onSetOptions={setLineOptions}
          onQuantity={updateQuantity}
          onCheckout={() => setStep('review')}
          onReset={reset}
        />
      )}

      {step === 'review' && (
        <Review
          cart={cart}
          total={total}
          onBack={() => setStep('browse')}
          onContinue={() => setStep('pay')}
        />
      )}

      {step === 'pay' && (
        <Pay
          total={total}
          paying={paying}
          error={error}
          onBack={() => setStep('review')}
          onSubmit={submit}
        />
      )}

      {step === 'done' && (
        <div className="center">
          <div className="card done-card">
            <h1>Order #{orderNumber}</h1>
            <p className="subtitle">The kitchen is on it.</p>
            <p className="total">{formatPrice(orderTotal)}</p>
            <button className="btn primary huge" onClick={reset}>
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Browse({ menu, cart, total, onAdd, onAddWithOptions, onSetOptions, onQuantity, onCheckout, onReset }) {
  const [activeId, setActiveId] = useState(menu[0]?.id ?? null);
  const [modalItem, setModalItem] = useState(null);
  const sectionRefs = useRef({});

  function scrollTo(id) {
    sectionRefs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function onScroll(e) {
    const top = e.currentTarget.getBoundingClientRect().top;
    let current = menu[0]?.id;
    for (const c of menu) {
      const el = sectionRefs.current[c.id];
      if (el && el.getBoundingClientRect().top - top < 120) current = c.id;
    }
    setActiveId(current);
  }

  return (
    <div className="browse">
      <header className="topbar">
        <h1>Snack Bar</h1>
        <button className="btn ghost" onClick={onReset}>
          Reset
        </button>
      </header>

      <div className="browse-body">
        <nav className="category-nav">
          {menu.map((c) => (
            <button
              key={c.id}
              className={`category-tab ${activeId === c.id ? 'active' : ''}`}
              onClick={() => scrollTo(c.id)}
            >
              {c.name}
            </button>
          ))}
        </nav>

        <div className="menu-scroll" onScroll={onScroll}>
          {menu.map((category) => (
            <section
              key={category.id}
              className="category-section"
              ref={(el) => (sectionRefs.current[category.id] = el)}
            >
              <h2 className="category-title">{category.name}</h2>
              <div className="items-grid">
                {category.items.map((item) => {
                  const soldOut = item.stock <= 0;
                  return (
                    <button
                      key={item.id}
                      className="item-card"
                      disabled={soldOut}
                      onClick={() => (item.option_groups.length ? setModalItem(item) : onAdd(item))}
                    >
                      <div className="item-img">
                        {item.image_url ? (
                          <img src={item.image_url} alt={item.name} loading="lazy" />
                        ) : (
                          <div className="placeholder">{item.name[0]}</div>
                        )}
                        {soldOut && <span className="soldout-badge">Sold out</span>}
                      </div>
                      <div className="item-info">
                        <span className="item-name">{item.name}</span>
                        <span className="item-price">{formatPrice(item.price)}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        <Cart
          cart={cart}
          total={total}
          onSetOptions={onSetOptions}
          onQuantity={onQuantity}
          onCheckout={onCheckout}
          onReset={onReset}
        />
      </div>

      {modalItem && (
        <ItemModal
          item={modalItem}
          onClose={() => setModalItem(null)}
          onAdd={(options) => {
            onAddWithOptions(modalItem, options);
            setModalItem(null);
          }}
        />
      )}
    </div>
  );
}

function ItemModal({ item, onClose, onAdd }) {
  const [selected, setSelected] = useState([]);
  const unit = item.price + selected.reduce((s, o) => s + o.price_delta, 0);

  function toggle(option) {
    setSelected((s) =>
      s.some((o) => o.id === option.id) ? s.filter((o) => o.id !== option.id) : [...s, option],
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()}>
        <h2>{item.name}</h2>
        <p className="muted">{item.description}</p>
        {item.option_groups.map((group) => (
          <div key={group.id} className="option-group">
            <h3>{group.name}</h3>
            <div className="option-list">
              {group.options.map((o) => (
                <button
                  key={o.id}
                  className={`option-chip ${selected.some((s) => s.id === o.id) ? 'selected' : ''}`}
                  onClick={() => toggle(o)}
                >
                  {o.name}
                  {o.price_delta > 0 && <span className="delta">+{formatPrice(o.price_delta)}</span>}
                </button>
              ))}
            </div>
          </div>
        ))}
        <div className="modal-actions">
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" onClick={() => onAdd(selected)}>
            Add · {formatPrice(unit)}
          </button>
        </div>
      </div>
    </div>
  );
}

function Cart({ cart, total, onSetOptions, onQuantity, onCheckout, onReset }) {
  return (
    <aside className="cart">
      <div className="cart-head">
        <h2>Your order</h2>
        <button className="btn ghost small" onClick={onReset}>
          Clear
        </button>
      </div>
      {cart.length === 0 ? (
        <p className="muted">Tap items to add them.</p>
      ) : (
        <ul className="cart-lines">
          {cart.map((line, i) => {
            const unit = line.item.price + line.options.reduce((s, o) => s + o.price_delta, 0);
            return (
              <li key={i} className="cart-line">
                <div className="cart-line-main">
                  <span className="qty">{line.quantity}×</span>
                  <span className="name">{line.item.name}</span>
                  <span className="price">{formatPrice(unit * line.quantity)}</span>
                </div>
                {line.item.option_groups.length > 0 && (
                  <div className="cart-line-options">
                    {line.item.option_groups.map((g) =>
                      g.options.map((o) => (
                        <button
                          key={o.id}
                          className={`mini-chip ${line.options.some((s) => s.id === o.id) ? 'selected' : ''}`}
                          onClick={() => onSetOptions(i, o)}
                        >
                          {o.name}
                        </button>
                      )),
                    )}
                  </div>
                )}
                <div className="cart-line-qty">
                  <button onClick={() => onQuantity(i, -1)}>−</button>
                  <span>{line.quantity}</span>
                  <button onClick={() => onQuantity(i, 1)}>+</button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <div className="cart-total">
        <span>Total</span>
        <span>{formatPrice(total)}</span>
      </div>
      <button className="btn primary huge" disabled={cart.length === 0} onClick={onCheckout}>
        Checkout
      </button>
    </aside>
  );
}

function Review({ cart, total, onBack, onContinue }) {
  return (
    <div className="center">
      <div className="card review-card">
        <h1>Review your order</h1>
        <ul className="review-lines">
          {cart.map((line, i) => {
            const unit = line.item.price + line.options.reduce((s, o) => s + o.price_delta, 0);
            return (
              <li key={i}>
                <div>
                  <strong>
                    {line.quantity}× {line.item.name}
                  </strong>
                  {line.options.length > 0 && (
                    <span className="muted"> · {line.options.map((o) => o.name).join(', ')}</span>
                  )}
                </div>
                <span>{formatPrice(unit * line.quantity)}</span>
              </li>
            );
          })}
        </ul>
        <div className="review-total">
          <span>Total</span>
          <span>{formatPrice(total)}</span>
        </div>
        <div className="modal-actions">
          <button className="btn ghost" onClick={onBack}>
            Back
          </button>
          <button className="btn primary" onClick={onContinue}>
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}

function Pay({ total, paying, error, onBack, onSubmit }) {
  return (
    <div className="center">
      <div className="card pay-card">
        <h1>Payment</h1>
        <p className="subtitle">{formatPrice(total)}</p>
        <p className="muted">This is a demo — no real charge.</p>
        <div className="pay-fields">
          <input placeholder="Card number" inputMode="numeric" />
          <div className="pay-row">
            <input placeholder="MM/YY" />
            <input placeholder="CVC" />
          </div>
        </div>
        {error && <p className="error-text">{error}</p>}
        <div className="modal-actions">
          <button className="btn ghost" onClick={onBack}>
            Back
          </button>
          <button className="btn primary huge" disabled={paying} onClick={onSubmit}>
            {paying ? 'Placing…' : `Pay ${formatPrice(total)}`}
          </button>
        </div>
      </div>
    </div>
  );
}
