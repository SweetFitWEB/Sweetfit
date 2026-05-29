// Ventas específico
function initVentasPage() {
  const formVenta = document.getElementById("formVenta");
  const contenedorProductos = document.getElementById("productosVentaContainer");
  if (!formVenta && !contenedorProductos) return;

  if (!window.__ventasInit) {
    window.__ventasInit = true;

    if (formVenta) {
      formVenta.addEventListener("submit", function(event) {
        event.preventDefault();
        registrarVenta();
      });
    }

    window.addEventListener("click", function(event) {
      const modal = document.getElementById("modalSeleccionarProductos");
      if (event.target === modal) {
        cerrarModalProductos();
      }
    });
  }

  document.querySelectorAll("#tablaCarrito tbody input[type='number']").forEach(input => {
    if (input.dataset.listener) return;
    input.dataset.listener = "1";
    input.addEventListener("input", () => {
      if (input.value === "" || parseInt(input.value) < 1) {
        input.value = 1;
        alert("La cantidad no puede ser negativa ni cero.");
      }
    });
  });

  cargarProductosParaVenta();
  cargarClientes();
  cargarEmpleados();
  autocompletarEmpleado();
  if (typeof activarAutocompleteCliente === "function") {
    activarAutocompleteCliente();
  }

  const esAdmin = getPuestoUsuario() === 'Administrador';
  const historialSection = document.querySelector('.historial-ventas');
  if (historialSection) {
    historialSection.style.display = esAdmin ? 'block' : 'none';
  }
  if (esAdmin && typeof cargarHistorialVentas === "function") {
    cargarHistorialVentas();
  }
  if (typeof cargarSelectEmpleados === "function") {
    cargarSelectEmpleados();
  }
}

window.initVentasPage = initVentasPage;

document.addEventListener("DOMContentLoaded", () => {
  initVentasPage();
});

document.addEventListener("ventas:loaded", () => {
  initVentasPage();
});

let carrito = [];

let paginaModalProductos = 1;
let textoModalProductos = "";

async function cargarProductosParaVenta() {
  try {
    const data = await api("/api/productos");
    const contenedor = document.getElementById("productosVentaContainer");
    if (contenedor) {
      contenedor.innerHTML = "";
      data.productos.forEach(prod => {
        if (prod.cantidad > 0) {
          const card = document.createElement("div");
          card.className = "producto-venta-card";
          card.innerHTML = `
            <img src="${API}/uploads/${prod.imagen}" alt="${prod.nombre}" onerror="this.style.display='none'">
            <h3>${prod.nombre}</h3>
            <p>Precio: $${parseFloat(prod.precio).toFixed(2)}</p>
            <p class="stock-producto">Stock: ${prod.cantidad}</p>
            <button onclick="agregarAlCarrito(${prod.id}, '${prod.nombre}', ${prod.precio}, ${prod.cantidad})">Agregar</button>
          `;
          contenedor.appendChild(card);
        }
      });
    }
  } catch (error) {
    console.error("Error al cargar productos para venta:", error);
  }
}

function abrirModalProductos() {
  const modal = document.getElementById("modalSeleccionarProductos");
  if (!modal) return;

  modal.style.display = "flex";

  const buscador = document.getElementById("buscador-modal");
  if (buscador && !buscador.dataset.listener) {
    buscador.dataset.listener = "1";
    buscador.addEventListener("input", () => {
      textoModalProductos = buscador.value.trim().toLowerCase();
      paginaModalProductos = 1;
      cargarProductosModal(paginaModalProductos, textoModalProductos);
    });
  }

  cargarProductosModal(paginaModalProductos, textoModalProductos);
}

function cerrarModalProductos() {
  const modal = document.getElementById("modalSeleccionarProductos");
  if (!modal) return;
  modal.style.display = "none";
}

