/*!
 * Calendarios de fútbol 7 del Club Deportivo Estoril II.
 *
 * Carga los JSON de temporada publicados junto a este fichero y pinta todos
 * los calendarios de la temporada elegida con filtros de temporada,
 * categoría y jornada. Sin dependencias.
 *
 * Uso en una página:
 *   <link rel="stylesheet" href="https://clubestoril2.github.io/futbol-7/futbol7.css">
 *   <div id="futbol7-app"></div>
 *   <script src="https://clubestoril2.github.io/futbol-7/futbol7.js" defer></script>
 *
 * El marcado usa las clases del tema de la web del club (ce-boton, ce-tabla,
 * ce-meta, ce-aviso, ce-oculto); futbol7.css solo añade lo que el tema no tiene.
 *
 * Atributos opcionales del contenedor:
 *   data-base="https://.../"   raíz donde está la carpeta data/ (por defecto, la del script)
 *   data-temporada="2025-26"   temporada inicial (por defecto la actual o la última)
 *   data-nivel="2"             nivel del primer encabezado que se genera (h2)
 *   data-hoy="2026-01-20"      fecha que se toma como «hoy» (solo para pruebas)
 *
 * Estructura que genera:
 *   - «Jornada actual»: próxima jornada de cada categoría de la temporada en
 *     curso (fija; no aparece si la temporada ha terminado).
 *   - «Buscador de encuentros»: filtros de temporada, categoría y jornada y
 *     los calendarios completos.
 */
