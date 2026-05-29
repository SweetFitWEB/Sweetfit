// Reportes específico
function initReportesPage() {
  const contenedor = document.getElementById("reportesContenido");
  if (!contenedor) return;

  if (!window.__reportesInit) {
    window.__reportesInit = true;
    inicializarSelectoresFecha();
    inicializarReportes();
    inicializarExportacionReportes();
  }
}

window.initReportesPage = initReportesPage;

document.addEventListener("DOMContentLoaded", () => {
  initReportesPage();
});

document.addEventListener("reportes:loaded", () => {
  initReportesPage();
});

function inicializarSelectoresFecha() {
  const hoy = new Date();
  const dateIso = hoy.toISOString().split("T")[0]; // YYYY-MM-DD
  const anio = hoy.getFullYear();
  let mes = hoy.getMonth() + 1;
  mes = mes < 10 ? '0' + mes : mes;

  const fechaDia = document.getElementById("fechaDia");
  const fechaSemana = document.getElementById("fechaSemana");
  const fechaMes = document.getElementById("fechaMes");
  const tipoReporte = document.getElementById("tipoReporte");

  if (fechaDia) fechaDia.value = dateIso;
  
  if (fechaSemana) {
    const d = new Date(Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
    const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1)/7);
    fechaSemana.value = `${anio}-W${weekNo < 10 ? '0'+weekNo : weekNo}`;
  }

  if (fechaMes) fechaMes.value = `${anio}-${mes < 10 ? '0'+mes : mes}`;

  if (tipoReporte) {
    tipoReporte.addEventListener("change", (e) => {
      const tipo = e.target.value;
      if(fechaDia) fechaDia.style.display = tipo === 'diario' ? 'inline-block' : 'none';
      if(fechaSemana) fechaSemana.style.display = tipo === 'semanal' ? 'inline-block' : 'none';
      if(fechaMes) fechaMes.style.display = tipo === 'mensual' ? 'inline-block' : 'none';
      document.getElementById("tituloTipoReporte").textContent = tipo.charAt(0).toUpperCase() + tipo.slice(1);
      
      generarReporteVentas(tipo);
    });
    
    // Trigger event to set initial visibility
    tipoReporte.dispatchEvent(new Event("change"));
  }

  if (fechaDia) fechaDia.addEventListener("change", () => generarReporteVentas('diario'));
  if (fechaSemana) fechaSemana.addEventListener("change", () => generarReporteVentas('semanal'));
  if (fechaMes) fechaMes.addEventListener("change", () => generarReporteVentas('mensual'));
}

function inicializarReportes() {
  // Configurar botones de generación de reportes no es necesario aquí, lo unimos a los selects.
  generarReporteCategorias();
}

async function generarReporteCategorias() {
  try {
    const data = await api("/api/reportes/categorias");
    mostrarGraficoCategorias(data);
  } catch (error) {
    console.error("Error al generar reporte de categorias:", error);
  }
}

function mostrarGraficoCategorias(data) {
  const canvas = document.getElementById("graficaCategorias");
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (window.categoriasChart) window.categoriasChart.destroy();
  const items = data.categorias || data || [];
  
  window.categoriasChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: items.map(i => i.CATEGORIA),
      datasets: [{
        data: items.map(i => i.total_cantidad_vendida),
        backgroundColor: ['#f56954', '#00a65a', '#f39c12', '#00c0ef', '#3c8dbc']
      }]
    },
    options: { responsive: true }
  });
}

function inicializarExportacionReportes() {
  const btnDescargarCSV = document.getElementById("btnDescargarCSV");
  const btnDescargarPDF = document.getElementById("btnDescargarPDF");

  if (btnDescargarCSV) {
    btnDescargarCSV.addEventListener("click", () => descargarReporteGlobal('csv'));
  }
  if (btnDescargarPDF) {
    btnDescargarPDF.addEventListener("click", () => descargarReporteGlobal('pdf'));
  }
}

async function generarReporteVentas(tipo) {
  let fecha = '';
  if (tipo === 'diario') fecha = document.getElementById("fechaDia")?.value;
  if (tipo === 'semanal') fecha = document.getElementById("fechaSemana")?.value;
  if (tipo === 'mensual') fecha = document.getElementById("fechaMes")?.value;
  
  try {
    const data = await obtenerDatosVentas(tipo, fecha);
    mostrarGraficoVentas(data, tipo);
    mostrarTablaVentas(data, tipo);
  } catch (error) {
    console.error("Error al generar reporte de ventas:", error);
  }
}

