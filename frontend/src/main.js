const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const resultSummaryEl = document.getElementById("result-summary");
const ratesEl = document.getElementById("rates");
const btnExtract = document.getElementById("btn-extract");
const btnMuestras = document.getElementById("btn-muestras");
const btnReport = document.getElementById("btn-report");
const btnClear = document.getElementById("btn-clear");
const inputFiles = document.getElementById("input-files");
const inputFolder = document.getElementById("input-folder");
const uploadSummary = document.getElementById("upload-summary");
const selectExtractor = document.getElementById("select-extractor");

/** @type {File[]} */
let selectedDocs = [];
let backendOk = false;

function esDocumento(file) {
  const nombre = (file.name || "").toLowerCase();
  return (
    nombre.endsWith(".pdf") ||
    nombre.endsWith(".txt") ||
    file.type === "application/pdf" ||
    file.type === "text/plain"
  );
}

function actualizarSeleccion(files) {
  selectedDocs = Array.from(files).filter(esDocumento);
  if (!selectedDocs.length) {
    uploadSummary.textContent = "Ningún PDF/TXT válido en la selección.";
  } else if (selectedDocs.length === 1) {
    uploadSummary.textContent = `1 archivo: ${selectedDocs[0].name}`;
  } else {
    uploadSummary.textContent = `${selectedDocs.length} archivos listos.`;
  }
  actualizarBoton();
}

function actualizarBoton() {
  btnExtract.disabled = !(backendOk && selectedDocs.length > 0);
}