async function cargarProductosModal(pagina = 1, texto = "") {
  let url = `/api/productos?page=${pagina}`;
  if (texto) {
    url += `&nombre=${encodeURIComponent(texto)}`;
  }

  try {
    const data = await api(url);
    const grid = document.getElementById("gridModalProductos");
    if (!grid) return;

    grid.innerHTML = "";
    (data.productos || []).forEach((prod) => {
      if (prod.cantidad <= 0) return;

      const card = document.createElement("div");
      card.className = "producto-venta-card";
      card.innerHTML = `
        <img src="${API}/uploads/${prod.imagen}" alt="${prod.nombre}" onerror="this.style.display='none'">
        <h3>${prod.nombre}</h3>
        <p>Precio: $${parseFloat(prod.precio).toFixed(2)}</p>
        <p class="stock-producto">Stock: ${prod.cantidad}</p>
        <button onclick="agregarAlCarrito(${prod.id}, '${prod.nombre}', ${prod.precio}, ${prod.cantidad})">Agregar</button>
      `;
      grid.appendChild(card);
    });

    renderPaginacionModal(data.total_paginas || 1, data.pagina_actual || pagina);
  } catch (error) {
    console.error("Error al cargar productos del modal:", error);
  }
}

function renderPaginacionModal(totalPaginas, paginaActual) {
  const cont = document.getElementById("paginacionModalProductos");
  if (!cont) return;

  cont.innerHTML = "";

  const btnPrev = document.createElement("button");
  btnPrev.type = "button";
  btnPrev.textContent = "<";
  btnPrev.disabled = paginaActual <= 1;
  btnPrev.addEventListener("click", () => {
    paginaModalProductos = Math.max(1, paginaActual - 1);
    cargarProductosModal(paginaModalProductos, textoModalProductos);
  });
  cont.appendChild(btnPrev);

  const label = document.createElement("span");
  label.textContent = `${paginaActual} / ${totalPaginas}`;
  cont.appendChild(label);

  const btnNext = document.createElement("button");
  btnNext.type = "button";
  btnNext.textContent = ">";
  btnNext.disabled = paginaActual >= totalPaginas;
  btnNext.addEventListener("click", () => {
    paginaModalProductos = Math.min(totalPaginas, paginaActual + 1);
    cargarProductosModal(paginaModalProductos, textoModalProductos);
  });
  cont.appendChild(btnNext);
}

async function cargarHistorialVentas() {
  const tabla = document.getElementById("tablaVentas");
  if (!tabla) return;

  const fechaInicio = document.getElementById("filtroFechaInicio")?.value;
  const fechaFin = document.getElementById("filtroFechaFin")?.value;
  const tipoVenta = document.getElementById("filtroTipo")?.value;
  const empleado = document.getElementById("selectEmpleadoVenta")?.value;

  let url = "/api/ventas/historial";
  const params = new URLSearchParams();
  if (fechaInicio) params.append("fecha_inicio", fechaInicio);
  if (fechaFin) params.append("fecha_fin", fechaFin);
  if (tipoVenta) params.append("tipo_venta", tipoVenta.charAt(0).toUpperCase() + tipoVenta.slice(1).toLowerCase());
  if (empleado) params.append("empleado", empleado);
  const qs = params.toString();
  if (qs) url += `?${qs}`;

  try {
    const data = await api(url);
    const tbody = tabla.querySelector("tbody") || tabla.createTBody();
    tbody.innerHTML = "";

    (data || []).forEach((venta) => {
      const row = tbody.insertRow();
      
      if (venta.ESTADO === "EN ESPERA") {
        row.style.cursor = "pointer";
        row.addEventListener("dblclick", () => cargarVentaParaEdicion(venta.ID_VENTA));
      }

      const estadoHtml = (venta.ESTADO !== 'FINALIZADA' && venta.ESTADO !== 'CANCELADA') 
        ? `<button type="button" class="btn-aceptarv" onclick="aceptarVenta(${venta.ID_VENTA})">✔️ Aceptar</button>
           <button type="button" class="btn-cancelarv" onclick="cancelarVenta(${venta.ID_VENTA})">❌ Cancelar</button>` 
        : '';
      row.innerHTML = `
        <td>${venta.ID_VENTA ?? ""}</td>
        <td>${venta.FECHA_VENTA ? new Date(venta.FECHA_VENTA).toLocaleDateString("es-MX", { day: "2-digit", month: "2-digit", year: "numeric" }) : ""}</td>
        <td>${venta.TIPO_VENTA ?? ""}</td>
        <td>${venta.nombre_empleado ?? ""}</td>
        <td>$${parseFloat(venta.TOTAL_VENTA || 0).toFixed(2)}</td>
        <td>${formatoEstado(venta.ESTADO)}</td>
        <td><button type="button" class="btn-ver-detalle" onclick="verDetalleVenta(${venta.ID_VENTA})">Ver</button></td>
        <td>${estadoHtml}</td>
      `;
    });
  } catch (error) {
    console.error("Error al cargar historial de ventas:", error);
  }
}

