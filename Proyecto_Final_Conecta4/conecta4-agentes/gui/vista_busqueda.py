"""
Animación del proceso de búsqueda.

``ReproductorTraza`` reconstruye el estado del árbol de búsqueda después
de los primeros k eventos de una traza (ver ``conecta4.metricas.Traza``).
Como el estado se reconstruye a partir de la traza, la animación se
puede pausar, avanzar paso a paso y también RETROCEDER.

Las funciones ``dibujar_arbol`` y ``dibujar_estado_interno`` pintan ese
estado: los nodos se diferencian por color según estén en la frontera,
en expansión, evaluados o podados.
"""
import math

import pygame

from gui import tema

INF = float('inf')


class ReproductorTraza:
    """Reconstruye el árbol de búsqueda paso a paso a partir de la traza."""

    def __init__(self, traza):
        self.traza = traza
        self.es_mcts = traza.algoritmo == 'MCTS'
        self.total = len(traza.eventos)
        self._reiniciar()

    def _reiniciar(self):
        self.k = 0                  # Eventos aplicados
        self.nodos = {}             # camino -> datos del nodo
        self.actual = ()            # Camino del nodo del último evento
        self.evento = None          # Último evento aplicado
        self.alfa = -INF
        self.beta = INF
        self.foco = None            # Nodo de nivel 2 que se ve en detalle
        self.pv = set()             # Variante principal (mejor línea)
        if self.es_mcts:
            self.nodos[()] = {'n': 0, 'w': 0.0}
        else:
            self.nodos[()] = {'estado': 'pendiente'}

    def ir_a(self, k):
        """Deja el árbol como estaba después de k eventos."""
        k = max(0, min(k, self.total))
        if k < self.k:
            self._reiniciar()       # Para retroceder se reconstruye
        while self.k < k:
            evento = self.traza.eventos[self.k]
            if self.es_mcts:
                self._aplicar_mcts(evento)
            else:
                self._aplicar_minimax(evento)
            self.k += 1
        self.pv = self._variante_principal() if k == self.total else set()
        return self

    # ------------------------------------------------------------------
    # Minimax y alfa-beta
    # ------------------------------------------------------------------
    def _aplicar_minimax(self, e):
        camino = e['camino']
        nodo = self.nodos.setdefault(camino, {})
        if e['tipo'] == 'entra':
            # El nodo se expande: sus sucesores pasan a la frontera
            nodo.update(estado='actual', es_max=e['es_max'],
                        alfa=e['alfa'], beta=e['beta'])
            for a in e['acciones']:
                self.nodos.setdefault(camino + (a,), {'estado': 'pendiente'})
            self.alfa, self.beta = e['alfa'], e['beta']
        elif e['tipo'] == 'hoja':
            nodo.update(estado='evaluado', valor=e['valor'],
                        clase=e['clase'], cota=e['cota'])
        elif e['tipo'] == 'sale':
            nodo.update(estado='evaluado', valor=e['valor'],
                        mejor=e['mejor'], cota=e['cota'], clase='interno')
        elif e['tipo'] == 'poda':
            for a in e['podadas']:
                self.nodos.setdefault(camino + (a,), {})['estado'] = 'podado'
            self.alfa, self.beta = e['alfa'], e['beta']
        self.actual = camino
        self.evento = e
        if len(camino) >= 2:
            self.foco = camino[:2]

    def _variante_principal(self):
        """Caminos de la mejor línea encontrada, siguiendo desde la raíz
        la mejor jugada de cada nodo."""
        pv = set()
        if self.es_mcts:
            hijos = [c for c in self.nodos if len(c) == 1]
            if hijos:
                pv.add(max(hijos, key=lambda c: self.nodos[c]['n']))
            return pv
        camino = ()
        while camino in self.nodos:
            pv.add(camino)
            mejor = self.nodos[camino].get('mejor')
            if mejor is None:
                break
            camino = camino + (mejor,)
        return pv

    def frontera(self):
        """Cantidad de nodos generados que siguen pendientes."""
        return sum(1 for n in self.nodos.values()
                   if n.get('estado') == 'pendiente')

    # ------------------------------------------------------------------
    # MCTS
    # ------------------------------------------------------------------
    def _aplicar_mcts(self, e):
        camino = e['camino']
        self.nodos[()]['n'] += 1
        self.nodos[()]['w'] += e['resultado']
        for largo in (1, 2):
            if len(camino) >= largo:
                nodo = self.nodos.setdefault(camino[:largo],
                                             {'n': 0, 'w': 0.0})
                nodo['n'] += 1
                nodo['w'] += e['resultado']
        self.actual = camino
        self.evento = e


