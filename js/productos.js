// Productos específico
function initProductosPage() {
  console.log("DEBUG: Body classes:", document.body.className);

  const contenedor = document.getElementById("gridProductos");
  if (!contenedor) {
    console.log("DEBUG: initProductosPage() cancelado - no existe #gridProductos todavía");
    return;
  }

  initProductoModal();
  cargarCategorias();
  cargarProductos();

  const buscador = document.getElementById("buscador");
  if (buscador && !buscador.dataset.listener) {
    buscador.dataset.listener = "1";
    buscador.addEventListener("input", () => {
      const texto = buscador.value.trim().toLowerCase();
      cargarProductos(categoriaActual, 1, texto);
    });
  }
}

window.initProductosPage = initProductosPage;

document.addEventListener("DOMContentLoaded", () => {
  initProductosPage();
});

document.addEventListener("productos:loaded", () => {
  initProductosPage();
});

let categoriaActual = null;
let paginaActual = 1;

function initProductoModal() {
  const modal = document.getElementById("modalAgregarProducto");
  const btnAbrir = document.querySelector(".btn-agregar-producto");
  const btnCerrar = document.getElementById("cerrarModal");
  const form = document.getElementById("formAgregarProducto");

  if (btnAbrir && modal) {
    if (getPuestoUsuario() !== 'Administrador') {
      btnAbrir.style.display = 'none';
    } else {
      btnAbrir.addEventListener("click", () => modal.style.display = "block");
    }
  }

  if (btnCerrar && modal) {
    btnCerrar.addEventListener("click", () => modal.style.display = "none");
  }

  if (form) {
    form.addEventListener("submit", guardarProducto);
  }

  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });
}

async function cargarCategorias() {
  try {
    const data = await api("/api/categorias");
    const contenedor = document.getElementById("filtrosCategorias");
    if (!contenedor) return;

    contenedor.innerHTML = `<button class="filtro activo" data-cat="">Todo</button>`;

    (data || []).forEach((cat) => {
      // El backend original usaba cat.categoria, soportamos ambos por si acaso
      const nombreCat = cat.categoria || cat.nombre;
      if (!nombreCat) return;

      const btn = document.createElement("button");
      btn.className = "filtro";
      btn.textContent = nombreCat;
      btn.dataset.cat = nombreCat;
      contenedor.appendChild(btn);
    });

    const botones = contenedor.querySelectorAll(".filtro");
    botones.forEach(btn => {
      btn.addEventListener("click", () => {
        botones.forEach(b => b.classList.remove("activo"));
        btn.classList.add("activo");
        const cat = btn.dataset.cat === "" ? null : btn.dataset.cat;
        cargarProductos(cat, 1, document.getElementById("buscador")?.value?.trim()?.toLowerCase() || "");
      });
    });

  } catch (error) {
    console.error("Error al cargar categorías:", error);
  }
}

async function cargarProductos(categoria = null, pagina = 1, texto = "") {
  categoriaActual = categoria;
  paginaActual = pagina;

  let url = `/api/productos?page=${pagina}`;
  if (categoria) {
    url += `&categoria=${encodeURIComponent(categoria)}`;
  }
  if (texto) {
    url += `&nombre=${encodeURIComponent(texto)}`;
  }

  try {
    console.log("DEBUG: Cargando productos desde URL:", url);
    const data = await api(url);
    console.log("DEBUG: Respuesta del servidor:", data);
    const contenedor = document.getElementById("gridProductos");
    if (contenedor) {
      console.log("DEBUG: Cantidad de productos recibidos:", data.productos?.length || 0);
      contenedor.innerHTML = "";
      const esAdmin = getPuestoUsuario() === 'Administrador';
      (data.productos || []).forEach((prod) => {
        const card = document.createElement("div");
        card.className = "producto-card";
        card.innerHTML = `
          <img src="${API}/uploads/${prod.imagen}" alt="${prod.nombre}" />
          <h3>${prod.nombre}</h3>
          <p class="desc">${prod.descripcion}</p>
          <p class="cantidad ${prod.cantidad <= 5 ? "stock-bajo" : ""}">
            Stock: ${prod.cantidad}
          </p>
          <p class="precio">$${parseFloat(prod.precio).toFixed(2)}</p>
          <div class="acciones">
            <button class="btn-editar" onclick="editarProducto(${prod.id})" ${esAdmin ? '' : 'style="display:none"'}>Editar</button>
            <button class="btn-eliminar" onclick="eliminarProducto(${prod.id})" ${esAdmin ? '' : 'style="display:none"'}>Eliminar</button>
          </div>
        `;
        contenedor.appendChild(card);
      });
      
      renderPaginacion(data.total_paginas || 1, data.pagina_actual || 1, categoria, texto);
    }
  } catch (error) {
    console.error("Error al cargar productos:", error);
  }
}

async function guardarProducto(e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  const id = document.getElementById("productoId").value;

  const url = id
    ? `${API}/api/editar_producto/${id}`
    : `${API}/api/productos`;

  const method = "POST";
  if (id) {
    formData.append("_method", "PUT");
  }

  try {
    const response = await fetch(url, { method, body: formData });
    if (response.ok) {
      alert("Producto guardado");
      e.target.reset();
      const modal = document.getElementById("modalAgregarProducto");
      if (modal) modal.style.display = "none";
      cargarProductos(categoriaActual, paginaActual);
    }
  } catch (error) {
    console.error("Error al guardar producto:", error);
  }
}

