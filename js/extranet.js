document.addEventListener("DOMContentLoaded", () => {
  // Verificar sesión
  const sessionData = localStorage.getItem("proveedor_session");
  if (!sessionData) {
    window.location.href = "extranet_login.html";
    return;
  }

  const proveedor = JSON.parse(sessionData);
  console.log("Sesion proveedor:", proveedor);
  document.getElementById("provNameLabel").textContent = `${proveedor.nombre} (ID: ${proveedor.id})`;

  // Logout
  document.getElementById("btnCerrarSesion").addEventListener("click", () => {
    localStorage.removeItem("proveedor_session");
    window.location.href = "extranet_login.html";
  });

  // Cargar catálogo
  cargarCatalogo(proveedor.id);

  // Modal
  const modal = document.getElementById("modalProductoExtranet");
  const btnCerrar = document.getElementById("cerrarModalExtranet");
  const btnAgregar = document.getElementById("btnAgregarProductoExtranet");
  const form = document.getElementById("formProductoExtranet");

  btnAgregar.addEventListener("click", () => {
    form.reset();
    document.getElementById("extranetProductoId").value = "";
    document.getElementById("tituloModalExtranet").textContent = "Proponer Nuevo Producto";
    document.getElementById("camposNuevoProducto").style.display = "block";
    modal.style.display = "flex";
  });

  btnCerrar.addEventListener("click", () => modal.style.display = "none");
  window.addEventListener("click", e => { if (e.target === modal) modal.style.display = "none"; });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const idProducto = document.getElementById("extranetProductoId").value;
    const isNew = !idProducto;
    
    let url = `/api/extranet/productos/${isNew ? proveedor.id : idProducto}`;
    let method = isNew ? "POST" : "PUT";
    
    // Si es PUT, enviamos todo como json igual
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData);
    
    try {
      await api(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      alert(isNew ? "Producto propuesto exitosamente. Pendiente de aprobación." : "Producto actualizado.");
      modal.style.display = "none";
      cargarCatalogo(proveedor.id);
    } catch (err) {
      console.error(err);
      alert("Error al guardar producto");
    }
  });
});

async function cargarCatalogo(idProveedor) {
  try {
    const data = await api(`/api/extranet/productos/${idProveedor}`);
    const grid = document.getElementById("gridCatalogo");
    grid.innerHTML = "";

    if (data.length === 0) {
      grid.innerHTML = `<div style="text-align:center; padding:40px; color:#666;">
        <p style="font-size:2rem;">📦</p>
        <p>No tienes productos vinculados a tu cuenta.</p>
        <p style="font-size:12px; color:#aaa;">Proveedor ID: ${idProveedor}. Usa el botón "Proponer Producto" para añadir uno.</p>
      </div>`;
      return;
    }

    data.forEach(prod => {
      const div = document.createElement("div");
      div.className = "card-producto";
      
      const estado = prod.ESTADO_APROBACION || 'APROBADO';
      const badgeClass = estado === 'APROBADO' ? 'badge-aprobado' : 
                         estado === 'EN_EDICION' ? 'badge-en-edicion' :
                         estado === 'RECHAZADO' ? 'badge-rechazado' : 'badge-pendiente';

      div.innerHTML = `
        <span class="badge-estado ${badgeClass}">${estado}</span>
        <h3>${prod.NOMBRE}</h3>
        <p style="font-size:12px">${prod.CATEGORIA}</p>
        <p class="card-precio">$${parseFloat(prod.PRECIO).toFixed(2)}</p>
        <div class="card-acciones">
          <button onclick="editarProductoExtranet(${prod.ID_PRODUCTO}, '${prod.NOMBRE}', ${prod.PRECIO})" title="Editar Precio">✏️</button>
          <button onclick="eliminarProductoExtranet(${prod.ID_PRODUCTO}, ${idProveedor})" title="Desvincular">🗑️</button>
        </div>
      `;
      grid.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

function editarProductoExtranet(id, nombre, precio) {
  const modal = document.getElementById("modalProductoExtranet");
  document.getElementById("extranetProductoId").value = id;
  document.getElementById("extranetNombre").value = nombre;
  document.getElementById("extranetPrecio").value = precio;
  document.getElementById("camposNuevoProducto").style.display = "none";
  document.getElementById("tituloModalExtranet").textContent = "Editar Producto";
  modal.style.display = "flex";
}

async function eliminarProductoExtranet(idProducto, idProveedor) {
  if (!confirm("¿Estás seguro de quitar este producto de tu catálogo?")) return;
  try {
    await api(`/api/extranet/productos/${idProducto}/${idProveedor}`, { method: 'DELETE' });
    cargarCatalogo(idProveedor);
  } catch (err) {
    alert("Error al eliminar");
  }
}