# ----------------------------------------------------------------------
# Geometría del árbol
# ----------------------------------------------------------------------
def _geometria(rect):
    """Coordenadas de los niveles del árbol dentro del panel."""
    x0 = rect.x + 50
    ancho = rect.width - 62
    return {
        'x0': x0, 'ancho': ancho,
        'y0': rect.y + 52, 'y1': rect.y + 110, 'y2': rect.y + 170,
        'y3': rect.y + 240,
    }


def _pos(geo, camino):
    """Posición en pantalla de un nodo de nivel 0, 1 o 2."""
    if len(camino) == 0:
        return (geo['x0'] + geo['ancho'] / 2, geo['y0'])
    if len(camino) == 1:
        return (geo['x0'] + (camino[0] + 0.5) * geo['ancho'] / 7, geo['y1'])
    indice = camino[0] * 7 + camino[1]
    return (geo['x0'] + (indice + 0.5) * geo['ancho'] / 49, geo['y2'])


def _pos_detalle(geo, a):
    """Posición de los sucesores (nivel 3) del nodo en detalle."""
    centro = geo['x0'] + geo['ancho'] / 2
    return (centro + (a - 3) * 58, geo['y3'])


def _color_nodo(rep, camino, nodo):
    if camino in rep.pv:
        return tema.NODO_MEJOR
    estado = nodo.get('estado')
    if estado == 'actual':
        return tema.NODO_ACTUAL
    if estado == 'evaluado':
        return tema.NODO_EVALUADO
    if estado == 'podado':
        return tema.NODO_PODADO
    return tema.NODO_PENDIENTE


def _dibujar_nodo(sup, rep, camino, pos, radio, etiqueta=None):
    """Dibuja un nodo de minimax/alfa-beta según su estado."""
    nodo = rep.nodos.get(camino)
    x, y = int(pos[0]), int(pos[1])
    if nodo is None:
        # Todavía no se ha generado: solo se marca su lugar
        pygame.draw.circle(sup, tema.PANEL_CLARO, (x, y), max(2, radio - 2),
                           1)
        return
    color = _color_nodo(rep, camino, nodo)
    estado = nodo.get('estado')
    if estado == 'pendiente':
        pygame.draw.circle(sup, tema.PANEL, (x, y), radio)
        pygame.draw.circle(sup, color, (x, y), radio, 2)
    elif estado == 'podado':
        pygame.draw.circle(sup, tema.PANEL, (x, y), radio)
        pygame.draw.circle(sup, color, (x, y), radio, 2)
        d = radio * 0.55
        pygame.draw.line(sup, color, (x - d, y - d), (x + d, y + d), 2)
        pygame.draw.line(sup, color, (x - d, y + d), (x + d, y - d), 2)
    else:
        pygame.draw.circle(sup, color, (x, y), radio)
        if nodo.get('clase') == 'terminal' and radio >= 4:
            pygame.draw.circle(sup, tema.BLANCO, (x, y), radio, 2)
    if camino == rep.actual and rep.k < rep.total:
        pygame.draw.circle(sup, tema.BLANCO, (x, y), radio + 3, 2)
    if etiqueta is not None and radio >= 10:
        color_texto = tema.TEXTO if estado in ('pendiente', 'podado') \
            else tema.FONDO
        tema.texto(sup, etiqueta, (x, y), 12, color_texto, True, 'center')


def _texto_valor(nodo):
    """Texto del valor de un nodo, con el símbolo de cota si aplica."""
    if nodo is None or 'valor' not in nodo:
        return ''
    cadena = tema.formato_valor(nodo['valor'])
    if nodo.get('cota') == '<=':
        return '≤' + cadena
    if nodo.get('cota') == '>=':
        return '≥' + cadena
    return cadena


# ----------------------------------------------------------------------
# Dibujo del árbol
# ----------------------------------------------------------------------
def dibujar_arbol(sup, rect, rep, titulo):
    """Dibuja el panel con la animación del proceso de búsqueda."""
    tema.panel(sup, rect, titulo)
    if rep is None:
        tema.texto(sup, 'Aquí se anima la búsqueda cuando juega un agente.',
                   rect.center, 13, tema.TEXTO_SUAVE, ancla='center')
        return
    geo = _geometria(rect)
    if rep.es_mcts:
        _dibujar_arbol_mcts(sup, rect, rep, geo)
    else:
        _dibujar_arbol_minimax(sup, rect, rep, geo)


