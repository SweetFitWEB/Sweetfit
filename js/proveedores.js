// Proveedores específico
function initProveedoresPage() {
  const contenedor = document.getElementById("listaProveedores");
  if (!contenedor) return;

  if (!window.__proveedoresInit) {
    window.__proveedoresInit = true;
    initProveedorModal();

    document.querySelector(".btn-agregar-proveedor")?.addEventListener("click", abrirModalProveedor);
    document.querySelector(".btn-nueva-compra")?.addEventListener("click", abrirModalCompra);
    document.getElementById("formCompra")?.addEventListener("submit", guardarCompra);
    document.getElementById("filtroFecha")?.addEventListener("change", cargarHistorialCompras);

    const buscador = document.getElementById("buscadorProveedores");
    if (buscador && !buscador.dataset.listener) {
      buscador.dataset.listener = "1";
      buscador.addEventListener("input", (e) => {
        const texto = e.target.value.toLowerCase();
        mostrarProveedores(
          listaProveedores.filter((p) => (p?.NOMBRE || "").toLowerCase().includes(texto))
        );
      });
    }
  }

  cargarProveedores();
  cargarProductosProveedor();
  cargarHistorialCompras();
}

window.initProveedoresPage = initProveedoresPage;

document.addEventListener("DOMContentLoaded", () => {
  initProveedoresPage();
});

document.addEventListener("proveedor:loaded", () => {
  initProveedoresPage();
});

let listaProveedores = [];
let productosCompra = [];

function initProveedorModal() {
  const modal = document.getElementById("modalProveedor");
  const btnAbrir = document.querySelector(".btn-agregar-proveedor");
  const btnCerrar = document.querySelector(".cerrar-modal-proveedor");
  const form = document.getElementById("formProveedor");

  if (btnAbrir && modal) {
    btnAbrir.addEventListener("click", () => modal.style.display = "block");
  }

  if (btnCerrar && modal) {
    btnCerrar.addEventListener("click", () => modal.style.display = "none");
  }

  if (form) {
    form.addEventListener("submit", guardarProveedor);
  }

  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });
}

async function guardarProveedor(e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  const id = formData.get("id_proveedor");

  const url = id 
    ? `${API}/api/proveedores/${id}`
    : `${API}/api/proveedores`;

  const method = id ? "PUT" : "POST";

  try {
    await api(url, { method, body: JSON.stringify(Object.fromEntries(formData)) });
    alert("Proveedor guardado");
    e.target.reset();
    document.getElementById("modalProveedor").style.display = "none";
    cargarProveedores();
  } catch (error) {
    console.error("Error al guardar proveedor:", error);
  }
}

async function cargarProveedores(filtroNombre = '') {
  try {
    const data = await api("/api/proveedores");
    listaProveedores = data;
    mostrarProveedores(data);
  } catch (error) {
    console.error("Error al cargar proveedores:", error);
  }
}

