// Script principal - solo para funcionalidades globales
document.addEventListener("DOMContentLoaded", () => {
  // Verificar autenticación en todas las páginas excepto login
  if (!document.body.classList.contains("pagina-login")) {
    const usuario = getUsuarioData();
    if (!usuario) {
      window.location.href = "login.html";
      return;
    }

    // Actualizar label de usuario
    const userLabel = document.getElementById("userLabel");
    if (userLabel && usuario?.puesto) {
      userLabel.textContent = usuario.puesto;
    }

    // Configurar dropdown de usuario
    configurarDropdownUsuario();
  }

  // Configurar animación de sidebar solo en páginas que lo tengan
  if (document.getElementById("toggleSidebar")) {
    configurarSidebar();
  }

  // Configurar navegación del menú
  configurarNavegacionMenu();

  // Cargar última página visitada o el panel por defecto
  const lastPage = localStorage.getItem('lastPage') || 'panel.html';
  const lastText = localStorage.getItem('lastText') || 'Panel';
  loadPage(lastPage, lastText);
});

function configurarSidebar() {
  const toggleSidebar = document.getElementById("toggleSidebar");
  if (toggleSidebar) {
    toggleSidebar.addEventListener("click", () => {
      const sidebar = document.getElementById("sidebar");
      if (sidebar) {
        sidebar.classList.toggle("collapsed");
      }
    });
  }
}

function configurarNavegacionMenu() {
  const links = document.querySelectorAll(".menu a");
  links.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const page = link.getAttribute("data-page");
      const text = link.querySelector(".text")?.textContent || "";
      loadPage(page, text);
    });
  });
}

function configurarDropdownUsuario() {
  const userButton = document.getElementById("userButton");
  const dropdownMenu = document.getElementById("dropdownMenu");
  const logoutButton = document.getElementById("logoutButton");

  if (userButton && dropdownMenu) {
    userButton.addEventListener("click", () => {
      dropdownMenu.style.display = dropdownMenu.style.display === "block" ? "none" : "block";
    });

    window.addEventListener("click", function (e) {
      if (!userButton.contains(e.target) && !dropdownMenu.contains(e.target)) {
        dropdownMenu.style.display = "none";
      }
    });
  }

  if (logoutButton) {
    logoutButton.addEventListener("click", () => {
      localStorage.removeItem("usuario");
      window.location.href = "login.html";
    });
  }
}

// Función global para cargar páginas dinámicamente (solo para index.html)
function loadPage(page, text) {
  const usuario = getUsuarioData();
  const puesto = usuario?.puesto;

  // Guardar en localStorage
  localStorage.setItem('lastPage', page);
  localStorage.setItem('lastText', text);

  const permitidoCajero = ["panel.html", "ventas.html", "productos.html"];
  if (puesto === "Cajero" && !permitidoCajero.includes(page)) {
    const contentArea = document.getElementById("content-area");
    if (contentArea) {
      contentArea.innerHTML = "<p>No tienes acceso a esta sección.</p>";
    }
    return;
  }

  const viewUrl = `views/${page}`;
  console.log("DEBUG: loadPage() ->", { page, viewUrl });

  fetch(viewUrl)
    .then(res => {
      if (!res.ok) {
        throw new Error(`No se pudo cargar la vista: ${viewUrl} (HTTP ${res.status})`);
      }
      return res.text();
    })
    .then(html => {
      const contentArea = document.getElementById("content-area");
      const title = document.getElementById("titulo-vista");
      
      if (contentArea) contentArea.innerHTML = html;
      if (title) title.textContent = text;

      const initByPage = {
        "productos.html": { init: "initProductosPage", event: "productos:loaded" },
        "ventas.html": { init: "initVentasPage", event: "ventas:loaded" },
        "cliente.html": { init: "initClientesPage", event: "clientes:loaded" },
        "proveedor.html": { init: "initProveedoresPage", event: "proveedor:loaded" },
        "reportes.html": { init: "initReportesPage", event: "reportes:loaded" },
        "configuracion.html": { init: "initConfiguracionPage", event: "configuracion:loaded" },
      };

      const target = initByPage[page];
      if (target) {
        const initFn = window[target.init];
        if (typeof initFn === "function") {
          initFn();
        }

        document.dispatchEvent(new Event(target.event));

        setTimeout(() => {
          const retryFn = window[target.init];
          if (typeof retryFn === "function") {
            retryFn();
          }
        }, 50);
      }

      // Agregar clase al body para identificar la página
      document.body.className = document.body.className.replace(/pagina-\w+/g, '');
      document.body.classList.add(`pagina-${page.replace('.html', '')}`);

      // Inicializar scripts específicos de la página
      if (page === "panel.html") {
        cargarDashboard();
      }
    })
    .catch(error => {
      console.error("Error al cargar la página:", error);
      const contentArea = document.getElementById("content-area");
      if (contentArea) {
        contentArea.innerHTML = `<p>Error al cargar la página: ${error.message}</p>`;
      }
    });
}
