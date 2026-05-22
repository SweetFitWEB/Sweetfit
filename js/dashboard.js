// Dashboard específico
// El DOMContentLoaded ya no es necesario porque main.js llama a cargarDashboard()


async function cargarDashboard() {
  try {
    const data = await api("/api/dashboard");
    
    // Actualizar tarjetas del dashboard
    const ventasDia = document.getElementById("ventas-dia");
    const clientesCount = document.getElementById("clientes-registrados");
    const productosCount = document.getElementById("inventario");
    const ultimaCompra = document.getElementById("ultima-compra");
    
    if (ventasDia) ventasDia.textContent = `$${parseFloat(data.ventas_dia).toFixed(2)}`;
    if (clientesCount) clientesCount.textContent = data.clientes_registrados;
    if (productosCount) productosCount.textContent = data.productos_disponibles;
    if (ultimaCompra) ultimaCompra.textContent = data.ultima_compra || 'Sin registro';
    
    // Cargar gráfico de ventas
    cargarGraficoVentas();
    
    // Cargar cierre de caja
    cargarCierreCaja();
    
  } catch (error) {
    console.error("Error al cargar dashboard:", error);
  }
}

async function cargarCierreCaja() {
  try {
    const data = await api("/api/cierre-caja");
    
    const ventasCount = document.getElementById("cc-ventas-count");
    const ingresos = document.getElementById("cc-ingresos");
    const pendientes = document.getElementById("cc-pendientes");
    
    if (ventasCount) ventasCount.textContent = data.total_ventas;
    if (ingresos) ingresos.textContent = `$${parseFloat(data.total_ingresos).toFixed(2)}`;
    if (pendientes) pendientes.textContent = data.pedidos_pendientes;
    
    // Desglose por tipo
    const desglose = document.getElementById("cc-desglose");
    if (desglose && data.desglose_por_tipo) {
      desglose.innerHTML = data.desglose_por_tipo.map(t => `
        <div class="card">
          <h3>${t.TIPO_VENTA}</h3>
          <p>${t.cantidad} ventas - $${parseFloat(t.total).toFixed(2)}</p>
        </div>
      `).join('');
    }
    
    // Productos más vendidos
    const masVendidos = document.getElementById("cc-mas-vendidos");
    if (masVendidos && data.productos_mas_vendidos) {
      if (data.productos_mas_vendidos.length === 0) {
        masVendidos.innerHTML = '<tr><td colspan="2" style="padding: 8px; text-align: center; color: #999;">Sin ventas hoy</td></tr>';
      } else {
        masVendidos.innerHTML = data.productos_mas_vendidos.map(p => `
          <tr>
            <td style="padding: 8px;">${p.NOMBRE}</td>
            <td style="padding: 8px; text-align: right;">${p.vendido}</td>
          </tr>
        `).join('');
      }
    }
    
  } catch (error) {
    console.error("Error al cargar cierre de caja:", error);
  }
}

async function cargarGraficoVentas() {
  const canvas = document.getElementById("ventasChart");
  if (!canvas || typeof Chart === 'undefined') return;
  
  const ctx = canvas.getContext('2d');
  
  if (window.ventasChart && typeof window.ventasChart.destroy === 'function') {
    window.ventasChart.destroy();
  }
  
  let labels = [], data = [];
  try {
    const res = await api("/api/reportes/ventas?tipo=semanal");
    if (res?.ventas) {
      labels = res.ventas.map(v => {
        const d = new Date(v.fecha);
        return d.toLocaleDateString('es', { weekday: 'short', day: 'numeric' });
      });
      data = res.ventas.map(v => parseFloat(v.total_ventas) || 0);
    }
  } catch (e) {
    console.warn("No se pudo cargar el gráfico", e);
  }
  
  window.ventasChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Ventas diarias',
        data: data,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.1
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return '$' + value.toFixed(2);
            }
          }
        }
      }
    }
  });
}
