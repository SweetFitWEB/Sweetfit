// Configuración específica
function initConfiguracionPage() {
  const tabla = document.getElementById("empleadosTable");
  const form = document.getElementById("altaEmpleadoForm");
  if (!tabla && !form) return;

  if (!window.__configuracionInit) {
    window.__configuracionInit = true;
    configurarFormularioEmpleado();
  }

  cargarEmpleados();
}

window.initConfiguracionPage = initConfiguracionPage;

document.addEventListener("DOMContentLoaded", () => {
  initConfiguracionPage();
});

document.addEventListener("configuracion:loaded", () => {
  initConfiguracionPage();
});

async function cargarEmpleados() {
  try {
    const data = await api("/empleados");
    mostrarEmpleados(data);
  } catch (error) {
    console.error("Error al cargar empleados:", error);
  }
}

function mostrarEmpleados(empleados) {
  const tbody = document.getElementById("empleadosTable");
  if (!tbody) return;

  tbody.innerHTML = "";

  empleados.forEach(emp => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${emp.NOMBRE}</td>
      <td>${emp.APELLIDOS}</td>
      <td>${emp.EMAIL}</td>
      <td>${emp.PUESTO}</td>
      <td>
        <div class="acciones">
          <button class="btn-editar" onclick="editarEmpleado(${emp.ID_EMPLEADO})">Editar</button>
          <button class="btn-eliminar" onclick="eliminarEmpleado(${emp.ID_EMPLEADO})">Eliminar</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function configurarFormularioEmpleado() {
  const form = document.getElementById("altaEmpleadoForm");
  if (form) {
    form.addEventListener("submit", guardarEmpleado);
  }
}

let idEditando = null;

async function guardarEmpleado(e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  
  const empleadoData = {
    nombre: formData.get("nombre"),
    apellidos: formData.get("apellidos"),
    email: formData.get("email"),
    puesto: formData.get("puesto")
  };

  const password = formData.get("password");
  if (password) {
    empleadoData.password = password;
  }

  const url = idEditando ? `/empleados/${idEditando}` : "/empleados";
  const method = idEditando ? "PUT" : "POST";

  try {
    await api(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(empleadoData)
    });

    alert("Empleado guardado exitosamente");
    e.target.reset();
    idEditando = null;
    cargarEmpleados();
  } catch (error) {
    console.error("Error al guardar empleado:", error);
  }
}

async function editarEmpleado(id) {
  try {
    const empleados = await api("/empleados");
    const emp = empleados.find(e => e.ID_EMPLEADO === id);
    if (!emp) return;
    
    idEditando = id;
    const form = document.getElementById("altaEmpleadoForm");
    if (form) {
      if (form.nombre) form.nombre.value = emp.NOMBRE || "";
      if (form.apellidos) form.apellidos.value = emp.APELLIDOS || "";
      if (form.email) form.email.value = emp.EMAIL || "";
      if (form.puesto) form.puesto.value = emp.PUESTO || "";
      if (form.password) form.password.value = ""; // Opcional para cambiar
      
      const btn = form.querySelector("button[type='submit']");
      if (btn) btn.textContent = "Guardar Cambios";
    }
  } catch (error) {
    console.error("Error al cargar empleado para edición:", error);
  }
}

async function eliminarEmpleado(id) {
  if (!confirm("¿Estás seguro de eliminar este empleado?")) return;

  try {
    await api(`/empleados/${id}`, { method: "DELETE" });
    alert("Empleado eliminado exitosamente");
    cargarEmpleados();
  } catch (error) {
    console.error("Error al eliminar empleado:", error);
  }
}