function mostrarProveedores(proveedores) {
  const tbody = document.getElementById("listaProveedores");
  if (!tbody) return;

  tbody.innerHTML = "";
  proveedores.forEach(prov => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${prov.NOMBRE}</td>
      <td>${prov.EMAIL || 'N/A'}</td>
      <td>${prov.TELEFONO || 'N/A'}</td>
      <td class="col-acciones">
        <button class="btn-editarprov" title="Editar proveedor" onclick="editarProveedor(${prov.ID_PROVEEDOR})">✏️</button>
        <button class="btn-eliminar" title="Eliminar proveedor" onclick="eliminarProveedor(${prov.ID_PROVEEDOR})">🗑️</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
  
  cargarSelectProveedores(proveedores);
}

function cargarSelectProveedores(proveedores) {
  const select = document.getElementById("proveedorSelect");
  if (!select) return;

  select.innerHTML = "<option value=''>Selecciona proveedor</option>";
  proveedores.forEach(p => {
    const option = document.createElement("option");
    option.value = p.ID_PROVEEDOR;
    option.textContent = p.NOMBRE;
    select.appendChild(option);
  });
}

function abrirModalProveedor() {
  document.getElementById("modalProveedor").style.display = "block";
}

async function cargarHistorialCompras() {
  const fecha = document.getElementById("filtroFecha").value;
  let url = "/api/compras";
  if (fecha) url += `?fecha=${fecha}`;

  try {
    const data = await api(url);
    mostrarHistorialCompras(data);
  } catch (error) {
    console.error("Error al cargar historial de compras:", error);
  }
}

function mostrarHistorialCompras(compras) {
  const tabla = document.getElementById("tablaCompras");
  if (!tabla) return;

  const tbody = tabla.querySelector("tbody") || tabla.createTBody();
  tbody.innerHTML = "";

  compras.forEach(compra => {
    const row = tbody.insertRow();
    row.innerHTML = `
      <td>${compra.fecha}</td>
      <td>${compra.proveedor}</td>
      <td>$${parseFloat(compra.total).toFixed(2)}</td>
      <td>${compra.estado}</td>
      <td><button class="btn-ver" onclick="mostrarTicketCompra(${compra.id_compra})">Ver</button></td>
    `;
  });
}

async function guardarCompra(e) {
  e.preventDefault();

  const proveedorId = document.getElementById("proveedorSelect")?.value;
  if (!proveedorId || productosCompra.length === 0) {
    return alert("Selecciona proveedor y agrega productos");
  }

  const usuarioData = getUsuarioData();
  const empleadoId = usuarioData?.id;

  if (!empleadoId) {
    alert("No se pudo identificar al empleado logueado");
    return;
  }

  const productosUnicos = [];
  productosCompra.forEach(p => {
    const yaExiste = productosUnicos.find(x => x.id === p.id);
    if (yaExiste) {
      yaExiste.cantidad += p.cantidad;
    } else {
      productosUnicos.push({ ...p });
    }
  });

  const total = productosUnicos.reduce((sum, item) => sum + (item.precio * item.cantidad), 0);

  const payload = {
    id_proveedor: proveedorId,
    id_empleado: empleadoId,
    total: total,
    productos: productosUnicos.map(p => ({
      id_producto: p.id,
      cantidad: p.cantidad,
      precio: p.precio
    }))
  };

  try {
    await api("/api/compras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    alert("Compra registrada correctamente");
    document.getElementById("modalCompra").style.display = "none";
    e.target.reset();
    productosCompra = [];
    actualizarListaProductosCompra();
    cargarHistorialCompras();
  } catch (error) {
    console.error("Error al guardar compra:", error);
    alert("Error al registrar compra");
  }
}

function cerrarModalCompra() {
  const modal = document.getElementById("modalCompra");
  if (modal) modal.style.display = "none";
}
window.cerrarModalCompra = cerrarModalCompra;

function agregarProductoCompra() {
  const productoSelect = document.getElementById("productoSelect");
  if (!productoSelect || !productoSelect.value) return alert("Selecciona un producto");
  
  const productoId = parseInt(productoSelect.value);
  const nombreTexto = productoSelect.options[productoSelect.selectedIndex].text;
  
  // Extraer nombre y precio del texto (ej. "Manzana (Precio Ref: $10.00)")
  const nombreProducto = nombreTexto.split(" (Precio Ref:")[0];
  const match = nombreTexto.match(/\$([\d.]+)/);
  const precio = match ? parseFloat(match[1]) : 0;

  const cantidad = parseInt(document.getElementById("cantidadProducto").value);

  if (isNaN(cantidad) || cantidad <= 0) {
    return alert("Completa una cantidad válida");
  }

  const existente = productosCompra.find(p => p.id === productoId);
  if (existente) {
    existente.cantidad += cantidad;
  } else {
    productosCompra.push({ id: productoId, nombre: nombreProducto, cantidad, precio });
  }

  actualizarListaProductosCompra();
  document.getElementById("cantidadProducto").value = "";
  document.getElementById("productoSelect").value = "";
}
window.agregarProductoCompra = agregarProductoCompra;

function actualizarListaProductosCompra() {
  const contenedor = document.getElementById("listaProductosCompra");
  if (!contenedor) return;
  
  contenedor.innerHTML = "";
  let total = 0;
  
  productosCompra.forEach(prod => {
    const div = document.createElement("div");
    div.style.display = "flex";
    div.style.justifyContent = "space-between";
    div.style.marginBottom = "5px";
    
    const subtotal = prod.cantidad * prod.precio;
    total += subtotal;
    
    div.innerHTML = `
      <span>${prod.nombre} - ${prod.cantidad} unidades</span>
      <span>$${subtotal.toFixed(2)}</span>
      <button type="button" class="btn-eliminar" onclick="eliminarProductoCompra(${prod.id})" style="padding:2px 5px; font-size:12px;">❌</button>
    `;
    contenedor.appendChild(div);
  });
  
  const divTotal = document.createElement("div");
  divTotal.style.fontWeight = "bold";
  divTotal.style.marginTop = "10px";
  divTotal.style.borderTop = "1px solid #ccc";
  divTotal.style.paddingTop = "5px";
  divTotal.innerHTML = `Total de compra: $${total.toFixed(2)}`;
  contenedor.appendChild(divTotal);
}

function eliminarProductoCompra(id) {
  productosCompra = productosCompra.filter(p => p.id !== id);
  actualizarListaProductosCompra();
}
window.eliminarProductoCompra = eliminarProductoCompra;

function abrirModalCompra() {
  const modal = document.getElementById("modalCompra");
  if (modal) modal.style.display = "block";
}

async function cargarProductosProveedor() {
  const selectProv = document.getElementById("proveedorSelect");
  if (!selectProv || !selectProv.value) return;

  const idProveedor = selectProv.value;
  
  try {
    const productos = await api(`/api/proveedores/${idProveedor}/productos`);
    const selectProd = document.getElementById("productoSelect");
    if (!selectProd) return;

    selectProd.innerHTML = "<option value=''>Selecciona producto</option>";
    
    (productos || []).forEach(p => {
      const option = document.createElement("option");
      option.value = p.ID_PRODUCTO;
      option.textContent = `${p.NOMBRE} (Precio Ref: $${parseFloat(p.PRECIO).toFixed(2)})`;
      selectProd.appendChild(option);
    });
  } catch (error) {
    console.error("Error al cargar productos del proveedor:", error);
  }
}

function editarProveedor(id) {
  const prov = listaProveedores.find(p => p.ID_PROVEEDOR === id);
  if (!prov) {
    alert("Proveedor no encontrado");
    return;
  }

  const modal = document.getElementById("modalProveedor");
  const form = document.getElementById("formProveedor");
  const titulo = modal?.querySelector("h3");

  if (form) {
    if (form.id_proveedor) form.id_proveedor.value = prov.ID_PROVEEDOR;
    if (form.nombre) form.nombre.value = prov.NOMBRE || "";
    if (form.email) form.email.value = prov.EMAIL || "";
    if (form.telefono) form.telefono.value = prov.TELEFONO || "";
  }

  if (titulo) titulo.textContent = "Editar Proveedor";
  if (modal) modal.style.display = "flex";
}

async function eliminarProveedor(id) {
  if (!confirm("¿Estás seguro de eliminar este proveedor?")) return;

  try {
    await api(`/api/proveedores/${id}`, { method: "DELETE" });
    alert("Proveedor eliminado");
    cargarProveedores();
  } catch (error) {
    console.error("Error al eliminar proveedor:", error);
  }
}

async function mostrarTicketCompra(id_compra) {
  try {
    const data = await api(`/api/compras/${id_compra}?t=${Date.now()}`);
    const detalles = data.detalles || [];
    const fechaCompra = new Date(data.fecha); 
    const proveedor = data.proveedor || 'Proveedor desconocido';
    const ordenCompra = data.orden || id_compra;
    const empleado = data.empleado || '';

    const options = { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    };
    const fechaFormateada = fechaCompra.toLocaleDateString('es-ES', options);

    let html = `
      <div class="ticket-header" style="text-align: center; border-bottom: 2px dashed #ccc; padding-bottom: 10px; margin-bottom: 10px;">
        <h2 style="margin:0 0 10px 0;">SWEETFIT - COMPRA</h2>
        <p style="margin:5px 0;"><strong>Fecha:</strong> ${fechaFormateada}</p>
        <p style="margin:5px 0;"><strong>Proveedor:</strong> ${proveedor}</p>
        <p style="margin:5px 0;"><strong>Empleado:</strong> ${empleado}</p>
        <p style="margin:5px 0;"><strong>Orden:</strong> #${ordenCompra}</p>
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="border-bottom: 1px solid #eee;">
            <th>Cant.</th>
            <th>Producto</th>
            <th>Precio U.</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
    `;

    if (detalles.length === 0) {
      html += `<tr><td colspan="4" style="text-align:center;">No hay detalles</td></tr>`;
    } else {
      detalles.forEach(item => {
        const cant = parseFloat(item.CANTIDAD_COMPRA || item.cantidad || 0);
        const pre = parseFloat(item.PRECIO_COMPRA || item.precio || 0);
        const sub = parseFloat(item.SUBTOTAL_COMPRA || item.subtotal || (cant * pre));
        html += `
          <tr>
            <td>${cant}</td>
            <td>${item.PRODUCTO || item.producto || ''}</td>
            <td>$${pre.toFixed(2)}</td>
            <td>$${sub.toFixed(2)}</td>
          </tr>
        `;
      });
    }

    html += `
        </tbody>
      </table>
      <div style="text-align: right; margin-top: 15px; font-size: 1.2em;">
        <strong>Total: $${parseFloat(data.total || 0).toFixed(2)}</strong>
      </div>
    `;

    const contenido = document.getElementById("contenidoTicket");
    if (contenido) contenido.innerHTML = html;
    
    const modal = document.getElementById("modalTicket");
    if (modal) modal.style.display = "block";
  } catch (error) {
    console.error("Error al cargar el ticket de compra:", error);
    alert("No se pudo cargar el ticket de la compra.");
  }
}
window.mostrarTicketCompra = mostrarTicketCompra;