function filtrarVentas() {
  cargarHistorialVentas();
}

async function verDetalleVenta(idVenta) {
  const modal = document.getElementById("modalDetalleVenta");
  const cont = document.getElementById("detalleVentaContenido");
  if (!modal || !cont) return;

  try {
    const data = await api(`/api/ventas/${idVenta}`);
    const fecha = data.fecha ? new Date(data.fecha).toLocaleDateString("es-ES", {
      year: "numeric", month: "long", day: "numeric",
      hour: "2-digit", minute: "2-digit"
    }) : "";

    const tipoClass = data.tipo_venta === "Local" ? "tag-local"
      : data.tipo_venta === "Domicilio" ? "tag-domicilio"
      : "tag-app";

    const detalles = (data.detallesV || []).map((d) => {
      const precio = parseFloat(d.PRECIO_UNITARIO || 0);
      const subtotal = parseFloat(d.SUBTOTAL_VENTA || 0);
      return `<tr><td>${d.PRODUCTO ?? ""}</td><td>${d.CANTIDAD_VENTA ?? ""}</td><td>$${precio.toFixed(2)}</td><td>$${subtotal.toFixed(2)}</td></tr>`;
    }).join("");

    const total = (data.detallesV || []).reduce((sum, d) => sum + parseFloat(d.SUBTOTAL_VENTA || 0), 0);

    const esWeb = data.es_pedido_web;
    const webBadge = esWeb ? `<span class="venta-detalle-web-badge">🌐 Pedido Web</span>` : "";

    const direccionHtml = (esWeb && data.direccion_web)
      ? `<div class="venta-detalle-info-item">
          <span class="info-label">Dirección de entrega</span>
          <span class="info-value">${data.direccion_web}</span>
        </div>`
      : "";

    const notasHtml = (esWeb && data.notas_web)
      ? `<div class="venta-detalle-info-item venta-detalle-notas">
          <span class="info-label">Notas del pedido</span>
          <span class="info-value">${data.notas_web}</span>
        </div>`
      : "";

    cont.innerHTML = `
      <div class="venta-detalle-header-info">
        <div class="venta-detalle-logo">
          <img src="img/logosweet.png" alt="Sweetfit">
          ${webBadge}
        </div>
        <div class="venta-detalle-meta">
          <div class="venta-detalle-badge">#${data.orden ?? ""}</div>
          <span class="venta-detalle-tipo ${tipoClass}">${data.tipo_venta ?? ""}</span>
        </div>
      </div>

      <div class="venta-detalle-info-grid">
        <div class="venta-detalle-info-item">
          <span class="info-label">Fecha</span>
          <span class="info-value">${fecha}</span>
        </div>
        <div class="venta-detalle-info-item">
          <span class="info-label">Cliente</span>
          <span class="info-value">${data.cliente ?? ""}</span>
        </div>
        <div class="venta-detalle-info-item">
          <span class="info-label">Empleado</span>
          <span class="info-value">${data.empleado ?? ""}</span>
        </div>
        <div class="venta-detalle-info-item">
          <span class="info-label">Dirección</span>
          <span class="info-value">${data.direccion || "N/A"}</span>
        </div>
        ${esWeb ? `
        <div class="venta-detalle-info-item">
          <span class="info-label">Teléfono contacto</span>
          <span class="info-value">${data.telefono_web || "N/A"}</span>
        </div>
        ` : ""}
        ${direccionHtml}
        ${notasHtml}
      </div>

      <h4 class="venta-detalle-subtitulo">Productos</h4>
      <div class="venta-detalle-tabla-wrapper">
        <table class="venta-detalle-tabla">
          <thead><tr><th>Producto</th><th>Cant.</th><th>Precio</th><th>Subtotal</th></tr></thead>
          <tbody>${detalles}</tbody>
        </table>
      </div>

      <div class="venta-detalle-total">
        <span>Total</span>
        <span>$${total.toFixed(2)}</span>
      </div>
    `;

    modal.style.display = "flex";
  } catch (error) {
    console.error("Error al cargar detalle de venta:", error);
  }
}

function cerrarModalDetalleVenta() {
  const modal = document.getElementById("modalDetalleVenta");
  if (!modal) return;
  modal.style.display = "none";
}

function imprimirTicket() {
  window.print();
}

