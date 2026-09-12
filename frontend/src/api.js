const BASE = '';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(body?.detail || `Request failed (${res.status})`);
  }
  return body;
}

export const api = {
  getMenu: () => request('/menu'),
  checkout: (payload) =>
    request('/checkout', { method: 'POST', body: JSON.stringify(payload) }),
  listOrders: () => request('/orders'),
  getOrder: (id) => request(`/orders/${id}`),

  createCategory: (payload) => request('/menu/categories', { method: 'POST', body: JSON.stringify(payload) }),
  updateCategory: (id, payload) => request(`/menu/categories/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteCategory: (id) => request(`/menu/categories/${id}`, { method: 'DELETE' }),

  createItem: (payload) => request('/menu/items', { method: 'POST', body: JSON.stringify(payload) }),
  updateItem: (id, payload) => request(`/menu/items/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteItem: (id) => request(`/menu/items/${id}`, { method: 'DELETE' }),

  createOptionGroup: (payload) => request('/menu/option-groups', { method: 'POST', body: JSON.stringify(payload) }),
  updateOptionGroup: (id, payload) => request(`/menu/option-groups/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteOptionGroup: (id) => request(`/menu/option-groups/${id}`, { method: 'DELETE' }),

  createOption: (groupId, payload) => request(`/menu/option-groups/${groupId}/options`, { method: 'POST', body: JSON.stringify(payload) }),
  updateOption: (id, payload) => request(`/menu/options/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteOption: (id) => request(`/menu/options/${id}`, { method: 'DELETE' }),
};

export const formatPrice = (cents) => `$${(cents / 100).toFixed(2)}`;
