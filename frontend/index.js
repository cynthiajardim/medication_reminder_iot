const API_URL = "https://considerate-compassion-production-2ff2.up.railway.app";

// redireciona para login se não houver token
const token = sessionStorage.getItem("token");
if (!token) window.location.href = "login.html";

function authHeaders() {
	return { Authorization: `Bearer ${token}` };
}

function logout() {
	sessionStorage.removeItem("token");
	window.location.href = "login.html";
}

let todosRegistros = [];
let registrosFiltrados = [];
let pagina = 1;
const porPagina = 10;
let graficoInstance = null;

// calendário
let calAno = new Date().getFullYear();
let calMes = new Date().getMonth();

function setStatus(msg, tipo) {
	document.getElementById("dot").className = "dot " + (tipo || "loading");
	document.getElementById("status-msg").textContent = msg;
}

async function carregar() {
	const base = API_URL.trim().replace(/\/$/, "");
	setStatus("Carregando...", "loading");

	try {
		const [resumoRes, registrosRes] = await Promise.all([
			fetch(`${base}/resumo`, { headers: authHeaders() }),
			fetch(`${base}/registros`, { headers: authHeaders() }),
		]);

		if (resumoRes.status === 401 || registrosRes.status === 401) {
			logout();
			return;
		}

		if (!resumoRes.ok || !registrosRes.ok) throw new Error("Erro na API");

		const resumo = await resumoRes.json();
		const registros = await registrosRes.json();

		todosRegistros = registros;
		registrosFiltrados = registros;
		pagina = 1;

		preencherCards(resumo);
		renderizarGrafico(registros);
		renderizarTabela();

		document.getElementById("ultima-atualizacao").textContent =
			"Atualizado: " + new Date().toLocaleString("pt-BR");

		setStatus("Dados carregados com sucesso", "ok");
	} catch (e) {
		setStatus("Erro ao conectar na API: " + e.message, "err");
	}
}

function preencherCards(resumo) {
	const tomados = resumo.total_tomados || 0;
	const naoTomados = resumo.total_nao_tomados || 0;
	const total = tomados + naoTomados;
	const taxa = total > 0 ? Math.round((tomados / total) * 100) : 0;

	document.getElementById("total-verde").textContent = tomados;
	document.getElementById("total-vermelho").textContent = naoTomados;
	document.getElementById("total-geral").textContent = total;
	document.getElementById("taxa").textContent = taxa + "%";
}

function renderizarGrafico(registros) {
	const porDia = {};
	registros.forEach((r) => {
		const data = (r.timestamp || r.recebido || "").substring(0, 10);
		if (!data) return;
		if (!porDia[data]) porDia[data] = { tomados: 0, nao: 0 };
		if (r.cor === "verde") porDia[data].tomados++;
		else porDia[data].nao++;
	});

	const labels = Object.keys(porDia).sort();
	const tomados = labels.map((d) => porDia[d].tomados);
	const nao = labels.map((d) => porDia[d].nao);

	if (graficoInstance) graficoInstance.destroy();

	graficoInstance = new Chart(
		document.getElementById("grafico").getContext("2d"),
		{
			type: "bar",
			data: {
				labels,
				datasets: [
					{ label: "Tomado", data: tomados, backgroundColor: "#2d7a45" },
					{ label: "Não tomado", data: nao, backgroundColor: "#b03030" },
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { labels: { font: { family: "IBM Plex Mono", size: 11 } } },
				},
				scales: {
					x: {
						stacked: true,
						ticks: { font: { family: "IBM Plex Mono", size: 10 } },
					},
					y: {
						stacked: true,
						ticks: { font: { family: "IBM Plex Mono", size: 10 }, stepSize: 1 },
					},
				},
			},
		},
	);
}

function renderizarTabela() {
	const wrap = document.getElementById("tabela-wrap");
	const total = registrosFiltrados.length;
	const pages = Math.ceil(total / porPagina) || 1;
	const inicio = (pagina - 1) * porPagina;
	const slice = registrosFiltrados.slice(inicio, inicio + porPagina);

	document.getElementById("pag-info").textContent = `pág ${pagina} de ${pages}`;
	document.getElementById("btn-prev").disabled = pagina <= 1;
	document.getElementById("btn-next").disabled = pagina >= pages;

	if (slice.length === 0) {
		wrap.innerHTML = '<div class="empty">Nenhum registro encontrado</div>';
		return;
	}

	let html = `<table>
    <thead><tr>
      <th>#</th>
      <th>Status</th>
      <th>Timestamp ESP32</th>
      <th>Recebido em</th>
    </tr></thead><tbody>`;

	slice.forEach((r) => {
		const badge =
			r.cor === "verde"
				? '<span class="badge verde">✓ Tomado</span>'
				: '<span class="badge vermelho">✗ Não tomado</span>';
		html += `<tr>
      <td>${r.id}</td>
      <td>${badge}</td>
      <td>${r.timestamp || "—"}</td>
      <td>${r.recebido || "—"}</td>
    </tr>`;
	});

	html += "</tbody></table>";
	wrap.innerHTML = html;
}

function mudarPagina(dir) {
	const pages = Math.ceil(registrosFiltrados.length / porPagina) || 1;
	pagina = Math.min(Math.max(pagina + dir, 1), pages);
	renderizarTabela();
}

function filtrarData() {
	const data = document.getElementById("filtro-data").value;
	registrosFiltrados = data
		? todosRegistros.filter((r) =>
				(r.timestamp || r.recebido || "").startsWith(data),
			)
		: todosRegistros;
	pagina = 1;
	renderizarTabela();
}

function limparFiltro() {
	document.getElementById("filtro-data").value = "";
	registrosFiltrados = todosRegistros;
	pagina = 1;
	renderizarTabela();
}

carregar();
