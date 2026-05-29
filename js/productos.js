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
  const btnCancelar = document.getElementById("btnCancelarModal");
  const form = document.getElementById("formAgregarProducto");
  const uploadArea = document.getElementById("imageUploadArea");
  const fileInput = document.getElementById("imagen");

  const abrirModal = () => {
    modal.style.display = "flex";
    document.body.classList.add("modal-abierto");
    resetearModal();
  };

  if (btnAbrir && modal) {
    if (getPuestoUsuario() !== 'Administrador') {
      btnAbrir.style.display = 'none';
    } else {
      btnAbrir.addEventListener("click", abrirModal);
    }
  }

  const cerrarModal = () => {
    modal.style.display = "none";
    document.body.classList.remove("modal-abierto");
    resetearModal();
  };

  if (btnCerrar && modal) {
    btnCerrar.addEventListener("click", cerrarModal);
  }

  if (btnCancelar) {
    btnCancelar.addEventListener("click", cerrarModal);
  }

  if (uploadArea && fileInput) {
    uploadArea.addEventListener("click", (e) => {
      if (e.target === fileInput) return;
      fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          const preview = document.getElementById("previewImagen");
          const placeholder = uploadArea.querySelector(".image-upload-placeholder");
          preview.src = ev.target.result;
          preview.style.display = "block";
          if (placeholder) placeholder.style.display = "none";
          uploadArea.classList.add("has-image");
        };
        reader.readAsDataURL(file);
      }
    });
  }

  if (form) {
    form.addEventListener("submit", guardarProducto);
  }

  window.addEventListener("click", (e) => {
    if (e.target === modal) cerrarModal();
  });
}

function resetearModal() {
  const form = document.getElementById("formAgregarProducto");
  const preview = document.getElementById("previewImagen");
  const uploadArea = document.getElementById("imageUploadArea");
  const placeholder = uploadArea?.querySelector(".image-upload-placeholder");
  const titulo = document.getElementById("tituloModal");
  const btnGuardar = document.getElementById("btnGuardarProducto");

  if (form) form.reset();
  if (preview) {
    preview.src = "";
    preview.style.display = "none";
  }
  if (placeholder) placeholder.style.display = "flex";
  if (uploadArea) uploadArea.classList.remove("has-image");
  if (titulo) titulo.textContent = "Agregar nuevo producto";
  if (btnGuardar) {
    btnGuardar.querySelector("span").textContent = "Guardar producto";
    btnGuardar.disabled = false;
  }
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
  const btnGuardar = document.getElementById("btnGuardarProducto");
  const spanBtn = btnGuardar?.querySelector("span");

  const url = id
    ? `${API}/api/editar_producto/${id}`
    : `${API}/api/productos`;

  const method = "POST";
  if (id) {
    formData.append("_method", "PUT");
  }

  if (btnGuardar) {
    btnGuardar.disabled = true;
    if (spanBtn) spanBtn.textContent = "Guardando...";
  }

  try {
    const response = await fetch(url, { method, body: formData });
    if (response.ok) {
      mostrarNotificacion("Producto guardado exitosamente", "success");
      const modal = document.getElementById("modalAgregarProducto");
      if (modal) {
        modal.style.display = "none";
        document.body.classList.remove("modal-abierto");
      }
      cargarProductos(categoriaActual, paginaActual);
    } else {
      const errData = await response.json().catch(() => ({}));
      mostrarNotificacion(errData.error || "Error al guardar producto", "error");
    }
  } catch (error) {
    console.error("Error al guardar producto:", error);
    mostrarNotificacion("Error de conexión al guardar producto", "error");
  } finally {
    if (btnGuardar) {
      btnGuardar.disabled = false;
      if (spanBtn) spanBtn.textContent = id ? "Guardar cambios" : "Guardar producto";
    }
  }
}

async function editarProducto(id) {
  try {
    const prod = await api(`/api/editar_producto/${id}`);
    const modal = document.getElementById("modalAgregarProducto");
    const form = document.getElementById("formAgregarProducto");
    const preview = document.getElementById("previewImagen");
    const titulo = document.getElementById("tituloModal");
    const btnGuardar = document.getElementById("btnGuardarProducto");
    const uploadArea = document.getElementById("imageUploadArea");
    const placeholder = uploadArea?.querySelector(".image-upload-placeholder");

    if (!prod || !form) return;

    if (titulo) titulo.textContent = "Editar producto";
    if (btnGuardar) btnGuardar.querySelector("span").textContent = "Guardar cambios";

    form.nombre.value = prod.nombre || '';
    form.descripcion.value = prod.descripcion || '';
    form.precio.value = prod.precio || '';
    form.cantidad.value = prod.cantidad || '';
    form.categoria.value = prod.categoria || '';
    document.getElementById("productoId").value = prod.ID_PRODUCTO || id;
    
    if (preview && uploadArea) {
      if (prod.imagen) {
        preview.src = `${API}/uploads/${prod.imagen}`;
        preview.style.display = 'block';
        if (placeholder) placeholder.style.display = 'none';
        uploadArea.classList.add("has-image");
      } else {
        preview.style.display = 'none';
        if (placeholder) placeholder.style.display = 'flex';
        uploadArea.classList.remove("has-image");
      }
    }

    if (modal) {
      modal.style.display = "flex";
      document.body.classList.add("modal-abierto");
    }
  } catch (err) {
    console.error("Error al cargar producto:", err);
    mostrarNotificacion("Error al cargar producto para edición.", "error");
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
    mostrarNotificacion("Producto eliminado", "success");
    cargarProductos(categoriaActual, paginaActual);
  } catch (error) {
    console.error("Error al eliminar producto:", error);
    mostrarNotificacion("Error al eliminar producto", "error");
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

// ==========================================
// Sistema de notificaciones
// ==========================================
function mostrarNotificacion(mensaje, tipo = "success") {
  const container = document.getElementById("notificacionContainer") || (() => {
    const c = document.createElement("div");
    c.id = "notificacionContainer";
    document.body.appendChild(c);
    return c;
  })();

  const notif = document.createElement("div");
  notif.className = `notificacion notificacion-${tipo}`;
  notif.innerHTML = `
    <span>${mensaje}</span>
    <button class="notificacion-cerrar">&times;</button>
  `;

  notif.querySelector(".notificacion-cerrar").addEventListener("click", () => {
    notif.remove();
  });

  container.appendChild(notif);

  setTimeout(() => {
    notif.classList.add("notificacion-salida");
    setTimeout(() => notif.remove(), 300);
  }, 3500);
}
