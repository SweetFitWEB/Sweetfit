// Configuración centralizada de la API
const API = window.location.origin;

// Helper function para hacer peticiones a la API
async function api(endpoint, options = {}) {
  const usuario = getUsuarioData();
  if (usuario) {
    options.headers = options.headers || {};
    options.headers['X-User-Role'] = usuario.puesto;
    options.headers['X-User-Id'] = usuario.id;
  }
  const res = await fetch(`${API}${endpoint}`, options);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

// Helper para validar localStorage
function getUsuarioData() {
  try {
    const data = JSON.parse(localStorage.getItem("usuario"));
    return data?.usuario || null;
  } catch (error) {
    console.error("Error al leer localStorage:", error);
    return null;
  }
}

// Helper para verificar si el usuario está autenticado
function isAutenticado() {
  const usuario = getUsuarioData();
  return !!usuario;
}

// Helper para obtener el puesto del usuario
function getPuestoUsuario() {
  const usuario = getUsuarioData();
  return usuario?.puesto || null;
}
