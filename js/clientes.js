// Clientes específico
function initClientesPage() {
  const tabla = document.getElementById("listaClientes");
  if (!tabla) return;

  if (!window.__clientesInit) {
    window.__clientesInit = true;
    initClienteModal();

    const buscadorClientes = document.getElementById("buscadorClientes");
    if (buscadorClientes && !buscadorClientes.dataset.listener) {
      buscadorClientes.dataset.listener = "1";
      buscadorClientes.addEventListener("input", () => {
        const texto = buscadorClientes.value.trim().toLowerCase();
        document.querySelectorAll(".cliente-card").forEach(card => {
          const nombre = card.querySelector("h3")?.textContent?.toLowerCase() || "";
          card.style.display = nombre.includes(texto) ? "block" : "none";
        });
      });
    }
  }

  cargarClientes();
}

window.initClientesPage = initClientesPage;

document.addEventListener("DOMContentLoaded", () => {
  initClientesPage();
});

document.addEventListener("clientes:loaded", () => {
  initClientesPage();
});

async function cargarClientes() {
  try {
    const data = await api("/api/clientes");
    const contenedor = document.getElementById("listaClientes");
    if (contenedor) {
      contenedor.innerHTML = "";
      data.forEach(cliente => {
        const div = document.createElement("div");
        div.className = "cliente-card";
        div.innerHTML = `
          <h3>${cliente.NOMBRE} ${cliente.APELLIDO_PATERNO || ''} ${cliente.APELLIDO_MATERNO || ''}</h3>
          <p><strong>Tel:</strong> ${cliente.TELEFONO || 'N/A'}</p>
          <p><strong>Dirección:</strong> ${cliente.DIRECCION || 'N/A'}</p>
          <div class="acciones-cliente">
            <button class="btn-editar" onclick="editarCliente(${cliente.ID_CLIENTE})">✏️</button>
            <button class="btn-eliminar" onclick="eliminarCliente(${cliente.ID_CLIENTE})">🗑️</button>
            <button class="btn-historial" onclick="mostrarHistorialCliente(${cliente.ID_CLIENTE})">📜 Historial</button>
          </div>
        `;
        contenedor.appendChild(div);
      });
    }
  } catch (error) {
    console.error("Error al cargar clientes:", error);
  }
}

async function guardarCliente(e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  const id = document.getElementById("clienteId")?.value;

  const clienteData = {
    nombre: formData.get("nombre"),
    apellido_paterno: formData.get("apellido_paterno"),
    apellido_materno: formData.get("apellido_materno"),
    telefono: formData.get("telefono"),
    direccion: formData.get("direccion")
  };

  const url = id ? `/api/clientes/${id}` : "/api/clientes";
  const method = id ? "PUT" : "POST";

  try {
    await api(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clienteData)
    });

    alert("Cliente guardado exitosamente");
    e.target.reset();
    cargarClientes();
  } catch (error) {
    console.error("Error al guardar cliente:", error);
    alert("Error al guardar el cliente");
  }
}

function initClienteModal() {
  const modal = document.getElementById("modalCliente");
  const cerrar = document.getElementById("cerrarModalCliente");
  const form = document.getElementById("formCliente");

  if (!modal || !cerrar || !form) {
    console.warn("⚠️ Elementos del modal de cliente no encontrados");
    return;
  }

  cerrar.addEventListener("click", () => {
    modal.style.display = "none";
  });

  window.addEventListener("click", e => {
    if (e.target === modal) modal.style.display = "none";
  });

  form.addEventListener("submit", guardarCliente);
}

function abrirModalCliente() {
  const modal = document.getElementById("modalCliente");
  const form = document.getElementById("formCliente");
  if (form) form.reset();
  const idField = document.getElementById("clienteId");
  if (idField) idField.value = "";
  if (modal) modal.style.display = "flex";
}

function cerrarModalCliente() {
  const modal = document.getElementById("modalCliente");
  if (modal) modal.style.display = "none";
}

async function editarCliente(id) {
  try {
    const clientes = await api("/api/clientes");
    const cliente = clientes.find(c => c.ID_CLIENTE == id);
    if (!cliente) return;
    
    const form = document.getElementById("formCliente");
    if (form) {
      form.nombre.value = cliente.NOMBRE || "";
      form.apellido_paterno.value = cliente.APELLIDO_PATERNO || "";
      form.apellido_materno.value = cliente.APELLIDO_MATERNO || "";
      form.telefono.value = cliente.TELEFONO || "";
      form.direccion.value = cliente.DIRECCION || "";
      const idField = document.getElementById("clienteId");
      if (idField) idField.value = cliente.ID_CLIENTE;
      
      const modal = document.getElementById("modalCliente");
      if (modal) modal.style.display = "flex";
    }
  } catch (error) {
    console.error("Error al cargar cliente para edición:", error);
  }
}

async function mostrarHistorialCliente(idCliente) {
  const panel = document.getElementById("historialPanel");
  const contenedor = document.getElementById("contenidoHistorial");

  if (!panel || !contenedor) return;
  contenedor.style.opacity = 0;

  setTimeout(async () => {
    contenedor.innerHTML = '';

    try {
      const historial = await api(`/api/clientes/${idCliente}/historial`);
      
      if (Array.isArray(historial) && historial.length > 0) {
        historial.forEach(venta => {
          const ventaDiv = document.createElement("div");
          ventaDiv.className = "venta-item";

          let tipoColor = "";
          let tipoIcono = "";
          switch (venta.TIPO_VENTA) {
            case "Local": tipoColor = "#4CAF50"; tipoIcono = "🏪"; break;
            case "Domicilio": tipoColor = "#2196F3"; tipoIcono = "🏠"; break;
            case "App": tipoColor = "#9C27B0"; tipoIcono = "📱"; break;
            default: tipoColor = "#999"; tipoIcono = "❓";
          }

          ventaDiv.innerHTML = `
            <p><strong>Fecha:</strong> ${new Date(venta.FECHA_VENTA).toLocaleDateString("es-MX", { day: "2-digit", month: "2-digit", year: "numeric" })}</p>
            <p><strong>Total:</strong> $${parseFloat(venta.TOTAL_VENTA).toFixed(2)}</p>
            <p><strong>Tipo:</strong> <span style="color:${tipoColor}; font-weight: bold;">${tipoIcono} ${venta.TIPO_VENTA}</span></p>
            <hr>
          `;

          contenedor.appendChild(ventaDiv);
        });

        contenedor.style.opacity = 1;
      } else {
        contenedor.innerHTML = `<p>No se encontraron ventas para este cliente.</p>`;
        contenedor.style.opacity = 1;
      }

      abrirHistorialCliente();
    } catch (err) {
      console.error("Error al cargar el historial:", err);
      contenedor.innerHTML = `<p>Error al cargar el historial.</p>`;
      contenedor.style.opacity = 1;
      abrirHistorialCliente();
    }
  }, 50);
}

function abrirHistorialCliente() {
  const panel = document.getElementById("historialPanel");
  if(panel) panel.style.right = "0";
}

function cerrarHistorialCliente() {
  const panel = document.getElementById("historialPanel");
  if(panel) panel.style.right = "-100%";
}

async function eliminarCliente(id) {
  if (!confirm("¿Estás seguro de eliminar este cliente?")) return;

  try {
    await api(`/api/clientes/${id}`, { method: "DELETE" });
    alert("Cliente eliminado");
    cargarClientes();
  } catch (error) {
    console.error("Error al eliminar cliente:", error);
  }
}