def _etiquetas_niveles(sup, rect, geo, nombres):
    for y, nombre in zip((geo['y0'], geo['y1'], geo['y2'], geo['y3']),
                         nombres):
        tema.texto(sup, nombre, (rect.x + 12, y), 11, tema.TEXTO_SUAVE,
                   True, 'midleft')


def _dibujar_arbol_minimax(sup, rect, rep, geo):
    _etiquetas_niveles(sup, rect, geo, ('MAX', 'MIN', 'MAX', 'MIN'))
    en_camino = {rep.actual[:i] for i in range(len(rep.actual) + 1)}

    def color_arista(hijo):
        if hijo in rep.pv:
            return tema.NODO_MEJOR, 2
        if hijo in en_camino and rep.k < rep.total:
            return tema.NODO_ACTUAL, 2
        if rep.nodos[hijo].get('estado') == 'podado':
            return (127, 29, 29), 1
        return tema.BORDE, 1

    # Aristas
    for camino in rep.nodos:
        if len(camino) in (1, 2):
            color, grosor = color_arista(camino)
            pygame.draw.line(sup, color, _pos(geo, camino[:-1]),
                             _pos(geo, camino), grosor)
    # Nivel 2: los 49 nietos de la raíz
    for a in range(7):
        for b in range(7):
            _dibujar_nodo(sup, rep, (a, b), _pos(geo, (a, b)), 4)
    # Nivel 1: las 7 jugadas de la raíz
    for a in range(7):
        pos = _pos(geo, (a,))
        _dibujar_nodo(sup, rep, (a,), pos, 14, str(a))
        nodo = rep.nodos.get((a,))
        if nodo is not None and 'valor' in nodo:
            tema.texto(sup, _texto_valor(nodo), (pos[0], pos[1] + 24), 10,
                       tema.TEXTO, ancla='center')
    # Raíz
    pos = _pos(geo, ())
    _dibujar_nodo(sup, rep, (), pos, 15, 'R')
    raiz = rep.nodos.get(())
    if raiz is not None and 'valor' in raiz:
        tema.texto(sup, 'valor ' + _texto_valor(raiz),
                   (pos[0] + 24, pos[1]), 11, tema.TEXTO, ancla='midleft')
    # Nivel 3: sucesores del nodo de nivel 2 que se está viendo
    if rep.foco is not None and rep.foco in rep.nodos:
        origen = _pos(geo, rep.foco)
        hijos = [a for a in range(7) if rep.foco + (a,) in rep.nodos]
        for a in hijos:
            pygame.draw.line(sup, tema.PANEL_CLARO, origen,
                             _pos_detalle(geo, a), 1)
        for a in hijos:
            camino = rep.foco + (a,)
            pos = _pos_detalle(geo, a)
            _dibujar_nodo(sup, rep, camino, pos, 12, str(a))
            tema.texto(sup, _texto_valor(rep.nodos[camino]),
                       (pos[0], pos[1] + 21), 10, tema.TEXTO,
                       ancla='center')
        nombre = ' → '.join(str(c) for c in rep.foco)
        tema.texto(sup, f'Sucesores del nodo {nombre}',
                   (rect.right - 12, geo['y3'] - 30), 10, tema.TEXTO_SUAVE,
                   ancla='topright')
    _leyenda(sup, rect, [(tema.NODO_PENDIENTE, 'Frontera'),
                         (tema.NODO_ACTUAL, 'En expansión'),
                         (tema.NODO_EVALUADO, 'Evaluado'),
                         (tema.NODO_PODADO, 'Podado'),
                         (tema.NODO_MEJOR, 'Mejor línea')])