function detalleError(data) {
  if (!data) return "Error desconocido";
  if (Array.isArray(data.detail)) {
    return data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return data.detail || data.error || JSON.stringify(data);
}

function etiquetaEstado(estado) {
  if (estado === "exito") return "Éxito";
  if (estado === "parcial") return "Parcial";
  if (estado === "fallido") return "Fallido";
  return estado || "?";
}

function pintarRates(data) {
  ratesEl.hidden = false;
  ratesEl.innerHTML = `
    <div class="rate-card exito"><span>Éxito</span><strong>${data.exitosos ?? 0}</strong><small>${data.tasa_exito ?? 0}%</small></div>
    <div class="rate-card parcial"><span>Parcial</span><strong>${data.parciales ?? 0}</strong><small>${data.tasa_parcial ?? 0}%</small></div>
    <div class="rate-card fallido"><span>Fallido</span><strong>${data.fallidos ?? 0}</strong><small>${data.tasa_fallo ?? 0}%</small></div>
    <div class="rate-card total"><span>Total</span><strong>${data.total ?? 0}</strong><small>modelo ${data.modelo || ""}</small></div>
  `;
}

function pintarResumen(data) {
  const resultados = data.resultados || data.reporte?.resultados || [];
  resultSummaryEl.hidden = false;
  resultSummaryEl.innerHTML = "";

  for (const r of resultados) {
    const estado = r.estado || (r.ok ? "exito" : "fallido");
    const item = document.createElement("article");
    item.className = `result-item ${estado}`;
    const titulo = document.createElement("strong");
    titulo.textContent = `${etiquetaEstado(estado)} · ${r.archivo}`;
    item.appendChild(titulo);
    if (r.error) {
      const msg = document.createElement("p");
      msg.textContent = r.error;
      item.appendChild(msg);
    }
    if (r.errores_validacion?.length) {
      const ul = document.createElement("ul");
      for (const e of r.errores_validacion) {
        const li = document.createElement("li");
        li.textContent = `${e.campo}: ${e.motivo}`;
        ul.appendChild(li);
      }
      item.appendChild(ul);
    }
    if (r.datos && Object.keys(r.datos).length) {
      const pre = document.createElement("pre");
      pre.className = "mini-json";
      pre.textContent = JSON.stringify(r.datos, null, 2);
      item.appendChild(pre);
    }
    resultSummaryEl.appendChild(item);
  }
}

function mostrarLote(data) {
  outputEl.textContent = JSON.stringify(data, null, 2);
  pintarRates(data);
  pintarResumen(data);
  const fallidos = data.fallidos ?? 0;
  const parciales = data.parciales ?? 0;
  if (fallidos || parciales) {
    statusEl.textContent =
      `Lote listo · éxito ${data.tasa_exito}% · parcial ${data.tasa_parcial}% · fallo ${data.tasa_fallo}%`;
    statusEl.className = "status error";
  } else {
    statusEl.textContent = `Lote listo · ${data.total} documento(s) con éxito total`;
    statusEl.className = "status ok";
  }
}

async function cargarExtractores() {
  try {
    const res = await fetch("/api/extractors");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    selectExtractor.innerHTML = "";
    for (const clave of data.disponibles || []) {
      const opt = document.createElement("option");
      opt.value = clave;
      opt.textContent = clave;
      if (clave === data.activo) opt.selected = true;
      selectExtractor.appendChild(opt);
    }
    selectExtractor.disabled = false;
  } catch {
    selectExtractor.innerHTML = '<option value="">No disponible</option>';
    selectExtractor.disabled = true;
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    const ollama = data.ollama || {};
    if (data.status === "ok") {
      statusEl.textContent =
        `Listo · modelo ${data.modelo} · extractor ${data.extractor} · Ollama OK`;
      statusEl.className = "status ok";
      backendOk = true;
    } else if (data.status === "degraded") {
      statusEl.textContent =
        `Backend up · Ollama: ${ollama.error || "modelo no disponible"}`;
      statusEl.className = "status error";
      backendOk = false;
    } else {
      statusEl.textContent =
        `Backend up · Ollama inaccesible: ${ollama.error || "error"}`;
      statusEl.className = "status error";
      backendOk = false;
    }
    btnMuestras.disabled = !backendOk;
    btnReport.disabled = false;
    btnClear.disabled = false;
  } catch {
    statusEl.textContent =
      "No se pudo conectar con el backend en http://127.0.0.1:8000";
    statusEl.className = "status error";
    backendOk = false;
    btnMuestras.disabled = true;
    btnReport.disabled = true;
    btnClear.disabled = true;
  }
  actualizarBoton();
}

inputFiles.addEventListener("change", () => {
  if (inputFiles.files?.length) {
    inputFolder.value = "";
    actualizarSeleccion(inputFiles.files);
  }
});

inputFolder.addEventListener("change", () => {
  if (inputFolder.files?.length) {
    inputFiles.value = "";
    actualizarSeleccion(inputFolder.files);
  }
});

btnExtract.addEventListener("click", async () => {
  if (!selectedDocs.length) {
    statusEl.textContent = "Selecciona al menos un PDF/TXT o una carpeta.";
    statusEl.className = "status error";
    return;
  }

  btnExtract.disabled = true;
  statusEl.textContent = `Extrayendo ${selectedDocs.length} archivo(s)…`;
  statusEl.className = "status";
  outputEl.textContent = "Procesando…";
  resultSummaryEl.hidden = true;
  ratesEl.hidden = true;

  const form = new FormData();
  for (const file of selectedDocs) {
    form.append("files", file, file.name);
  }
  if (selectExtractor.value) {
    form.append("extractor", selectExtractor.value);
  }

  try {
    const res = await fetch("/api/extract", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(detalleError(data) || `HTTP ${res.status}`);
    mostrarLote(data);
  } catch (err) {
    outputEl.textContent = String(err.message || err);
    resultSummaryEl.hidden = true;
    ratesEl.hidden = true;
    statusEl.textContent = "Error durante la extracción";
    statusEl.className = "status error";
  } finally {
    actualizarBoton();
  }
});

btnMuestras.addEventListener("click", async () => {
  btnMuestras.disabled = true;
  statusEl.textContent = "Procesando muestras académicas (docs/muestras)…";
  statusEl.className = "status";
  outputEl.textContent = "Procesando…";
  resultSummaryEl.hidden = true;
  ratesEl.hidden = true;

  const qs = selectExtractor.value
    ? `?extractor=${encodeURIComponent(selectExtractor.value)}`
    : "";
  try {
    const res = await fetch(`/api/extract/muestras${qs}`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(detalleError(data) || `HTTP ${res.status}`);
    mostrarLote(data);
  } catch (err) {
    outputEl.textContent = String(err.message || err);
    statusEl.textContent = "Error al procesar muestras";
    statusEl.className = "status error";
  } finally {
    btnMuestras.disabled = !backendOk;
  }
});

btnReport.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/report");
    const data = await res.json();
    if (!res.ok) throw new Error(detalleError(data) || `HTTP ${res.status}`);
    mostrarLote({
      ...data,
      ...data.resumen,
      resultados: data.resultados,
      reporte: data,
    });
    statusEl.textContent = "Último reporte cargado";
    statusEl.className = "status ok";
  } catch (err) {
    statusEl.textContent = String(err.message || err);
    statusEl.className = "status error";
  }
});

btnClear.addEventListener("click", async () => {
  if (!confirm("¿Vaciar la carpeta output/ en el servidor?")) return;
  btnClear.disabled = true;
  try {
    const res = await fetch("/api/results", { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(detalleError(data));
    statusEl.textContent = `Resultados limpiados · ${data.eliminados ?? 0} archivo(s)`;
    statusEl.className = "status ok";
    resultSummaryEl.hidden = true;
    ratesEl.hidden = true;
    outputEl.textContent = "Aún no hay resultados.";
  } catch (err) {
    statusEl.textContent = String(err.message || err);
    statusEl.className = "status error";
  } finally {
    btnClear.disabled = false;
  }
});

cargarExtractores();
checkHealth();