async function obtenerDatosVentas(tipo, fecha) {
  let url = `/api/reportes/ventas?tipo=${tipo}`;
  if (fecha) url += `&fecha=${encodeURIComponent(fecha)}`;

  return await api(url);
}

function mostrarGraficoVentas(data, tipo) {
  const canvas = document.getElementById("graficaVentas");
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  
  if (window.ventasChart) {
    window.ventasChart.destroy();
  }

  const items = data.ventas || data || [];

  window.ventasChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: items.map(item => item.fecha || item.label),
      datasets: [{
        label: `Ventas ${tipo}`,
        data: items.map(item => item.total_ventas || item.total),
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
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

function mostrarTablaVentas(data, tipo) {
  const tabla = document.getElementById("tablaVentas");
  if (!tabla) return;

  const tbody = tabla.querySelector('tbody') || tabla.createTBody();
  tbody.innerHTML = '';

  const items = data.ventas || data || [];
  items.forEach(item => {
    const row = tbody.insertRow();
    row.innerHTML = `
      <td>${item.fecha || item.label}</td>
      <td>$${parseFloat(item.total_ventas || item.total || 0).toFixed(2)}</td>
      <td>${item.total_ventas ? '' : (item.cantidad || 0)}</td>
    `;
  });
}

async function generarReporteProductos() {
  try {
    const data = await api("/api/reportes/productos-mas-vendidos");
    mostrarTablaProductos(data);
  } catch (error) {
    console.error("Error al generar reporte de productos:", error);
    alert("Error al generar el reporte");
  }
}

function mostrarTablaProductos(data) {
  const tabla = document.getElementById("tablaProductos");
  if (!tabla) return;

  const tbody = tabla.querySelector('tbody') || tabla.createTBody();
  tbody.innerHTML = '';

  data.forEach(producto => {
    const row = tbody.insertRow();
    row.innerHTML = `
      <td>${producto.nombre}</td>
      <td>${producto.total_vendido}</td>
      <td>$${parseFloat(producto.total_ingresos).toFixed(2)}</td>
    `;
  });
}

async function descargarReporteGlobal(formato) {
  const tipo = document.getElementById("tipoReporte")?.value || 'diario';
  let fecha = '';

  if (tipo === 'diario') fecha = document.getElementById("fechaDia")?.value;
  else if (tipo === 'semanal') fecha = document.getElementById("fechaSemana")?.value;
  else if (tipo === 'mensual') fecha = document.getElementById("fechaMes")?.value;

  if (!fecha) {
    alert("Por favor seleccione una fecha válida para el reporte.");
    return;
  }

  try {
    const data = await api(`/api/reportes/detalles?tipo=${tipo}&fecha=${encodeURIComponent(fecha)}`);
    if (formato === 'csv') exportarCSV(data);
    else if (formato === 'pdf') exportarPDF(data);
  } catch (err) {
    console.error("Error al descargar el reporte:", err);
    alert("Hubo un problema obteniendo los datos del reporte.");
  }
}

function formatearFecha(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return isoStr;
  const meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
  return `${d.getDate()} de ${meses[d.getMonth()]} de ${d.getFullYear()}`;
}

function exportarCSV(data) {
  const { ventas, compras, totalVentas, totalCompras } = data;
  const fechaHoy = new Date().toLocaleDateString("es-MX", {
    year: "numeric", month: "long", day: "numeric"
  });

  let csv = "";
  csv += "SWEETFIT\n";
  csv += "Reporte Detallado de Ventas y Compras\n";
  csv += `Fecha de generacion: ${fechaHoy}\n`;
  csv += "\n";

  // Ventas
  csv += "===========================\n";
  csv += "SECCION: VENTAS\n";
  csv += "===========================\n";
  csv += "Tipo,Fecha,Producto,Categoria,Cantidad,Precio Unitario,Subtotal\n";
  (ventas || []).forEach(v => {
    csv += `Venta,${formatearFecha(v.FECHA_VENTA)},${v.producto},${v.CATEGORIA},${v.CANTIDAD_VENTA},${Number(v.PRECIO).toFixed(2)},${Number(v.SUBTOTAL_VENTA).toFixed(2)}\n`;
  });

  // Compras
  csv += "\n";
  csv += "===========================\n";
  csv += "SECCION: COMPRAS A PROVEEDORES\n";
  csv += "===========================\n";
  csv += "Tipo,Fecha,Proveedor,Producto,Cantidad,Subtotal\n";
  (compras || []).forEach(c => {
    csv += `Compra,${formatearFecha(c.FECHA_COMPRA)},${c.proveedor},${c.producto},${c.CANTIDAD_COMPRA},${Number(c.SUBTOTAL_COMPRA).toFixed(2)}\n`;
  });

  // Totales
  csv += "\n";
  csv += "===========================\n";
  csv += "TOTALES\n";
  csv += "===========================\n";
  csv += `Total Ventas,,,$${Number(totalVentas || 0).toFixed(2)}\n`;
  csv += `Total Compras,,,$${Number(totalCompras || 0).toFixed(2)}\n`;

  // Convertir a Blob y descargar
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = `reporte_sweetfit.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function convertirImagenABase64(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "Anonymous";
    img.onload = function () {
      const canvas = document.createElement("canvas");
      canvas.width = this.width;
      canvas.height = this.height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(this, 0, 0);
      const dataURL = canvas.toDataURL("image/png");
      resolve(dataURL);
    };
    img.onerror = reject;
    img.src = url;
  });
}

async function exportarPDF(data) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF("p", "mm", "a4");

  const pageWidth = doc.internal.pageSize.getWidth();
  let y = 20; // Posición inicial en Y

  // Título
  doc.setFont("helvetica", "bold");
  doc.setFontSize(20);
  doc.text("SWEETFIT", pageWidth / 2, y, { align: "center" });
  y += 10;

  doc.setFontSize(14);
  doc.text("Reporte Detallado de Ventas y Compras", pageWidth / 2, y, { align: "center" });
  y += 10;

  const fechaHoy = new Date().toLocaleDateString("es-MX", { year: "numeric", month: "long", day: "numeric" });
  doc.setFontSize(12);
  doc.setFont("helvetica", "normal");
  doc.text(`Fecha de generación: ${fechaHoy}`, pageWidth / 2, y, { align: "center" });
  y += 15;

  // ==== SECCIÓN VENTAS ====
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text("VENTAS", 14, y);
  y += 5;

  const headVentas = [["Fecha", "Producto", "Cat.", "Cant.", "Precio U.", "Subtotal"]];
  const bodyVentas = (data.ventas || []).map(v => [
    formatearFecha(v.FECHA_VENTA),
    v.producto,
    v.CATEGORIA,
    v.CANTIDAD_VENTA,
    `$${Number(v.PRECIO).toFixed(2)}`,
    `$${Number(v.SUBTOTAL_VENTA).toFixed(2)}`
  ]);

  doc.autoTable({
    startY: y,
    head: headVentas,
    body: bodyVentas,
    theme: "striped",
    styles: { fontSize: 10 },
    headStyles: { fillColor: [41, 128, 185] },
  });

  y = doc.lastAutoTable.finalY + 15;

  // ==== SECCIÓN COMPRAS ====
  doc.text("COMPRAS A PROVEEDORES", 14, y);
  y += 5;

  const headCompras = [["Fecha", "Proveedor", "Producto", "Cant.", "Subtotal"]];
  const bodyCompras = (data.compras || []).map(c => [
    formatearFecha(c.FECHA_COMPRA),
    c.proveedor,
    c.producto,
    c.CANTIDAD_COMPRA,
    `$${Number(c.SUBTOTAL_COMPRA).toFixed(2)}`
  ]);

  doc.autoTable({
    startY: y,
    head: headCompras,
    body: bodyCompras,
    theme: "striped",
    styles: { fontSize: 10 },
    headStyles: { fillColor: [192, 57, 43] },
  });

  y = doc.lastAutoTable.finalY + 15;

  // Línea separadora
  doc.setDrawColor(150);
  doc.line(14, y, pageWidth - 14, y);
  y += 10;

  // ==== RESUMEN ====
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text("RESUMEN TOTAL", 14, y);
  y += 10;

  doc.setFontSize(12);
  doc.setFont("helvetica", "normal");
  doc.text(`Total en Ventas: $${Number(data.totalVentas || 0).toFixed(2)}`, 14, y);
  y += 8;
  doc.text(`Total en Compras: $${Number(data.totalCompras || 0).toFixed(2)}`, 14, y);

  doc.save("Reporte_Sweetfit.pdf");
}
