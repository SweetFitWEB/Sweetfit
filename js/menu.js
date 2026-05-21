/* ── Estado del carrito ── */
let carrito = JSON.parse(localStorage.getItem('sweetfit_carrito') || '[]');
let menuData = {}; // { Categoria: [productos...] }

const API_BASE = 'http://localhost:5000';

/* ── Inicio ── */
document.addEventListener('DOMContentLoaded', () => {
  cargarMenu();
  renderizarCarrito();

  // Eventos del carrito
  document.getElementById('btnAbrirCarrito').addEventListener('click', abrirCarrito);
  document.getElementById('btnCerrarCarrito').addEventListener('click', cerrarCarrito);
  document.getElementById('carritoOverlay').addEventListener('click', cerrarCarrito);
  document.getElementById('btnVaciarCarrito').addEventListener('click', vaciarCarrito);
  document.getElementById('btnConfirmarPedido').addEventListener('click', abrirModalPedido);
  document.getElementById('btnCancelarModal').addEventListener('click', cerrarModalPedido);
  document.getElementById('formPedido').addEventListener('submit', enviarPedido);
});

/* ── Cargar menú desde API ── */
async function cargarMenu() {
  try {
    const resp = await fetch(`${API_BASE}/api/menu`);
    menuData = await resp.json();

    construirFiltros(Object.keys(menuData));
    renderizarMenu('todos');

    document.getElementById('cargandoMsg')?.remove();
  } catch (err) {
    document.getElementById('cargandoMsg').textContent = '❌ No se pudo cargar el menú. Intenta más tarde.';
    console.error(err);
  }
}

/* ── Filtros de categoría ── */
function construirFiltros(categorias) {
  const nav = document.getElementById('filtrosCategorias');
  const emojis = {
    'Hamburguesas': '🍔', 'Hot Dogs': '🌭', 'Postres': '🍰',
    'Bebidas': '🥤', 'Papas': '🍟'
  };

  categorias.forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'filtro-cat';
    btn.dataset.cat = cat;
    btn.textContent = `${emojis[cat] || '🍽️'} ${cat}`;
    btn.id = `filtro-${cat.replace(/\s/g,'-')}`;
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filtro-cat').forEach(b => b.classList.remove('activo'));
      btn.classList.add('activo');
      renderizarMenu(cat);
    });
    nav.appendChild(btn);
  });

  document.getElementById('filtro-todos').addEventListener('click', () => {
    document.querySelectorAll('.filtro-cat').forEach(b => b.classList.remove('activo'));
    document.getElementById('filtro-todos').classList.add('activo');
    renderizarMenu('todos');
  });
}

/* ── Renderizar productos ── */
function renderizarMenu(filtro) {
  const contenedor = document.getElementById('menuContent');
  contenedor.innerHTML = '';

  const categorias = filtro === 'todos' ? Object.keys(menuData) : [filtro];

  if (categorias.length === 0) {
    contenedor.innerHTML = '<p style="text-align:center;color:#888;padding:60px;">No hay productos disponibles en esta categoría.</p>';
    return;
  }

  categorias.forEach(cat => {
    const productos = menuData[cat];
    if (!productos?.length) return;

    const seccion = document.createElement('div');
    seccion.className = 'categoria-seccion';
    seccion.id = `cat-${cat.replace(/\s/g, '-')}`;

    const titulo = document.createElement('h2');
    titulo.className = 'categoria-titulo';
    titulo.textContent = cat;
    seccion.appendChild(titulo);

    const grid = document.createElement('div');
    grid.className = 'grid-menu';

    productos.forEach(prod => {
      grid.appendChild(crearCardProducto(prod));
    });

    seccion.appendChild(grid);
    contenedor.appendChild(seccion);
  });
}

function crearCardProducto(prod) {
  const div = document.createElement('div');
  div.className = 'card-menu';

  const imgSrc = prod.IMAGEN
    ? `${API_BASE}/uploads/${prod.IMAGEN}`
    : `https://placehold.co/300x170/ABBF7F/white?text=${encodeURIComponent(prod.NOMBRE)}`;

  div.innerHTML = `
    <img src="${imgSrc}" alt="${prod.NOMBRE}" onerror="this.src='https://placehold.co/300x170/ABBF7F/white?text=${encodeURIComponent(prod.NOMBRE)}'"/>
    <div class="card-body">
      <h3>${prod.NOMBRE}</h3>
      <p class="desc">${prod.DESCRIPCION || ''}</p>
      <div class="card-footer">
        <span class="precio">$${prod.PRECIO.toFixed(2)}</span>
        <button class="btn-agregar" id="btn-prod-${prod.ID_PRODUCTO}" onclick="agregarAlCarrito(${prod.ID_PRODUCTO}, '${prod.NOMBRE.replace(/'/g,"\\'")}', ${prod.PRECIO})">
          <i class="fi fi-br-plus"></i> Agregar
        </button>
      </div>
    </div>
  `;
  return div;
}

/* ── Carrito ── */
function agregarAlCarrito(id, nombre, precio) {
  const existente = carrito.find(i => i.id_producto === id);
  if (existente) {
    existente.cantidad++;
  } else {
    carrito.push({ id_producto: id, nombre, precio, cantidad: 1 });
  }
  guardarCarrito();
  renderizarCarrito();

  // Animación en el botón
  const btn = document.getElementById(`btn-prod-${id}`);
  if (btn) {
    btn.classList.add('pop');
    setTimeout(() => btn.classList.remove('pop'), 300);
  }
}