async function guardarEnEspera() {
  if (carrito.length === 0) {
    alert("Agregue productos al carrito");
    return;
  }

  const nombre = document.getElementById("nombreCliente")?.value.trim();
  const apellidoPaterno = document.getElementById("apellidoPaterno")?.value.trim();
  const apellidoMaterno = document.getElementById("apellidoMaterno")?.value.trim();
  const direccion = document.getElementById("direccionCliente")?.value.trim();
  const telefono = document.getElementById("telefonoCliente")?.value.trim();
  const tipoVentaRaw = document.getElementById("tipoVenta")?.value;
  const usuario = getUsuarioData();

  if (!tipoVentaRaw) {
    alert("Seleccione un tipo de venta");
    return;
  }

  const payload = {
    cliente: {
      nombre: nombre || "General",
      apellido_paterno: apellidoPaterno || "",
      apellido_materno: apellidoMaterno || "",
      direccion: direccion || "",
      telefono: telefono || ""
    },
    carrito: carrito.map(item => ({
      id: item.id,
      cantidad: item.cantidad,
      subtotal: item.precio * item.cantidad
    })),
    empleado: usuario ? `${usuario.nombre} ${usuario.apellidos || ''}`.trim() : "",
    tipo_venta: tipoVentaRaw,
    estado: "EN ESPERA"
  };

  const idVenta = window.ventaEnEdicion || null;
  const url = idVenta ? `/api/ventas/${idVenta}` : "/api/ventas";
  const method = idVenta ? "PUT" : "POST";

  try {
    await api(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    alert("Venta guardada en espera exitosamente");
    carrito = [];
    actualizarCarrito();
    window.ventaEnEdicion = null;
    cargarProductosParaVenta();
    cargarHistorialVentas();
  } catch (error) {
    console.error("Error al guardar venta en espera:", error);
    alert("Error al guardar en espera");
  }
}

async function cancelarVenta(idVenta) {
  if (!confirm(`¿Deseas cancelar la venta ${idVenta}?`)) return;

  try {
    await api(`/api/ventas/${idVenta}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estado: "CANCELADA" })
    });
    alert("Venta cancelada exitosamente");
    cargarHistorialVentas();
  } catch (err) {
    console.error("Error al cancelar venta:", err);
    alert("Error al cancelar la venta");
  }
}

async function aceptarVenta(idVenta) {
  if (!confirm(`¿Deseas aceptar y finalizar la venta ${idVenta}?`)) return;

  try {
    await api(`/api/ventas/${idVenta}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estado: "FINALIZADA" })
    });
    alert("Venta aceptada y finalizada exitosamente");
    cargarHistorialVentas();
  } catch (err) {
    console.error("Error al aceptar venta:", err);
    alert("Error al aceptar la venta");
  }
}
window.aceptarVenta = aceptarVenta;

async function cargarClientes() {
  try {
    const data = await api("/api/clientes");
    const select = document.getElementById("clienteVenta");
    if (select) {
      select.innerHTML = '<option value="">Seleccionar cliente</option>';
      data.forEach(cliente => {
        select.innerHTML += `<option value="${cliente.ID_CLIENTE}">${cliente.NOMBRE}</option>`;
      });
    }
  } catch (error) {
    console.error("Error al cargar clientes:", error);
  }
}

async function cargarEmpleados() {
  try {
    const data = await api("/empleados");
    const select = document.getElementById("selectEmpleadoVenta");
    if (select) {
      select.innerHTML = '<option value="">Seleccionar empleado</option>';
      data.forEach(emp => {
        select.innerHTML += `<option value="${emp.ID_EMPLEADO}">${emp.NOMBRE}</option>`;
      });
    }
  } catch (error) {
    console.error("Error al cargar empleados:", error);
  }
}

function agregarAlCarrito(id, nombre, precio, stock) {
  const existente = carrito.find(item => item.id === id);
  
  if (existente) {
    if (existente.cantidad < stock) {
      existente.cantidad++;
    } else {
      alert("No hay más stock disponible");
      return;
    }
  } else {
    carrito.push({ id, nombre, precio, cantidad: 1, stock });
  }
  
  actualizarCarrito();
}

