document.getElementById("btnAplicar").addEventListener("click", cargarReporte);

async function cargarReporte() {
    const tipo = document.getElementById("tipoReporte").value;
    const inicio = document.getElementById("fechaInicio").value;
    const fin = document.getElementById("fechaFin").value;

    if (tipo !== "Arbol") {
        alert("Solo está habilitado el reporte de Árboles.");
        return;
    }

    const url = `/api/reportes?tipo=${tipo}&fechaInicio=${inicio}&fechaFin=${fin}`;

    const respuesta = await fetch(url);
    const datos = await respuesta.json();

    if (!datos.tabla || datos.tabla.length === 0) {
        document.getElementById("tablaResultados").innerHTML = "<p>No hay datos para mostrar.</p>";
        return;
    }

    mostrarTablaArboles(datos.tabla);

    // ← ← GENERAMOS LAS DOS GRÁFICAS
    generarGraficas(datos.tabla);
}


function mostrarTablaArboles(registros) {
    const columnas = [
        "ID_ARBOL",
        "NOMBRE_CIENTIFICO",
        "NOMBRE_COMUN",
        "ALTURA",
        "DIAMETRO",
        "DANO",
        "FORMAFUSTE",
        "OBSERVACIONES",
        "NSUBPARCELA",
        "NRO_DOCUMENTO",
        "ID_RESERVA",
        "FECHA_REGISTRO"
    ];

    let html = "<table><thead><tr>";

    columnas.forEach(col => {
        html += `<th>${col}</th>`;
    });

    html += "</tr></thead><tbody>";

    registros.forEach(row => {
        html += "<tr>";
        columnas.forEach(col => {
            html += `<td>${row[col] ?? ""}</td>`;
        });
        html += "</tr>";
    });

    html += "</tbody></table>";

    document.getElementById("tablaResultados").innerHTML = html;
}

let graficoDanio = null;
let graficoFuste = null;

function generarGraficas(registros) {
    generarGraficaDanio(registros);
    generarGraficaFuste(registros);
}

/* -------------------------
   📌 GRÁFICA: TIPOS DE DAÑO
   ------------------------- */
function generarGraficaDanio(registros) {
    const conteo = {};

    registros.forEach(r => {
        const d = r.DANO || "SIN DATO";
        conteo[d] = (conteo[d] || 0) + 1;
    });

    const labels = Object.keys(conteo);
    const valores = Object.values(conteo);

    if (graficoDanio) graficoDanio.destroy();

    graficoDanio = new Chart(document.getElementById("graficoDanio"), {
        type: "pie",
        data: {
            labels: labels,
            datasets: [
                {
                    data: valores
                }
            ]
        },
        options: {
            responsive: true
        }
    });
}

/* ----------------------------
   📌 GRÁFICA: FORMA DEL FUSTE
   ---------------------------- */
function generarGraficaFuste(registros) {
    const conteo = {};

    registros.forEach(r => {
        const f = r.FORMAFUSTE || "SIN DATO";
        conteo[f] = (conteo[f] || 0) + 1;
    });

    const labels = Object.keys(conteo);
    const valores = Object.values(conteo);

    if (graficoFuste) graficoFuste.destroy();

    graficoFuste = new Chart(document.getElementById("graficoFuste"), {
        type: "pie",
        data: {
            labels: labels,
            datasets: [
                {
                    data: valores
                }
            ]
        },
        options: {
            responsive: true
        }
    });
}