def _dibujar_arbol_mcts(sup, rect, rep, geo):
    _etiquetas_niveles(sup, rect, geo, ('MAX', 'MIN', 'MAX', ''))
    raiz = rep.nodos[()]
    total = max(raiz['n'], 1)
    en_camino = {rep.actual[:i] for i in range(len(rep.actual) + 1)}
    animando = rep.k < rep.total
    # Aristas
    for camino in rep.nodos:
        if len(camino) in (1, 2):
            if camino in en_camino and animando:
                color, grosor = tema.NODO_ACTUAL, 2
            elif camino in rep.pv:
                color, grosor = tema.NODO_MEJOR, 2
            else:
                color, grosor = tema.BORDE, 1
            pygame.draw.line(sup, color, _pos(geo, camino[:-1]),
                             _pos(geo, camino), grosor)
    # Nivel 2: el tamaño crece con las visitas
    maximo_2 = max([n['n'] for c, n in rep.nodos.items() if len(c) == 2]
                   + [1])
    for camino, nodo in rep.nodos.items():
        if len(camino) != 2:
            continue
        radio = 2 + int(round(3 * math.sqrt(nodo['n'] / maximo_2)))
        color = tema.NODO_ACTUAL if (camino in en_camino and animando) \
            else tema.NODO_EVALUADO
        pos = _pos(geo, camino)
        pygame.draw.circle(sup, color, (int(pos[0]), int(pos[1])), radio)
    # Nivel 1: una jugada por columna
    for a in range(7):
        pos = _pos(geo, (a,))
        x, y = int(pos[0]), int(pos[1])
        nodo = rep.nodos.get((a,))
        if nodo is None:
            pygame.draw.circle(sup, tema.PANEL_CLARO, (x, y), 10, 1)
            continue
        radio = 7 + int(round(11 * math.sqrt(nodo['n'] / total)))
        if (a,) in rep.pv:
            color = tema.NODO_MEJOR
        elif (a,) in en_camino and animando:
            color = tema.NODO_ACTUAL
        else:
            color = tema.NODO_EVALUADO
        pygame.draw.circle(sup, color, (x, y), radio)
        tema.texto(sup, str(a), (x, y), 12, tema.FONDO, True, 'center')
    # Raíz
    pos = _pos(geo, ())
    pygame.draw.circle(sup, tema.NODO_EVALUADO,
                       (int(pos[0]), int(pos[1])), 15)
    tema.texto(sup, 'R', pos, 12, tema.FONDO, True, 'center')
    tema.texto(sup, f'{raiz["n"]} simulaciones', (pos[0] + 24, pos[1]), 11,
               tema.TEXTO, ancla='midleft')
    # Barras con las visitas y la recompensa media de cada columna
    base = geo['y3'] + 36
    alto_max = 44
    maximo = max([rep.nodos[(a,)]['n'] for a in range(7)
                  if (a,) in rep.nodos] + [1])
    tema.texto(sup, 'Visitas (barra) y recompensa media de MAX por columna',
               (rect.right - 12, geo['y3'] - 46), 10, tema.TEXTO_SUAVE,
               ancla='topright')
    for a in range(7):
        x = _pos(geo, (a,))[0]
        nodo = rep.nodos.get((a,))
        if nodo is None:
            continue
        alto = max(2, alto_max * nodo['n'] / maximo)
        color = tema.NODO_MEJOR if (a,) in rep.pv else tema.NODO_EVALUADO
        pygame.draw.rect(sup, color, (x - 16, base - alto, 32, alto),
                         border_radius=3)
        tema.texto(sup, str(nodo['n']), (x, base - alto - 8), 10,
                   tema.TEXTO, ancla='center')
        media = nodo['w'] / max(nodo['n'], 1)
        tema.texto(sup, f'{media:.2f}', (x, base + 9), 10,
                   tema.TEXTO_SUAVE, ancla='center')
    _leyenda(sup, rect, [(tema.NODO_EVALUADO, 'Nodo (tamaño = visitas)'),
                         (tema.NODO_ACTUAL, 'Iteración actual'),
                         (tema.NODO_MEJOR, 'Más visitada')])


def _leyenda(sup, rect, elementos):
    x = rect.x + 12
    y = rect.bottom - 14
    for color, nombre in elementos:
        pygame.draw.circle(sup, color, (x + 5, y), 5)
        ancho = tema.texto(sup, nombre, (x + 14, y), 10, tema.TEXTO_SUAVE,
                           ancla='midleft').width
        x += ancho + 28


# ----------------------------------------------------------------------
# Estado interno del algoritmo
# ----------------------------------------------------------------------
def _nombre_camino(camino):
    """Nombre de un nodo: las columnas jugadas desde la raíz."""
    if len(camino) == 0:
        return 'raíz'
    if len(camino) > 4:
        inicio = ' → '.join(str(c) for c in camino[:2])
        return f'raíz → {inicio} → … → {camino[-1]} (prof. {len(camino)})'
    return 'raíz → ' + ' → '.join(str(c) for c in camino)