function actualizarCarrito() {
  const tbody = document.querySelector("#tablaCarrito tbody");
  if (tbody) {
    tbody.innerHTML = "";
    carrito.forEach(item => {
      const row = tbody.insertRow();
      row.innerHTML = `
        <td>${item.nombre}</td>
        <td>
          <input type="number" value="${item.cantidad}" min="1" max="${item.stock}" 
                 onchange="actualizarCantidad(${item.id}, this.value)">
        </td>
        <td>$${item.precio.toFixed(2)}</td>
        <td>$${(item.precio * item.cantidad).toFixed(2)}</td>
        <td><button onclick="eliminarDelCarrito(${item.id})">Eliminar</button></td>
      `;
    });
  }
  
  const total = carrito.reduce((sum, item) => sum + (item.precio * item.cantidad), 0);
  const totalElement = document.getElementById("totalVenta");
  if (totalElement) {
    totalElement.textContent = `${total.toFixed(2)}`;
  }
}

function actualizarCantidad(id, nuevaCantidad) {
  const item = carrito.find(item => item.id === id);
  if (item) {
    const cantidad = parseInt(nuevaCantidad);
    if (cantidad >= 1 && cantidad <= item.stock) {
      item.cantidad = cantidad;
      actualizarCarrito();
    } else {
      alert("Cantidad inválida");
      actualizarCarrito();
    }
  }
}

function eliminarDelCarrito(id) {
  carrito = carrito.filter(item => item.id !== id);
  actualizarCarrito();
}

