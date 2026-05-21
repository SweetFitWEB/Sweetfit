document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("formExtranetLogin");
  const errorMsg = document.getElementById("loginError");

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorMsg.style.display = "none";
      
      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;

      try {
        const response = await fetch(`${API}/api/extranet/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
          throw new Error("Login fallido");
        }

        const data = await response.json();
        
        // Guardar sesión del proveedor
        localStorage.setItem("proveedor_session", JSON.stringify(data.proveedor));
        
        // Redirigir al portal
        window.location.href = "extranet.html";
      } catch (err) {
        errorMsg.style.display = "block";
        console.error("Error en login:", err);
      }
    });
  }
});