(function () {
    'use strict';

    var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    var MESES_LARGO = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
        'septiembre', 'octubre', 'noviembre', 'diciembre'];
    var DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
    var scriptSrc = document.currentScript && document.currentScript.src;

    /* ---------- utilidades ---------- */

    function el(etiqueta, atributos, hijos) {
        var nodo = document.createElement(etiqueta);
        if (atributos) {
            Object.keys(atributos).forEach(function (k) {
                if (atributos[k] === null || atributos[k] === undefined) { return; }
                if (k === 'text') { nodo.textContent = atributos[k]; }
                else if (k === 'on') {
                    Object.keys(atributos.on).forEach(function (ev) { nodo.addEventListener(ev, atributos.on[ev]); });
                }
                else { nodo.setAttribute(k, atributos[k]); }
            });
        }
        (hijos || []).forEach(function (h) {
            if (h === null || h === undefined) { return; }
            nodo.appendChild(typeof h === 'string' ? document.createTextNode(h) : h);
        });
        return nodo;
    }

    function partesFecha(iso) {
        var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
        if (!m) { return null; }
        return { a: +m[1], m: +m[2], d: +m[3], fecha: new Date(+m[1], +m[2] - 1, +m[3]) };
    }

    function dosCifras(n) { return (n < 10 ? '0' : '') + n; }

    /* 10/nov */
    function fechaCorta(iso) {
        var p = partesFecha(iso);
        return p ? dosCifras(p.d) + '/' + MESES[p.m - 1] : '';
    }

    /* sábado 15 de noviembre de 2025 */
    function fechaLarga(iso) {
        var p = partesFecha(iso);
        return p ? DIAS[p.fecha.getDay()] + ' ' + p.d + ' de ' + MESES_LARGO[p.m - 1] + ' de ' + p.a : '';
    }

    /* 15/11/2025 */
    function fechaNumerica(iso) {
        var p = partesFecha(iso);
        return p ? dosCifras(p.d) + '/' + dosCifras(p.m) + '/' + p.a : '';
    }

    function hoyISO(forzado) {
        if (/^\d{4}-\d{2}-\d{2}$/.test(forzado || '')) { return forzado; }
        var d = new Date();
        return d.getFullYear() + '-' + dosCifras(d.getMonth() + 1) + '-' + dosCifras(d.getDate());
    }

    /* Última fecha de los partidos de una jornada (o la de la jornada). */
    function ultimaFecha(jornada) {
        var fechas = (jornada.partidos || []).map(function (p) { return p.fecha; }).filter(Boolean).sort();
        return fechas.length ? fechas[fechas.length - 1] : (jornada.fecha || '');
    }

    /* Próxima jornada de una categoría: la primera que aún no ha terminado (hoy incluido). */
    function jornadaActual(categoria, hoy) {
        var pendientes = (categoria.jornadas || []).filter(function (j) { return ultimaFecha(j) >= hoy; });
        return pendientes.length ? pendientes[0] : null;
    }

    function temporadaActual() {
        var hoy = new Date();
        var inicio = hoy.getMonth() + 1 >= 7 ? hoy.getFullYear() : hoy.getFullYear() - 1;
        return inicio + '-' + dosCifras((inicio + 1) % 100);
    }

    function esEstoril(nombre) { return /ESTORIL/i.test(nombre || ''); }

    function leerHash() {
        var h = location.hash.replace(/^#/, '');
        var estado = {};
        if (!/^(t|c|j)=/.test(h)) { return estado; }
        h.split('&').forEach(function (par) {
            var kv = par.split('=');
            if (kv[0] === 't') { estado.temporada = decodeURIComponent(kv[1] || ''); }
            if (kv[0] === 'c') { estado.categoria = decodeURIComponent(kv[1] || ''); }
            if (kv[0] === 'j') { estado.jornada = kv[1] === 'ninguna' ? 'ninguna' : (parseInt(kv[1], 10) || null); }
        });
        return estado;
    }

    function hashPropio() { return /^#(t|c|j)=/.test(location.hash); }

    function escribirHash(estado, porDefecto) {
        /* Sin filtros y con la temporada por defecto no se toca la URL, para
           respetar las anclas de la página (#alevin) y no ensuciar el enlace. */
        if (!estado.categoria && !estado.jornada && estado.temporada === porDefecto && !hashPropio()) { return; }
        var partes = ['t=' + encodeURIComponent(estado.temporada)];
        if (estado.categoria) { partes.push('c=' + encodeURIComponent(estado.categoria)); }
        if (estado.jornada) { partes.push('j=' + estado.jornada); }
        var nuevo = '#' + partes.join('&');
        if (location.hash !== nuevo && window.history && history.replaceState) {
            history.replaceState(null, '', nuevo);
        }
    }

    /* ---------- aplicación ---------- */

    function Futbol7(root) {
        this.root = root;
        this.base = this.calcularBase();
        this.nivel = Math.min(Math.max(parseInt(root.getAttribute('data-nivel'), 10) || 2, 1), 5);
        this.cache = {};
        this.estado = { temporada: null, categoria: null, jornada: null };
        this.temporadas = [];
        this.datos = null;

        root.classList.add('f7');
        root.setAttribute('aria-busy', 'true');
        this.hoy = hoyISO(root.getAttribute('data-hoy'));
        this.nodoActual = el('section', { 'class': 'f7-actual', hidden: '' });
        this.nodoBuscador = el('section', { 'class': 'f7-buscador' });
        this.nodoFiltros = el('div', { 'class': 'f7-filtros ce-no-imprimir', role: 'group', 'aria-label': 'Filtros del calendario' });
        this.nodoContenido = el('div', { 'class': 'f7-contenido', 'aria-live': 'polite' });
        root.textContent = '';
        root.appendChild(this.nodoActual);
        root.appendChild(this.nodoBuscador);
        this.nodoBuscador.appendChild(this.encabezado(0, { 'class': 'f7-buscador__titulo' }, ['Buscador de encuentros']));
        this.nodoBuscador.appendChild(this.nodoFiltros);
        this.nodoBuscador.appendChild(this.nodoContenido);
        this.mensaje('Cargando calendarios…', 'ce-meta');

        var yo = this;
        window.addEventListener('hashchange', function () {
            var h = leerHash();
            if (h.temporada || h.categoria || h.jornada) { yo.aplicarEstado(h); }
        });
        this.cargarIndice();
    }

    Futbol7.prototype.calcularBase = function () {
        var base = this.root.getAttribute('data-base');
        if (!base && scriptSrc) { base = scriptSrc.replace(/[^\/]*$/, ''); }
        if (!base) { base = './'; }
        return base.replace(/\/?$/, '/');
    };

    Futbol7.prototype.mensaje = function (texto, clase) {
        this.nodoContenido.textContent = '';
        this.nodoContenido.appendChild(el('p', { 'class': clase || 'ce-meta', text: texto }));
    };

    Futbol7.prototype.pedir = function (ruta) {
        return fetch(this.base + ruta, { cache: 'no-cache' }).then(function (r) {
            if (!r.ok) { throw new Error('HTTP ' + r.status + ' al pedir ' + ruta); }
            return r.json();
        });
    };

    Futbol7.prototype.cargarIndice = function () {
        var yo = this;
        this.pedir('data/index.json').then(function (indice) {
            yo.temporadas = (indice.temporadas || []).slice().sort(function (a, b) {
                return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
            });
            if (!yo.temporadas.length) { throw new Error('No hay temporadas publicadas'); }
            var inicial = leerHash();
            var pedida = inicial.temporada || yo.root.getAttribute('data-temporada') || temporadaActual();
            var existe = yo.temporadas.some(function (t) { return t.id === pedida; });
            inicial.temporada = existe ? pedida : yo.temporadas[yo.temporadas.length - 1].id;
            yo.temporadaPorDefecto = inicial.temporada;
            /* La temporada en curso: la actual si está publicada, si no la última. */
            var enCurso = yo.temporadas.some(function (t) { return t.id === temporadaActual(); })
                ? temporadaActual() : yo.temporadas[yo.temporadas.length - 1].id;
            yo.cargarTemporada(enCurso).then(function (datos) { yo.pintarActual(datos); }).catch(function () {});
            yo.aplicarEstado(inicial);
        }).catch(function (e) { yo.error(e); });
    };

    Futbol7.prototype.error = function (e) {
        this.root.setAttribute('aria-busy', 'false');
        this.mensaje('No se han podido cargar los calendarios (' + e.message + '). ' +
            'Puede consultarlos en la web del Ayuntamiento de Móstoles.', 'ce-aviso');
        if (window.console) { console.error('futbol7', e); }
    };

    Futbol7.prototype.aplicarEstado = function (nuevo) {
        var yo = this;
        var temporada = nuevo.temporada || this.estado.temporada;
        var cambiaTemporada = temporada !== this.estado.temporada;
        this.estado = {
            temporada: temporada,
            categoria: nuevo.categoria !== undefined ? nuevo.categoria : this.estado.categoria,
            jornada: nuevo.jornada !== undefined ? nuevo.jornada : this.estado.jornada
        };
        if (!cambiaTemporada && this.datos) { this.pintar(); return; }

        this.root.setAttribute('aria-busy', 'true');
        this.pintarFiltros();
        var promesa = this.cache[temporada] ? Promise.resolve(this.cache[temporada]) : this.cargarTemporada(temporada);
        promesa.then(function (datos) {
            if (yo.estado.temporada !== temporada) { return; }
            yo.datos = datos;
            yo.root.setAttribute('aria-busy', 'false');
            yo.pintar();
        }).catch(function (e) { yo.error(e); });
    };

    Futbol7.prototype.cargarTemporada = function (id) {
        var yo = this;
        var entrada = this.temporadas.filter(function (t) { return t.id === id; })[0];
        var fichero = entrada && entrada.fichero ? entrada.fichero : id + '.json';
        return this.pedir('data/' + fichero).then(function (datos) {
            yo.cache[id] = datos;
            return datos;
        });
    };

    /* Id de categoría base de un calendario (benjamin-f1-g2 -> benjamin). */
    function categoriaDe(c) { return c.categoria || c.id; }
    function nombreCategoriaDe(c) { return c.categoria_nombre || c.nombre; }

    /* Calendarios (categoría, fase, grupo) visibles con el filtro actual */
    Futbol7.prototype.categoriasVisibles = function () {
        var cat = this.estado.categoria;
        return (this.datos.categorias || []).filter(function (c) { return !cat || categoriaDe(c) === cat; });
    };

    /* Categorías base de la temporada, en orden y sin repetir: [{id, nombre}] */
    Futbol7.prototype.categoriasBase = function () {
        var vistas = {}, lista = [];
        (this.datos.categorias || []).forEach(function (c) {
            var id = categoriaDe(c);
            if (!vistas[id]) { vistas[id] = true; lista.push({ id: id, nombre: nombreCategoriaDe(c) }); }
        });
        return lista;
    };

    /* Jornadas disponibles (número -> fechas) para las categorías visibles */
    Futbol7.prototype.jornadasDisponibles = function () {
        var mapa = {};
        this.categoriasVisibles().forEach(function (c) {
            (c.jornadas || []).forEach(function (j) {
                var fechas = mapa[j.numero] || (mapa[j.numero] = []);
                if (j.fecha && fechas.indexOf(j.fecha) === -1) { fechas.push(j.fecha); }
            });
        });
        return Object.keys(mapa).map(function (n) { return { numero: +n, fechas: mapa[n].sort() }; })
            .sort(function (a, b) { return a.numero - b.numero; });
    };

    Futbol7.prototype.pintar = function () {
        this.pintarFiltros();
        this.pintarContenido();
        escribirHash(this.estado, this.temporadaPorDefecto);
        this.irAlAncla();
    };

    /* Si se llegó con un ancla de la página (#alevin, #alevin-j3) se desplaza a ella una vez pintada. */
    Futbol7.prototype.irAlAncla = function () {
        if (this.anclaAtendida || hashPropio() || !location.hash) { return; }
        var id = decodeURIComponent(location.hash.slice(1));
        var destino = this.nodoContenido.querySelector('[id="' + id.replace(/"/g, '') + '"]');
        this.anclaAtendida = true;
        if (destino && destino.scrollIntoView) { destino.scrollIntoView(); }
    };

    Futbol7.prototype.boton = function (texto, activo, alPulsar, extra) {
        var b = el('button', {
            type: 'button',
            'class': 'ce-boton ' + (activo ? 'ce-boton--primario' : 'ce-boton--secundario'),
            'aria-pressed': activo ? 'true' : 'false',
            on: { click: alPulsar }
        }, typeof texto === 'string' ? [texto] : texto);
        if (extra) { Object.keys(extra).forEach(function (k) { b.setAttribute(k, extra[k]); }); }
        return b;
    };

    Futbol7.prototype.grupo = function (titulo, botones, ayuda) {
        return el('fieldset', { 'class': 'f7-grupo' }, [
            el('legend', { 'class': 'f7-grupo__titulo', text: titulo }),
            el('div', { 'class': 'f7-grupo__botones' }, botones),
            ayuda ? el('p', { 'class': 'ce-meta', text: ayuda }) : null
        ]);
    };

    Futbol7.prototype.pintarFiltros = function () {
        var yo = this, est = this.estado;
        var nodo = this.nodoFiltros;
        nodo.textContent = '';

        nodo.appendChild(this.grupo('Temporada', this.temporadas.map(function (t) {
            return yo.boton(t.nombre, t.id === est.temporada, function () {
                yo.aplicarEstado({ temporada: t.id });
            });
        })));

        if (!this.datos) { return; }

        nodo.appendChild(this.grupo('Categoría', this.categoriasBase().map(function (c) {
            var activo = c.id === est.categoria;
            return yo.boton(c.nombre, activo, function () {
                yo.aplicarEstado({ categoria: activo ? null : c.id });
            });
        })));

        var jornadas = this.jornadasDisponibles();
        /* «Ninguna» oculta los calendarios del buscador (útil para imprimir solo la jornada actual). */
        var ninguna = est.jornada === 'ninguna';
        var botonesJornada = [yo.boton('Ninguna', ninguna, function () {
            yo.aplicarEstado({ jornada: ninguna ? null : 'ninguna' });
        }, { 'aria-label': 'Ninguna jornada: no mostrar calendarios' })];
        nodo.appendChild(this.grupo('Jornada', botonesJornada.concat(jornadas.map(function (j) {
            var activo = j.numero === est.jornada;
            var etiqueta;
            if (!j.fechas.length) { etiqueta = ''; }
            else if (j.fechas.length === 1) { etiqueta = fechaCorta(j.fechas[0]); }
            else { etiqueta = fechaCorta(j.fechas[0]) + ' – ' + fechaCorta(j.fechas[j.fechas.length - 1]); }
            return yo.boton([
                String(j.numero),
                etiqueta ? el('small', { 'class': 'f7-boton__fecha', text: etiqueta }) : null
            ], activo, function () {
                yo.aplicarEstado({ jornada: activo ? null : j.numero });
            }, { 'aria-label': 'Jornada ' + j.numero + (etiqueta ? ', ' + etiqueta : '') });
        }))));

        if (est.categoria || est.jornada) {
            nodo.appendChild(el('p', { 'class': 'f7-limpiar' }, [
                el('button', {
                    type: 'button', 'class': 'f7-enlace', text: 'Mostrar todos los calendarios',
                    on: { click: function () { yo.aplicarEstado({ categoria: null, jornada: null }); } }
                })
            ]));
        }
    };

    /* Bloque fijo con la próxima jornada de cada categoría de la temporada en curso. */
    Futbol7.prototype.pintarActual = function (datos) {
        var yo = this, nodo = this.nodoActual;
        nodo.textContent = '';
        var pendientes = (datos.categorias || []).map(function (c) {
            return { categoria: c, jornada: jornadaActual(c, yo.hoy) };
        }).filter(function (x) { return x.jornada; });
        if (!pendientes.length) { nodo.setAttribute('hidden', ''); return; }

        nodo.appendChild(this.encabezado(0, { 'class': 'f7-actual__titulo' }, ['Jornada actual']));
        nodo.appendChild(el('p', { 'class': 'ce-meta', text: 'Próximos encuentros de la temporada ' + datos.temporada + '.' }));
        pendientes.forEach(function (x) {
            nodo.appendChild(yo.pintarJornada(x.categoria, x.jornada, { id: null }));
        });
        nodo.removeAttribute('hidden');
    };

    /* Enlaces a los PDF oficiales de los calendarios indicados, en una línea. */
    Futbol7.prototype.enlacesPdf = function (calendarios) {
        var enlaces = [];
        calendarios.forEach(function (c) {
            if (!c.pdf) { return; }
            enlaces.push(enlaces.length ? ', ' : 'Calendarios oficiales (PDF): ');
            enlaces.push(el('a', {
                href: c.pdf, target: '_blank', rel: 'noopener noreferrer', text: c.nombre,
                title: c.pdf_fecha ? 'Publicado el ' + fechaNumerica(c.pdf_fecha) : null
            }));
        });
        if (!enlaces.length) { return null; }
        enlaces.push('.');
        return el('p', { 'class': 'ce-meta f7-pdfs' }, enlaces);
    };

    Futbol7.prototype.encabezado = function (nivelRelativo, atributos, hijos) {
        return el('h' + Math.min(this.nivel + nivelRelativo, 6), atributos, hijos);
    };

    Futbol7.prototype.pintarContenido = function () {
        var yo = this, est = this.estado, datos = this.datos;
        var nodo = this.nodoContenido;
        nodo.textContent = '';

        /* Con «Ninguna» el buscador queda vacío y fuera de la impresión. */
        var ninguna = est.jornada === 'ninguna';
        this.nodoBuscador.classList.toggle('ce-no-imprimir', ninguna);
        if (ninguna) {
            nodo.appendChild(el('p', { 'class': 'ce-meta', text: 'No se muestra ningún calendario. Elija una jornada o pulse «Mostrar todos los calendarios».' }));
            return;
        }

        nodo.appendChild(el('p', { 'class': 'ce-meta', text: 'Encuentros de la temporada ' + datos.temporada + '.' }));

        /*
         * Mismo formato que «Jornada actual»: cada jornada lleva un encabezado
         * del mismo nivel con la categoría, la fase, el grupo y la fecha.
         * Las secciones por categoría y por calendario solo sirven de ancla.
         */
        var secciones = [], visibles = [];
        this.categoriasBase().forEach(function (base) {
            var seccion = el('section', { 'class': 'f7-categoria', id: base.id });
            yo.categoriasVisibles().filter(function (c) { return categoriaDe(c) === base.id; }).forEach(function (c) {
                var jornadas = (c.jornadas || []).filter(function (j) { return !est.jornada || j.numero === est.jornada; });
                if (!jornadas.length) { return; }
                visibles.push(c);
                var bloque = el('div', { 'class': 'f7-calendario', id: c.id });
                jornadas.forEach(function (j) { bloque.appendChild(yo.pintarJornada(c, j)); });
                seccion.appendChild(bloque);
            });
            if (seccion.childNodes.length) { secciones.push(seccion); }
        });
        var hayAlgo = secciones.length > 0;
        var pdfs = this.enlacesPdf(visibles);
        if (pdfs) { nodo.appendChild(pdfs); }
        secciones.forEach(function (s) { nodo.appendChild(s); });

        if (!hayAlgo) {
            nodo.appendChild(el('p', { 'class': 'ce-meta', text: 'No hay partidos que coincidan con el filtro elegido.' }));
        }

        if (datos.fuente || datos.actualizado) {
            var pie = [];
            if (datos.fuente) {
                pie.push('Datos extraídos de la ');
                pie.push(el('a', { href: datos.fuente, target: '_blank', rel: 'noopener noreferrer', text: 'web del Ayuntamiento de Móstoles' }));
            }
            if (datos.actualizado) { pie.push((pie.length ? ' · ' : '') + 'última comprobación: ' + fechaNumerica(datos.actualizado)); }
            pie.push('.');
            nodo.appendChild(el('p', { 'class': 'ce-meta f7-pie' }, pie));
        }
    };

    Futbol7.prototype.pintarJornada = function (categoria, jornada, opciones) {
        opciones = opciones || {};
        var titulo = categoria.nombre + ' · jornada ' + jornada.numero + (jornada.fecha ? ' · ' + fechaLarga(jornada.fecha) : '');
        var id = opciones.id === undefined ? categoria.id + '-j' + jornada.numero : opciones.id;
        var bloque = el('div', { 'class': 'f7-jornada', id: id });
        bloque.appendChild(this.encabezado(1, { 'class': 'f7-jornada__titulo' }, [titulo]));

        var cuerpo = el('tbody');
        (jornada.partidos || []).forEach(function (p) {
            if (p.descansa) {
                cuerpo.appendChild(el('tr', { 'class': 'f7-descansa' }, [
                    el('td', { colspan: '5' }, [
                        el('span', { 'class': esEstoril(p.local) ? 'f7-estoril' : null, text: p.local }), ' descansa'
                    ])
                ]));
                return;
            }
            cuerpo.appendChild(el('tr', null, [
                el('td', { 'class': 'f7-equipo' + (esEstoril(p.local) ? ' f7-estoril' : ''), text: p.local }),
                el('td', { 'class': 'f7-equipo' + (esEstoril(p.visitante) ? ' f7-estoril' : ''), text: p.visitante }),
                el('td', { 'class': 'f7-fecha', text: fechaNumerica(p.fecha) }),
                el('td', { 'class': 'f7-hora', text: p.hora || '' }),
                el('td', { 'class': 'f7-campo', text: p.campo || '' })
            ]));
        });

        /* Misma estructura que las tablas del resto de la web (div.ce-tabla > table.tabla). */
        var tabla = el('table', { 'class': 'tabla f7-tabla' }, [
            el('caption', { 'class': 'ce-oculto', text: titulo }),
            el('thead', null, [el('tr', null, [
                el('th', { scope: 'col', 'class': 'f7-equipo', text: 'Local' }),
                el('th', { scope: 'col', 'class': 'f7-equipo', text: 'Visitante' }),
                el('th', { scope: 'col', 'class': 'f7-fecha', text: 'Fecha' }),
                el('th', { scope: 'col', 'class': 'f7-hora', text: 'Hora' }),
                el('th', { scope: 'col', 'class': 'f7-campo', text: 'Campo' })
            ])]),
            cuerpo
        ]);
        bloque.appendChild(el('div', { 'class': 'ce-tabla' }, [tabla]));
        return bloque;
    };

    /* ---------- arranque ---------- */

    function iniciar(selector) {
        var nodos = document.querySelectorAll(selector || '#futbol7-app, [data-futbol7]');
        var apps = [];
        Array.prototype.forEach.call(nodos, function (n) {
            if (!n.futbol7) { n.futbol7 = new Futbol7(n); }
            apps.push(n.futbol7);
        });
        return apps;
    }

    window.Futbol7 = { iniciar: iniciar };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { iniciar(); });
    } else {
        iniciar();
    }
}());