function cambiarCantidad(id, delta) {
  const item = carrito.find(i => i.id_producto === id);
  if (!item) return;
  item.cantidad += delta;
  if (item.cantidad <= 0) {
    carrito = carrito.filter(i => i.id_producto !== id);
  }
  guardarCarrito();
  renderizarCarrito();
}

function eliminarDelCarrito(id) {
  carrito = carrito.filter(i => i.id_producto !== id);
  guardarCarrito();
  renderizarCarrito();
}

function vaciarCarrito() {
  if (!carrito.length) return;
  if (!confirm('¿Vaciar el carrito?')) return;
  carrito = [];
  guardarCarrito();
  renderizarCarrito();
}

function guardarCarrito() {
  localStorage.setItem('sweetfit_carrito', JSON.stringify(carrito));
}

function renderizarCarrito() {
  const contenedor = document.getElementById('carritoItems');
  const totalEl = document.getElementById('carritoTotal');
  const badge = document.getElementById('carritoContador');

  const totalItems = carrito.reduce((s, i) => s + i.cantidad, 0);
  const totalPrecio = carrito.reduce((s, i) => s + i.precio * i.cantidad, 0);

  badge.textContent = totalItems;
  totalEl.textContent = `$${totalPrecio.toFixed(2)}`;

  if (carrito.length === 0) {
    contenedor.innerHTML = `
      <div class="carrito-vacio">
        <span>🛒</span>
        <p>Tu carrito está vacío.</p>
        <p style="font-size:0.85rem; margin-top:6px;">¡Agrega algo del menú!</p>
      </div>`;
    return;
  }

  contenedor.innerHTML = '';
  carrito.forEach(item => {
    const div = document.createElement('div');
    div.className = 'item-carrito';
    div.innerHTML = `
      <div class="item-carrito-info">
        <div class="item-carrito-nombre">${item.nombre}</div>
        <div class="item-carrito-precio">$${(item.precio * item.cantidad).toFixed(2)}</div>
      </div>
      <div class="item-carrito-controles">
        <button class="btn-ctrl" onclick="cambiarCantidad(${item.id_producto}, -1)">−</button>
        <span class="item-carrito-cantidad">${item.cantidad}</span>
        <button class="btn-ctrl" onclick="cambiarCantidad(${item.id_producto}, 1)">+</button>
        <button class="btn-eliminar-item" onclick="eliminarDelCarrito(${item.id_producto})" title="Quitar">🗑️</button>
      </div>
    `;
    contenedor.appendChild(div);
  });
}

/* ── Abrir/cerrar carrito ── */
function abrirCarrito() {
  document.getElementById('carritoPanel').classList.add('abierto');
  document.getElementById('carritoOverlay').classList.add('abierto');
  document.body.style.overflow = 'hidden';
}

function cerrarCarrito() {
  document.getElementById('carritoPanel').classList.remove('abierto');
  document.getElementById('carritoOverlay').classList.remove('abierto');
  document.body.style.overflow = '';
}

/* ── Modal pedido ── */
function abrirModalPedido() {
  if (carrito.length === 0) {
    alert('Agrega al menos un producto antes de confirmar tu pedido.');
    return;
  }
  cerrarCarrito();

  const total = carrito.reduce((s, i) => s + i.precio * i.cantidad, 0);
  const resumen = carrito.map(i => `${i.cantidad}× ${i.nombre} — $${(i.precio * i.cantidad).toFixed(2)}`).join('<br>');
  document.getElementById('resumenModal').innerHTML = `
    <strong>Resumen:</strong><br>
    <span style="display:block; margin:6px 0;">${resumen}</span>
    <strong>Total: $${total.toFixed(2)}</strong>
  `;

  document.getElementById('modalPedido').classList.add('abierto');
}

function cerrarModalPedido() {
  document.getElementById('modalPedido').classList.remove('abierto');
}

/* ── Enviar pedido ── */
async function enviarPedido(e) {
  e.preventDefault();
  const btn = document.getElementById('btnEnviarPedido');
  btn.disabled = true;
  btn.textContent = 'Enviando...';

  const payload = {
    nombre: document.getElementById('pedidoNombre').value.trim(),
    telefono: document.getElementById('pedidoTelefono').value.trim(),
    tipo_pedido: document.getElementById('pedidoTipo').value,
    notas: document.getElementById('pedidoNotas').value.trim(),
    items: carrito.map(i => ({
      id_producto: i.id_producto,
      cantidad: i.cantidad,
      precio: i.precio
    }))
  };

  try {
    const resp = await fetch(`${API_BASE}/api/pedidos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();

    if (!resp.ok) throw new Error(data.error || 'Error al enviar el pedido');

    // Limpiar carrito
    carrito = [];
    guardarCarrito();

    // Redirigir a confirmación
    localStorage.setItem('sweetfit_ultimo_pedido', JSON.stringify({
      id: data.id_pedido,
      total: data.total,
      nombre: data.nombre_cliente,
      tipo: payload.tipo_pedido
    }));
    window.location.href = `pedido_confirmado.html`;

  } catch (err) {
    alert('❌ No se pudo registrar el pedido: ' + err.message);
    btn.disabled = false;
    btn.textContent = '🚀 Enviar Pedido';
  }
}
