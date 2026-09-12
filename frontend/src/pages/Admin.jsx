import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, formatPrice } from '../api.js';

export default function Admin() {
  const [tab, setTab] = useState('menu');
  const [menu, setMenu] = useState([]);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState(null);

  async function loadMenu() {
    try {
      setMenu(await api.getMenu());
    } catch (e) {
      setError(e.message);
    }
  }
  async function loadOrders() {
    try {
      setOrders(await api.listOrders());
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadMenu();
    loadOrders();
  }, []);

  return (
    <div className="admin">
      <header className="topbar admin-topbar">
        <h1>Admin</h1>
        <Link to="/" className="btn ghost">
          ← Kiosk
        </Link>
      </header>

      <nav className="admin-tabs">
        <button className={tab === 'menu' ? 'active' : ''} onClick={() => setTab('menu')}>
          Menu
        </button>
        <button className={tab === 'orders' ? 'active' : ''} onClick={() => setTab('orders')}>
          Orders
        </button>
      </nav>

      {error && <p className="error-text">{error}</p>}

      {tab === 'menu' && <MenuManager menu={menu} onChanged={loadMenu} />}
      {tab === 'orders' && <OrdersList orders={orders} />}
    </div>
  );
}

function MenuManager({ menu, onChanged }) {
  const [editing, setEditing] = useState(null); // {type, item, group}
  const [busy, setBusy] = useState(false);

  async function run(fn) {
    setBusy(true);
    try {
      await fn();
      await onChanged();
      setEditing(null);
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="menu-manager">
      <div className="menu-toolbar">
        <button className="btn primary" onClick={() => setEditing({ type: 'category' })}>
          + Category
        </button>
        <button className="btn" onClick={() => setEditing({ type: 'group' })}>
          + Option group
        </button>
      </div>

      {menu.map((category) => (
        <section key={category.id} className="admin-category">
          <div className="admin-category-head">
            <h2>{category.name}</h2>
            <div className="row">
              <button
                className="btn ghost small"
                onClick={() => setEditing({ type: 'category', item: category })}
              >
                Edit
              </button>
              <button
                className="btn ghost small danger"
                onClick={() => run(() => api.deleteCategory(category.id))}
              >
                Delete
              </button>
              <button
                className="btn ghost small"
                onClick={() => setEditing({ type: 'item', categoryId: category.id })}
              >
                + Item
              </button>
            </div>
          </div>

          <ul className="admin-items">
            {category.items.map((item) => (
              <li key={item.id} className="admin-item">
                <img src={item.image_url} alt="" width={40} height={40} />
                <div className="admin-item-info">
                  <strong>{item.name}</strong>
                  <span className="muted">
                    {formatPrice(item.price)} · stock {item.stock}
                    {item.option_groups.length > 0 &&
                      ` · ${item.option_groups.map((g) => g.name).join(', ')}`}
                  </span>
                </div>
                <div className="row">
                  <button className="btn ghost small" onClick={() => setEditing({ type: 'item', item })}>
                    Edit
                  </button>
                  <button
                    className="btn ghost small danger"
                    onClick={() => run(() => api.deleteItem(item.id))}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {editing && (
        <Editor
          editing={editing}
          menu={menu}
          busy={busy}
          onClose={() => setEditing(null)}
          onSave={(payload, type, id) => {
            const calls = {
              category: id ? () => api.updateCategory(id, payload) : () => api.createCategory(payload),
              item: id ? () => api.updateItem(id, payload) : () => api.createItem(payload),
              group: id ? () => api.updateOptionGroup(id, payload) : () => api.createOptionGroup(payload),
            };
            return run(calls[type]);
          }}
        />
      )}
    </div>
  );
}

function Editor({ editing, menu, busy, onClose, onSave }) {
  const { type, item, group, categoryId } = editing;
  const [form, setForm] = useState(() => {
    if (type === 'category')
      return { name: item?.name ?? '', description: item?.description ?? '', sort_order: item?.sort_order ?? 0 };
    if (type === 'group') return { name: group?.name ?? '', sort_order: group?.sort_order ?? 0 };
    return {
      category_id: item?.category_id ?? categoryId ?? '',
      name: item?.name ?? '',
      description: item?.description ?? '',
      price: item?.price ?? 0,
      stock: item?.stock ?? 0,
      image_url: item?.image_url ?? '',
      option_group_ids: item?.option_groups?.map((g) => g.id) ?? [],
    };
  });

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function toPayload() {
    if (type === 'category') return { ...form, sort_order: Number(form.sort_order) };
    if (type === 'group') return { ...form, sort_order: Number(form.sort_order) };
    return {
      ...form,
      category_id: Number(form.category_id),
      price: Math.round(Number(form.price) * 100),
      stock: Number(form.stock),
      option_group_ids: form.option_group_ids.map(Number),
    };
  }

  const allGroups = [
    ...new Map(
      menu.flatMap((c) => c.items).flatMap((i) => i.option_groups).map((g) => [g.id, g]),
    ).values(),
  ];

  const title =
    type === 'category' ? (item ? 'Edit category' : 'New category') :
    type === 'group' ? (group ? 'Edit option group' : 'New option group') :
    item ? 'Edit item' : 'New item';

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>

        {type === 'category' && (
          <>
            <Field label="Name" value={form.name} onChange={(v) => set('name', v)} />
            <Field label="Description" value={form.description} onChange={(v) => set('description', v)} />
            <Field label="Sort order" type="number" value={form.sort_order} onChange={(v) => set('sort_order', v)} />
          </>
        )}

        {type === 'group' && (
          <>
            <Field label="Name" value={form.name} onChange={(v) => set('name', v)} />
            <Field label="Sort order" type="number" value={form.sort_order} onChange={(v) => set('sort_order', v)} />
          </>
        )}

        {type === 'item' && (
          <>
            <Field label="Name" value={form.name} onChange={(v) => set('name', v)} />
            <Field label="Description" value={form.description} onChange={(v) => set('description', v)} />
            <label className="field">
              Category
              <select value={form.category_id} onChange={(e) => set('category_id', e.target.value)}>
                <option value="">Select…</option>
                {menu.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <Field
              label="Price ($)"
              type="number"
              step="0.01"
              value={form.price / 100}
              onChange={(v) => set('price', v)}
            />
            <Field label="Stock" type="number" value={form.stock} onChange={(v) => set('stock', v)} />
            <Field label="Image URL" value={form.image_url} onChange={(v) => set('image_url', v)} />
            <div className="field">
              <span className="label">Option groups</span>
              {allGroups.map((g) => (
                <label key={g.id} className="checkbox">
                  <input
                    type="checkbox"
                    checked={form.option_group_ids.includes(g.id)}
                    onChange={(e) =>
                      set(
                        'option_group_ids',
                        e.target.checked
                          ? [...form.option_group_ids, g.id]
                          : form.option_group_ids.filter((x) => x !== g.id),
                      )
                    }
                  />
                  {g.name}
                </label>
              ))}
            </div>
          </>
        )}

        <div className="modal-actions">
          <button className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={busy} onClick={() => onSave(toPayload(), type, item?.id ?? group?.id)}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, type = 'text', value, onChange, step }) {
  return (
    <label className="field">
      {label}
      <input type={type} step={step} value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function OrdersList({ orders }) {
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  async function open(id) {
    setSelected(id);
    setDetail(await api.getOrder(id));
  }

  return (
    <div className="orders">
      <table className="orders-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Status</th>
            <th>Total</th>
            <th>Placed</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} onClick={() => open(o.id)}>
              <td>{o.number}</td>
              <td>{o.status}</td>
              <td>{formatPrice(o.total)}</td>
              <td>{new Date(o.created_at).toLocaleTimeString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()}>
            <h2>Order #{detail?.number}</h2>
            {detail && (
              <ul className="review-lines">
                {detail.items.map((line, i) => (
                  <li key={i}>
                    <div>
                      <strong>
                        {line.quantity}× {line.item_name}
                      </strong>
                      {line.options.length > 0 && (
                        <span className="muted"> · {line.options.map((o) => o.option_name).join(', ')}</span>
                      )}
                    </div>
                    <span>{formatPrice(line.unit_price * line.quantity)}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="review-total">
              <span>Total</span>
              <span>{formatPrice(detail?.total ?? 0)}</span>
            </div>
            <div className="modal-actions">
              <button className="btn ghost" onClick={() => setSelected(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