def descripcion_evento(rep):
    """Frase que explica el último paso del algoritmo."""
    e = rep.evento
    if e is None:
        return 'Inicio de la búsqueda.'
    if e['tipo'] == 'entra':
        quien = 'MAX' if e['es_max'] else 'MIN'
        return (f'Expandir nodo {quien}: se generan sus '
                f'{len(e["acciones"])} sucesores.')
    if e['tipo'] == 'hoja':
        valor = tema.formato_valor(e['valor'])
        if e['clase'] == 'terminal':
            return f'Estado terminal: utilidad real = {valor}.'
        if e['clase'] == 'corte':
            return f'Límite de profundidad: evaluación = {valor}.'
        return f'Subárbol explorado: devuelve el valor {valor}.'
    if e['tipo'] == 'sale':
        return (f'Nodo resuelto: valor {tema.formato_valor(e["valor"])}, '
                f'mejor jugada columna {e["mejor"]}.')
    if e['tipo'] == 'poda':
        columnas = ', '.join(str(a) for a in e['podadas']) or 'ninguna'
        return f'Poda alfa-beta: no se exploran las columnas {columnas}.'
    if e['tipo'] == 'iteracion':
        nombres = {1: 'gana MAX', 0.5: 'empate', 0: 'gana MIN'}
        return (f'Simulación aleatoria de {e["largo"]} jugadas: '
                f'{nombres[e["resultado"]]}. Se retropropaga.')
    return ''


def datos_estado_interno(rep):
    """Lista de parejas (nombre, valor) con el estado interno actual."""
    e = rep.evento
    paso = f'{rep.k} / {rep.total}'
    if e is None:
        return [('Paso', paso)]
    if rep.es_mcts:
        mejor = '-'
        hijos = [c for c in rep.nodos if len(c) == 1]
        if hijos:
            mejor = str(max(hijos, key=lambda c: rep.nodos[c]['n'])[0])
        return [
            ('Iteración', paso),
            ('Nodo seleccionado', _nombre_camino(e['seleccion'])),
            ('Nodo expandido', _nombre_camino(e['camino'])),
            ('Tamaño del árbol', tema.formato_numero(e['nodos_arbol'])),
            ('Nodos generados', tema.formato_numero(e['gen'])),
            ('Nodos expandidos', tema.formato_numero(e['exp'])),
            ('Profundidad del árbol', str(e['prof'])),
            ('Jugada más visitada', mejor),
        ]
    nodo = rep.nodos.get(rep.actual, {})
    return [
        ('Paso', paso),
        ('Nodo actual', _nombre_camino(rep.actual)),
        ('Valor del nodo', _texto_valor(nodo) or '-'),
        ('α (mejor de MAX)', tema.formato_valor(rep.alfa)),
        ('β (mejor de MIN)', tema.formato_valor(rep.beta)),
        ('Frontera visible', str(rep.frontera())),
        ('Nodos generados', tema.formato_numero(e['gen'])),
        ('Nodos expandidos', tema.formato_numero(e['exp'])),
        ('Podas', tema.formato_numero(e['podas'])),
        ('Profundidad máxima', str(e['prof'])),
    ]


def dibujar_estado_interno(sup, rect, rep):
    """Dibuja el panel con el estado interno del algoritmo."""
    tema.panel(sup, rect, 'ESTADO INTERNO DEL ALGORITMO')
    if rep is None:
        tema.texto(sup, 'Sin búsqueda en curso.', (rect.x + 12, rect.y + 34),
                   12, tema.TEXTO_SUAVE)
        return
    tema.texto(sup, descripcion_evento(rep), (rect.x + 12, rect.y + 30), 12,
               tema.NARANJA)
    datos = datos_estado_interno(rep)
    mitad = (len(datos) + 1) // 2
    ancho_columna = (rect.width - 24) // 2
    for i, (nombre, valor) in enumerate(datos):
        columna, fila = divmod(i, mitad)
        x = rect.x + 12 + columna * ancho_columna
        y = rect.y + 52 + fila * 17
        tema.texto(sup, nombre, (x, y), 11, tema.TEXTO_SUAVE)
        tema.texto(sup, valor, (x + ancho_columna - 14, y), 11, tema.TEXTO,
                   ancla='topright')


def fantasmas_de(rep, juego, maximo=6):
    """Fichas que muestran en el tablero la línea que se está analizando.

    Output: lista de (fila, columna, jugador, orden)
    """
    if rep is None or rep.k == 0 or rep.k >= rep.total:
        return []
    estado = rep.traza.estado_raiz
    fantasmas = []
    for orden, columna in enumerate(rep.actual[:maximo], start=1):
        if juego.es_terminal(estado) or estado[0, columna] != 0:
            break
        jugador = juego.player(estado)
        fila = int((estado[:, columna] == 0).sum()) - 1
        fantasmas.append((fila, columna, jugador, orden))
        estado = juego.resultado(estado, columna)
    return fantasmas