async function editarProducto(id) {
  try {
    const prod = await api(`/api/editar_producto/${id}`);
    const modal = document.getElementById("modalAgregarProducto");
    const form = document.getElementById("formAgregarProducto");
    const preview = document.getElementById("previewImagen");
    const titulo = modal?.querySelector("h3");
    const botonSubmit = form?.querySelector("button[type='submit']");

    if (!prod || !form) return;

    if (titulo) titulo.textContent = "Editar producto";
    if (botonSubmit) botonSubmit.textContent = "Guardar cambios";

    form.nombre.value = prod.nombre || '';
    form.descripcion.value = prod.descripcion || '';
    form.precio.value = prod.precio || '';
    form.cantidad.value = prod.cantidad || '';
    form.categoria.value = prod.categoria || '';
    document.getElementById("productoId").value = prod.ID_PRODUCTO || id;
    
    if (preview) {
      if (prod.imagen) {
        preview.src = `${API}/uploads/${prod.imagen}`;
        preview.style.display = 'block';
      } else {
        preview.style.display = 'none';
      }
    }

    if (modal) modal.style.display = "flex";
  } catch (err) {
    console.error("Error al cargar producto:", err);
    alert("Error al cargar producto para edición.");
  }
}

function renderPaginacion(totalPaginas, paginaActual = 1, categoria = "", nombreFiltro = "") {
  const contenedor = document.getElementById("paginacionProductos");
  if (!contenedor) return;

  contenedor.innerHTML = "";

  for (let i = 1; i <= totalPaginas; i++) {
    const btn = document.createElement("button");
    btn.textContent = i;
    btn.classList.toggle("activo", i === paginaActual);
    btn.addEventListener("click", () => {
      cargarProductos(categoria, i, nombreFiltro);
    });
    contenedor.appendChild(btn);
  }
}

async function eliminarProducto(id) {
  if (!confirm("¿Estás seguro de eliminar este producto?")) return;

  try {
    await api(`/api/eliminar_producto/${id}`, { method: "DELETE" });
    alert("Producto eliminado");
    cargarProductos(categoriaActual, paginaActual);
  } catch (error) {
    console.error("Error al eliminar producto:", error);
  }
}

// ==========================================
// Lógica de Aprobaciones (Extranet)
// ==========================================
async function cargarAprobaciones() {
  const modal = document.getElementById("modalAprobaciones");
  const lista = document.getElementById("listaAprobaciones");
  
  if (!modal || !lista) return;
  
  try {
    const pendientes = await api("/api/productos/pendientes");
    lista.innerHTML = "";
    
    if (pendientes.length === 0) {
      lista.innerHTML = "<p>No hay productos pendientes de aprobación.</p>";
    } else {
      pendientes.forEach(prod => {
        const div = document.createElement("div");
        div.style.borderBottom = "1px solid #ccc";
        div.style.paddingBottom = "15px";
        div.style.marginBottom = "15px";
        
        div.innerHTML = `
          <h4>${prod.NOMBRE} <span style="font-size:12px; font-weight:normal; color:#666;">Propuesto por: ${prod.proveedor_nombre}</span></h4>
          <p style="margin:5px 0;"><strong>Cat:</strong> ${prod.CATEGORIA} | <strong>Precio:</strong> $${prod.PRECIO}</p>
          <div style="margin-top:10px;">
            <button onclick="procesarAprobacion(${prod.ID_PRODUCTO}, 'APROBADO')" style="background:#28a745; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;">Aprobar</button>
            <button onclick="procesarAprobacion(${prod.ID_PRODUCTO}, 'RECHAZADO')" style="background:#e74c3c; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;">Rechazar</button>
          </div>
        `;
        lista.appendChild(div);
      });
    }
    modal.style.display = "flex";
  } catch (err) {
    console.error("Error al cargar aprobaciones:", err);
    alert("Hubo un error cargando las aprobaciones.");
  }
}
window.cargarAprobaciones = cargarAprobaciones;

async function procesarAprobacion(idProducto, estado) {
  try {
    await api(`/api/productos/${idProducto}/aprobar`, {
      method: 'PUT',
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estado })
    });
    alert(`Producto ${estado.toLowerCase()}`);
    cargarAprobaciones();
    cargarProductos(categoriaActual, paginaActual);
  } catch (err) {
    console.error("Error al procesar aprobación:", err);
    alert("Hubo un problema al procesar la aprobación.");
  }
}
window.procesarAprobacion = procesarAprobacion;

// Ocultar botón de aprobaciones si no es admin
document.addEventListener("DOMContentLoaded", () => {
  const btnApr = document.getElementById('btnAprobaciones');
  if (btnApr && getPuestoUsuario() !== 'Administrador') {
    btnApr.style.display = 'none';
  }

  document.body.addEventListener('click', (e) => {
    if (e.target.id === 'btnAprobaciones' || e.target.closest('#btnAprobaciones')) {
      cargarAprobaciones();
    }
    if (e.target.id === 'cerrarModalAprobaciones') {
      document.getElementById("modalAprobaciones").style.display = "none";
    }
    if (e.target.id === 'modalAprobaciones') {
      document.getElementById("modalAprobaciones").style.display = "none";
    }
  });
});
