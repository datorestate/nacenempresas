/* Calculadoras de NacenEmpresas. Cifras orientativas; ver fecha de revisión en cada página. */
(function () {
  "use strict";
  var eur = function (v) {
    return (Math.round(v * 100) / 100).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: "always" }) + " €";
  };
  var num = function (f, n) { var v = parseFloat(String(f.elements[n].value).replace(",", ".")); return isNaN(v) ? 0 : v; };

  // RETA 2026: tramos de 2025 prorrogados (RDL 3/2026) con MEI al 0,9 %: tipo total 31,5 %
  var TIPO_RETA = 0.315;
  var TRAMOS = [
    [670, 653.59], [900, 718.95], [1166.70, 849.67], [1300, 950.98], [1500, 960.78], [1700, 960.78],
    [1850, 1143.79], [2030, 1209.15], [2330, 1274.51], [2760, 1356.21], [3190, 1437.91], [3620, 1519.61],
    [4050, 1601.31], [6000, 1732.03], [Infinity, 1928.10]
  ];
  var BASE_SOCIETARIO = 1424.40; // base mínima 2026 autónomos societarios
  function tramo(rendMes) {
    for (var i = 0; i < TRAMOS.length; i++) if (rendMes <= TRAMOS[i][0]) return { n: i + 1, base: TRAMOS[i][1], tope: TRAMOS[i][0] };
  }
  // Escalas IRPF orientativas (estatal + autonómica media)
  var GENERAL = [[12450, .19], [20200, .24], [35200, .30], [60000, .37], [300000, .45], [Infinity, .47]];
  var AHORRO = [[6000, .19], [50000, .21], [200000, .23], [300000, .27], [Infinity, .30]];
  function escala(base, tabla) {
    var cuota = 0, previo = 0;
    for (var i = 0; i < tabla.length && base > previo; i++) {
      var tramoMax = Math.min(base, tabla[i][0]);
      cuota += (tramoMax - previo) * tabla[i][1]; previo = tabla[i][0];
    }
    return cuota;
  }
  var MINIMO_PERSONAL = 5550;
  function irpfGeneral(base) { return Math.max(0, escala(Math.max(base, 0), GENERAL) - escala(MINIMO_PERSONAL, GENERAL)); }

  var calcs = {
    cuota: function (f, out) {
      var neto = num(f, "rendimiento"), societario = f.elements.tipo.value === "societario";
      var computable = neto * (societario ? 0.97 : 0.93);
      var t = tramo(computable), cuota = t.base * TIPO_RETA;
      var plana = f.elements.plana.checked;
      var cuotaSoc = BASE_SOCIETARIO * TIPO_RETA;
      var mensual = plana ? 80 : (societario ? Math.max(cuota, cuotaSoc) : cuota);
      var canarias = f.elements.canarias && f.elements.canarias.checked;
      out.innerHTML =
        "<p class='tenue'>Cuota mensual estimada</p><p class='grande'>" + eur(mensual) + "</p>" +
        "<table><tr><td>Rendimiento computable (" + (societario ? "−3 %" : "−7 %") + " gastos genéricos)</td><td>" + eur(computable) + "</td></tr>" +
        "<tr><td>Tramo</td><td>" + t.n + " de 15</td></tr><tr><td>Base mínima del tramo</td><td>" + eur(t.base) + "</td></tr>" +
        (societario ? "<tr><td>Base mínima societarios 2026</td><td>" + eur(BASE_SOCIETARIO) + "</td></tr>" : "") +
        "<tr><td>Cuota anual</td><td>" + eur(mensual * 12) + "</td></tr></table>" +
        (plana ? "<p class='nota'>Tarifa plana: 80 €/mes durante 12 meses si es tu primera alta o llevas 2 años sin estar de alta (3 si ya la disfrutaste). Puede ampliarse 12 meses más si tus rendimientos son inferiores al SMI.</p>" : "") +
        (canarias && plana ? "<p class='nota'><b>Cuota cero en Canarias:</b> el Gobierno de Canarias te devuelve las cuotas reducidas de la tarifa plana. Si la convocatoria se repite, tu coste neto queda en 0 €: pagas los 80 €/mes y los recuperas en la convocatoria del año siguiente al alta (la de 2026, para altas de 2025, estuvo abierta del 9 de marzo al 15 de octubre). Requisitos: domicilio fiscal y actividad en Canarias.</p>" : "") +
        (canarias && !plana ? "<p class='nota'>La cuota cero de Canarias devuelve solo cuotas reducidas o bonificadas, como la tarifa plana. Si es tu primera alta, marca la tarifa plana.</p>" : "") +
        "<p class='peq tenue'>La cuota definitiva se regulariza al año siguiente con tus rendimientos reales.</p>";
    },

    sl: function (f, out) {
      var B = num(f, "beneficio"), gestoria = num(f, "gestoria"), nueva = f.elements.nueva.checked;
      // Autónomo
      var cuotaMes = tramo((B / 12) * 0.93).base * TIPO_RETA, ssA = cuotaMes * 12;
      var rn = B - ssA, gdj = Math.min(Math.max(rn, 0) * 0.05, 2000);
      var irpfA = irpfGeneral(rn - gdj), netoA = B - ssA - irpfA;
      // SL: busca el sueldo de administrador que maximiza lo que te llevas
      var ssS = BASE_SOCIETARIO * TIPO_RETA * 12, mejor = null;
      var tipoIS = function (base) {
        if (base <= 0) return 0;
        if (nueva) return base * 0.15;
        return Math.min(base, 50000) * 0.19 + Math.max(base - 50000, 0) * 0.21;
      };
      for (var S = 0; S <= Math.max(B - ssS - gestoria, 0); S += 250) {
        var resultado = B - S - ssS - gestoria, is = tipoIS(resultado), div = Math.max(resultado - is, 0);
        var irpfS = irpfGeneral(S - 2000), irpfDiv = escala(div, AHORRO);
        var neto = S - irpfS + div - irpfDiv;
        if (!mejor || neto > mejor.neto) mejor = { S: S, is: is, div: div, irpfS: irpfS, irpfDiv: irpfDiv, neto: neto, retenido: S - irpfS + div };
      }
      if (!mejor) mejor = { S: 0, is: 0, div: 0, irpfS: 0, irpfDiv: 0, neto: B - ssS - gestoria, retenido: B - ssS - gestoria };
      var ric = f.elements.ric && f.elements.ric.checked;
      var resSL = Math.max(B - mejor.S - ssS - gestoria, 0), isRic = tipoIS(resSL * 0.10);
      var retenidoRic = mejor.S - mejor.irpfS + resSL - isRic;
      var gana = mejor.neto > netoA ? "La SL te deja más neto" : "Como autónomo te quedas con más";
      var dif = Math.abs(mejor.neto - netoA);
      out.innerHTML =
        "<p class='tenue'>" + gana + "</p><p class='grande'>" + eur(dif) + " al año de diferencia</p>" +
        "<table><tr><td><b>Autónomo</b></td><td></td></tr>" +
        "<tr><td>Cuota de autónomos</td><td>" + eur(ssA) + "</td></tr><tr><td>IRPF</td><td>" + eur(irpfA) + "</td></tr>" +
        "<tr><td>Neto para ti</td><td><b>" + eur(netoA) + "</b></td></tr>" +
        "<tr><td><b>Sociedad limitada</b></td><td></td></tr>" +
        "<tr><td>Cuota autónomo societario (base mínima)</td><td>" + eur(ssS) + "</td></tr>" +
        "<tr><td>Coste extra de gestoría y cuentas</td><td>" + eur(gestoria) + "</td></tr>" +
        "<tr><td>Sueldo óptimo de administrador</td><td>" + eur(mejor.S) + "</td></tr>" +
        "<tr><td>Impuesto sobre Sociedades (" + (nueva ? "15 % nueva creación" : "19/21 % microempresa") + ")</td><td>" + eur(mejor.is) + "</td></tr>" +
        "<tr><td>IRPF del sueldo</td><td>" + eur(mejor.irpfS) + "</td></tr>" +
        "<tr><td>IRPF de dividendos si repartes todo</td><td>" + eur(mejor.irpfDiv) + "</td></tr>" +
        "<tr><td>Neto para ti repartiendo todo</td><td><b>" + eur(mejor.neto) + "</b></td></tr>" +
        "<tr><td>Si dejas los beneficios en la SL</td><td>" + eur(mejor.retenido) + " (sin IRPF de dividendos aún)</td></tr>" +
        (ric ? "<tr><td>Impuesto sobre Sociedades dotando la RIC con el 90 % del beneficio (Canarias)</td><td>" + eur(isRic) + "</td></tr>" +
               "<tr><td>Si dejas los beneficios en la SL y dotas la RIC</td><td><b>" + eur(retenidoRic) + "</b> (" + eur(mejor.is - isRic) + " menos de Sociedades)</td></tr>" : "") +
        "</table>" +
        (ric ? "<p class='nota'>La RIC reduce la base del Impuesto sobre Sociedades hasta el 90 % del beneficio que no repartes, pero obliga a invertir esa cantidad en Canarias en un plazo de 3 años y a mantener la inversión 5 años. Como autónomo, la RIC funciona como deducción en la cuota del IRPF, con otros límites.</p>" : "") +
        "<p class='peq tenue'>Escala de IRPF estatal más una autonómica media y mínimo personal de 5.550 €. No incluye deducciones, retribuciones en especie ni la limitación de operaciones vinculadas.</p>";
    },

    constitucion: function (f, out) {
      var via = f.elements.via.value, socios = Math.max(1, num(f, "socios")), capital = num(f, "capital");
      var p = {
        pae: { notaria: [60, 150], registro: [40, 100], gestoria: [0, 0], dias: "2 a 7 días laborables" },
        online: { notaria: [250, 450], registro: [100, 200], gestoria: [150, 350], dias: "1 a 2 semanas" },
        clasica: { notaria: [300, 600], registro: [150, 300], gestoria: [300, 800], dias: "2 a 4 semanas" }
      }[via];
      var extraSocios = Math.max(0, socios - 1) * 25;
      var min = 15 + p.notaria[0] + extraSocios + p.registro[0] + p.gestoria[0] + 15;
      var max = 20 + p.notaria[1] + extraSocios * 2 + p.registro[1] + p.gestoria[1] + 30;
      out.innerHTML =
        "<p class='tenue'>Coste orientativo sin contar el capital</p><p class='grande'>" + eur(min) + " – " + eur(max) + "</p>" +
        "<table><tr><td>Certificación negativa de denominación</td><td>15 – 20 €</td></tr>" +
        "<tr><td>Notaría</td><td>" + eur(p.notaria[0] + extraSocios) + " – " + eur(p.notaria[1] + extraSocios * 2) + "</td></tr>" +
        "<tr><td>Registro Mercantil</td><td>" + eur(p.registro[0]) + " – " + eur(p.registro[1]) + "</td></tr>" +
        "<tr><td>Gestoría</td><td>" + (p.gestoria[1] ? eur(p.gestoria[0]) + " – " + eur(p.gestoria[1]) : "0 € (tramitas tú en un PAE)") + "</td></tr>" +
        "<tr><td>Certificado de representante (FNMT)</td><td>15 – 30 €</td></tr>" +
        "<tr><td>Impuesto de operaciones societarias</td><td>0 € (exento)</td></tr>" +
        "<tr><td>Plazo habitual</td><td>" + p.dias + "</td></tr>" +
        "<tr><td>Capital que aportas</td><td>" + eur(capital) + "</td></tr></table>" +
        (capital < 3000 ? "<p class='nota'>Con menos de 3.000 € de capital debes destinar al menos el 20 % del beneficio a reserva legal hasta llegar a 3.000 €, y los socios responden solidariamente de la diferencia si la sociedad se liquida sin patrimonio suficiente.</p>" : "");
    },

    factura: function (f, out) {
      var terr = f.elements.territorio ? f.elements.territorio.value : "peninsula";
      var sel = f.elements.iva;
      if (f.getAttribute("data-terr") !== terr) {
        var opciones = {
          peninsula: [["21", "21 % general"], ["10", "10 % reducido"], ["4", "4 % superreducido"], ["0", "Exenta"]],
          canarias: [["7", "7 % general"], ["3", "3 % reducido"], ["0", "0 % tipo cero"], ["9.5", "9,5 % incrementado"], ["15", "15 % incrementado"], ["exento", "Exenta: pequeño empresario (hasta 50.000 €)"]],
          canarias_peninsula: [["0", "Sin IGIC ni IVA: inversión del sujeto pasivo"]]
        }[terr];
        sel.innerHTML = opciones.map(function (o) { return "<option value='" + o[0] + "'>" + o[1] + "</option>"; }).join("");
        f.setAttribute("data-terr", terr);
        var etiqueta = document.getElementById("etiqueta-impuesto");
        if (etiqueta) etiqueta.textContent = terr === "peninsula" ? "IVA" : "IGIC";
      }
      var nombre = terr === "peninsula" ? "IVA" : "IGIC";
      var tipo = sel.value === "exento" ? 0 : parseFloat(sel.value);
      var base = num(f, "base"), ret = num(f, "retencion") / 100;
      var cuotaImp = base * tipo / 100, cuotaRet = base * ret, total = base + cuotaImp - cuotaRet;
      var ingresos = num(f, "ingresos"), gastos = num(f, "gastos"), retAcum = num(f, "retenciones"), previos = num(f, "previos");
      var m130 = Math.max(0, (ingresos - gastos) * 0.20 - retAcum - previos);
      var mencion = terr === "canarias_peninsula"
        ? "Operación no sujeta al IGIC (art. 17 de la Ley 20/1991). Inversión del sujeto pasivo: el IVA corresponde al destinatario (art. 84.Uno.2.º de la Ley 37/1992)."
        : (sel.value === "exento" ? "Operación exenta del IGIC por aplicación del régimen especial del pequeño empresario o profesional." : "");
      out.innerHTML =
        "<p class='tenue'>Total que cobrarás por la factura</p><p class='grande'>" + eur(total) + "</p>" +
        "<table><tr><td>Base imponible</td><td>" + eur(base) + "</td></tr>" +
        (terr === "canarias_peninsula" ? "<tr><td>IGIC o IVA en tu factura</td><td>No lleva</td></tr>"
          : "<tr><td>" + nombre + " (" + (sel.value === "exento" ? "exenta" : String(tipo).replace(".", ",") + " %") + ")</td><td>+ " + eur(cuotaImp) + "</td></tr>") +
        "<tr><td>Retención IRPF (" + (ret * 100) + " %)</td><td>− " + eur(cuotaRet) + "</td></tr></table>" +
        (mencion ? "<p class='nota'><b>Pon en la factura:</b> " + mencion + "</p>" : "") +
        (terr !== "peninsula" && sel.value !== "exento" && terr !== "canarias_peninsula" ? "<p class='peq tenue'>El IGIC repercutido se declara en el modelo 420 trimestral ante la Agencia Tributaria Canaria.</p>" : "") +
        "<h3 style='margin-top:1.4rem'>Modelo 130 estimado</h3>" +
        "<table><tr><td>20 % del rendimiento acumulado del año</td><td>" + eur(Math.max(0, (ingresos - gastos) * 0.2)) + "</td></tr>" +
        "<tr><td>Menos retenciones que te han practicado</td><td>− " + eur(retAcum) + "</td></tr>" +
        "<tr><td>Menos pagos de trimestres anteriores</td><td>− " + eur(previos) + "</td></tr>" +
        "<tr><td><b>A ingresar este trimestre</b></td><td><b>" + eur(m130) + "</b></td></tr></table>" +
        "<p class='peq tenue'>Si al menos el 70 % de tus ingresos del año anterior llevó retención, no tienes que presentar el 130. El 130 se presenta en la Agencia Tributaria estatal también desde Canarias.</p>";
    }
  };

  document.querySelectorAll("form[data-calc]").forEach(function (f) {
    var out = document.getElementById(f.getAttribute("data-salida"));
    var run = function () { try { calcs[f.getAttribute("data-calc")](f, out); } catch (e) { out.textContent = "Revisa los datos introducidos."; } };
    f.addEventListener("input", run); f.addEventListener("change", run);
    f.addEventListener("submit", function (e) { e.preventDefault(); run(); });
    run();
  });
})();