async function registrarVenta() {
  if (carrito.length === 0) {
    alert("Agregue productos al carrito");
    return;
  }

  const nombre = document.getElementById("nombreCliente")?.value.trim();
  const apellidoPaterno = document.getElementById("apellidoPaterno")?.value.trim();
  const apellidoMaterno = document.getElementById("apellidoMaterno")?.value.trim();
  const direccion = document.getElementById("direccionCliente")?.value.trim();
  const telefono = document.getElementById("telefonoCliente")?.value.trim();
  const tipoVentaRaw = document.getElementById("tipoVenta")?.value;
  const usuario = getUsuarioData();

  if (!tipoVentaRaw) {
    alert("Seleccione un tipo de venta");
    return;
  }

  const payload = {
    cliente: {
      nombre: nombre || "General",
      apellido_paterno: apellidoPaterno || "",
      apellido_materno: apellidoMaterno || "",
      direccion: direccion || "",
      telefono: telefono || ""
    },
    carrito: carrito.map(item => ({
      id: item.id,
      cantidad: item.cantidad,
      subtotal: item.precio * item.cantidad
    })),
    empleado: usuario ? `${usuario.nombre} ${usuario.apellidos || ''}`.trim() : "",
    tipo_venta: tipoVentaRaw,
    estado: "FINALIZADA"
  };

  const idVenta = window.ventaEnEdicion || null;
  const url = idVenta ? `/api/ventas/${idVenta}` : "/api/ventas";
  const method = idVenta ? "PUT" : "POST";

  try {
    await api(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    alert("Venta registrada exitosamente");
    limpiarFormularioVenta();
    cargarProductosParaVenta();
    window.ventaEnEdicion = null;
    cargarHistorialVentas();
  } catch (error) {
    console.error("Error al registrar venta:", error);
    alert("Error al registrar la venta");
  }
}

function formatoEstado(estado) {
  if (!estado) return estado;
  const est = estado.toUpperCase();
  switch(est) {
    case 'FINALIZADA': return `<span class="estado-finalizada">${estado}</span>`;
    case 'EN ESPERA': return `<span class="estado-en-espera">${estado}</span>`;
    case 'CANCELADA': return `<span class="estado-cancelada">${estado}</span>`;
    default: return `<span>${estado}</span>`;
  }
}

async function cargarVentaParaEdicion(idVenta) {
  try {
    const data = await api(`/api/ventas/${idVenta}`);
    if (!data) return;

    const elNombre = document.getElementById("nombreCliente");
    if (elNombre && data.cliente) {
      const partes = data.cliente.split(" ");
      elNombre.value = partes[0] || "";
      const ap = document.getElementById("apellidoPaterno");
      if (ap) ap.value = partes.slice(1, 3).join(" ") || "";
    }

    const elDir = document.getElementById("direccionCliente");
    if (elDir) elDir.value = data.direccion || "";

    const elTel = document.getElementById("telefonoCliente");
    if (elTel) elTel.value = data.telefono || "";

    const elTipo = document.getElementById("tipoVenta");
    if (elTipo && data.tipo_venta) elTipo.value = data.tipo_venta;

    carrito = [];
    (data.detallesV || []).forEach(prod => {
      carrito.push({
        id: prod.ID_PRODUCTO,
        nombre: prod.PRODUCTO,
        precio: parseFloat(prod.PRECIO_UNITARIO),
        cantidad: parseInt(prod.CANTIDAD_VENTA),
        stock: 9999
      });
    });

    actualizarCarrito();
    window.ventaEnEdicion = idVenta;
    alert("Venta cargada en espera. Puedes continuarla y finalizarla.");
  } catch (error) {
    console.error("Error al cargar venta para edición:", error);
  }
}

function autocompletarEmpleado() {
  const usuario = getUsuarioData();
  if (!usuario) return;

  const empleadoInput = document.getElementById("empleado");
  if (empleadoInput) {
    empleadoInput.value = `${usuario.nombre} ${usuario.apellidos || ''}`.trim();
  }
}

function activarAutocompleteCliente() {
  const inputNombre = document.getElementById('nombreCliente');
  if (!inputNombre) return;

  const listaSugerencias = document.createElement('ul');
  listaSugerencias.style.position = 'absolute';
  listaSugerencias.style.backgroundColor = '#fff';
  listaSugerencias.style.listStyle = 'none';
  listaSugerencias.style.padding = '0';
  listaSugerencias.style.margin = '0';
  listaSugerencias.style.maxHeight = '150px';
  listaSugerencias.style.overflowY = 'auto';
  listaSugerencias.style.width = inputNombre.offsetWidth + 'px';
  listaSugerencias.style.zIndex = '1000';
  listaSugerencias.style.border = '1px solid #ccc';
  inputNombre.parentNode.appendChild(listaSugerencias);

  inputNombre.addEventListener('input', async () => {
    const valor = inputNombre.value.trim();
    if (valor.length < 2) {
      listaSugerencias.innerHTML = '';
      return;
    }

    try {
      const clientes = await api(`/api/clientes`);
      listaSugerencias.innerHTML = '';
      const matches = clientes.filter(c => c.NOMBRE.toLowerCase().includes(valor.toLowerCase()));
      matches.forEach(cliente => {
        const li = document.createElement('li');
        li.style.padding = '8px';
        li.style.cursor = 'pointer';
        li.style.borderBottom = '1px solid #eee';
        li.textContent = `${cliente.NOMBRE} ${cliente.APELLIDO_PATERNO || ''} ${cliente.APELLIDO_MATERNO || ''}`.trim();
        li.addEventListener('mouseover', () => li.style.backgroundColor = '#f0f0f0');
        li.addEventListener('mouseout', () => li.style.backgroundColor = '#fff');
        li.addEventListener('click', () => {
          inputNombre.value = cliente.NOMBRE;
          const apPaterno = document.getElementById('apellidoPaterno');
          const apMaterno = document.getElementById('apellidoMaterno');
          const dirInput = document.getElementById('direccionCliente');
          const telInput = document.getElementById('telefonoCliente');
          if (apPaterno) apPaterno.value = cliente.APELLIDO_PATERNO || '';
          if (apMaterno) apMaterno.value = cliente.APELLIDO_MATERNO || '';
          if (dirInput) dirInput.value = cliente.DIRECCION || '';
          if (telInput) telInput.value = cliente.TELEFONO || '';
          listaSugerencias.innerHTML = '';
        });
        listaSugerencias.appendChild(li);
      });
    } catch (err) {
      console.error('Error buscando clientes:', err);
    }
  });

  document.addEventListener('click', e => {
    if (!inputNombre.contains(e.target) && !listaSugerencias.contains(e.target)) {
      listaSugerencias.innerHTML = '';
    }
  });
}

function limpiarFormularioVenta() {
  const nombreCliente = document.getElementById("nombreCliente");
  const apellidoPaterno = document.getElementById("apellidoPaterno");
  const apellidoMaterno = document.getElementById("apellidoMaterno");
  const direccionCliente = document.getElementById("direccionCliente");
  const telefonoCliente = document.getElementById("telefonoCliente");
  const clienteVenta = document.getElementById("clienteVenta");

  if (nombreCliente) nombreCliente.value = "";
  if (apellidoPaterno) apellidoPaterno.value = "";
  if (apellidoMaterno) apellidoMaterno.value = "";
  if (direccionCliente) direccionCliente.value = "";
  if (telefonoCliente) telefonoCliente.value = "";
  if (clienteVenta) clienteVenta.value = "";

  carrito = [];
  actualizarCarrito();
}
window.limpiarFormularioVenta = limpiarFormularioVenta;
