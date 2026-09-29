const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const resultSummaryEl = document.getElementById("result-summary");
const btnExtract = document.getElementById("btn-extract");
const btnClear = document.getElementById("btn-clear");
const inputFiles = document.getElementById("input-files");
const inputFolder = document.getElementById("input-folder");
const uploadSummary = document.getElementById("upload-summary");
const selectExtractor = document.getElementById("select-extractor");

/** @type {File[]} */
let selectedPdfs = [];
let backendOk = false;

function esPdf(file) {
  const nombre = (file.name || "").toLowerCase();
  return nombre.endsWith(".pdf") || file.type === "application/pdf";
}

function actualizarSeleccion(files) {
  selectedPdfs = Array.from(files).filter(esPdf);
  if (!selectedPdfs.length) {
    uploadSummary.textContent = "Ningún PDF válido en la selección.";
  } else if (selectedPdfs.length === 1) {
    uploadSummary.textContent = `1 archivo: ${selectedPdfs[0].name}`;
  } else {
    uploadSummary.textContent = `${selectedPdfs.length} archivos PDF listos.`;
  }
  actualizarBoton();
}

function actualizarBoton() {
  btnExtract.disabled = !(backendOk && selectedPdfs.length > 0);
}

function detalleError(data) {
  if (!data) return "Error desconocido";
  if (Array.isArray(data.detail)) {
    return data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return data.detail || data.error || JSON.stringify(data);
}

function pintarResumen(data) {
  const fallidos = (data.resultados || []).filter((r) => r.ok === false);
  const exitosos = data.exitosos ?? (data.total || 0) - fallidos.length;
  resultSummaryEl.hidden = false;
  resultSummaryEl.innerHTML = "";

  const meta = document.createElement("p");
  meta.className = "summary-meta";
  meta.textContent = `Total ${data.total} · OK ${exitosos} · Fallidos ${fallidos.length} · modelo ${data.modelo}`;
  resultSummaryEl.appendChild(meta);

  for (const r of data.resultados || []) {
    const item = document.createElement("article");
    item.className = r.ok ? "result-item ok" : "result-item fail";
    const titulo = document.createElement("strong");
    titulo.textContent = `${r.ok ? "OK" : "Error"} · ${r.archivo}`;
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
    resultSummaryEl.appendChild(item);
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
      btnClear.disabled = false;
    } else if (data.status === "degraded") {
      statusEl.textContent =
        `Backend up · Ollama: ${ollama.error || "modelo no disponible"}`;
      statusEl.className = "status error";
      backendOk = false;
      btnClear.disabled = false;
    } else {
      statusEl.textContent =
        `Backend up · Ollama inaccesible: ${ollama.error || "error"}`;
      statusEl.className = "status error";
      backendOk = false;
      btnClear.disabled = false;
    }
  } catch {
    statusEl.textContent =
      "No se pudo conectar con el backend en http://127.0.0.1:8000";
    statusEl.className = "status error";
    backendOk = false;
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
  if (!selectedPdfs.length) {
    statusEl.textContent = "Selecciona al menos un PDF o una carpeta.";
    statusEl.className = "status error";
    return;
  }

  btnExtract.disabled = true;
  statusEl.textContent = `Extrayendo ${selectedPdfs.length} archivo(s)… puede tardar varios minutos.`;
  statusEl.className = "status";
  outputEl.textContent = "Procesando…";
  resultSummaryEl.hidden = true;

  const form = new FormData();
  for (const file of selectedPdfs) {
    form.append("files", file, file.name);
  }
  if (selectExtractor.value) {
    form.append("extractor", selectExtractor.value);
  }

  try {
    const res = await fetch("/api/extract", {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(detalleError(data) || `HTTP ${res.status}`);

    outputEl.textContent = JSON.stringify(data, null, 2);
    pintarResumen(data);

    const fallidos = (data.resultados || []).filter((r) => r.ok === false);
    if (fallidos.length) {
      statusEl.textContent =
        `Procesado con avisos · ${data.total} archivo(s), ${fallidos.length} con error`;
      statusEl.className = "status error";
    } else {
      statusEl.textContent = `Listo · ${data.total} archivo(s) procesado(s)`;
      statusEl.className = "status ok";
    }
  } catch (err) {
    outputEl.textContent = String(err.message || err);
    resultSummaryEl.hidden = true;
    statusEl.textContent = "Error durante la extracción";
    statusEl.className = "status error";
  } finally {
    actualizarBoton();
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
