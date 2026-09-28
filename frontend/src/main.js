const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const btnExtract = document.getElementById("btn-extract");
const inputFiles = document.getElementById("input-files");
const inputFolder = document.getElementById("input-folder");
const uploadSummary = document.getElementById("upload-summary");

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

async function checkHealth() {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    statusEl.textContent = `Backend OK · modelo ${data.modelo} · extractor ${data.extractor}`;
    statusEl.className = "status ok";
    backendOk = true;
  } catch {
    statusEl.textContent =
      "No se pudo conectar con el backend en http://127.0.0.1:8000";
    statusEl.className = "status error";
    backendOk = false;
  }
  actualizarBoton();
}

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

  const form = new FormData();
  for (const file of selectedPdfs) {
    form.append("files", file, file.name);
  }

  try {
    const res = await fetch("/api/extract", {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
        : data.detail;
      throw new Error(detail || `HTTP ${res.status}`);
    }
    outputEl.textContent = JSON.stringify(data, null, 2);
    statusEl.textContent = `Listo · ${data.total} archivo(s) procesado(s)`;
    statusEl.className = "status ok";
  } catch (err) {
    outputEl.textContent = String(err.message || err);
    statusEl.textContent = "Error durante la extracción";
    statusEl.className = "status error";
  } finally {
    actualizarBoton();
  }
});

checkHealth();
