// Login específico
document.addEventListener("DOMContentLoaded", () => {
  if (!document.body.classList.contains("pagina-login")) return;

  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const formData = new FormData(loginForm);
      const email = formData.get("email");
      const password = formData.get("contraseña");

      try {
        // Debug: Verificar que la función api existe
        if (typeof api !== 'function') {
          throw new Error("La función api no está disponible. Verifica que api.js se cargue correctamente.");
        }

        console.log("Intentando login con:", { email, password: "***" });
        
        const data = await api("/api/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email, contraseña: password }),
        });

        console.log("Respuesta del servidor:", data);
        
        localStorage.setItem("usuario", JSON.stringify(data));
        window.location.href = "index.html";
      } catch (error) {
        console.error("Error de login detallado:", error);
        alert(`Error: ${error.message}`);
      }
    });
  }
});

function initLogin() {
  // Función placeholder para compatibilidad
}
