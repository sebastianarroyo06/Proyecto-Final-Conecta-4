"""
Funciones para comparar los algoritmos con métricas objetivas.

    jugar_partida     -> enfrenta dos agentes y registra las métricas de
                         cada jugada.
    comparar_jugada   -> ejecuta varios algoritmos sobre LA MISMA
                         instancia (un tablero) y compara sus métricas.
    torneo            -> todos contra todos entre varias configuraciones,
                         desde las mismas posiciones iniciales.

Las usan el modo de comparación de la interfaz gráfica, el notebook y el
script de experimentos del informe. Una "configuración" es un diccionario
como ``{'algoritmo': 'alfabeta', 'nivel': 'medio', 'heuristica': 'h1'}``.
"""
from conecta4.config import crear_agente, describir
from conecta4.solver import SolverExacto


def nombre_config(config: dict) -> str:
    """Nombre corto de una configuración, p.ej. 'Alfa-beta h1 d=5'."""
    if 'nombre' in config:
        return config['nombre']
    if config.get('parametro') is not None:
        algoritmo = config['algoritmo']
        if algoritmo == 'minimax':
            return f"Minimax d={config['parametro']}"
        if algoritmo == 'alfabeta':
            heuristica = config.get('heuristica', 'h1')
            return f"Alfa-beta {heuristica} d={config['parametro']}"
        if algoritmo == 'mcts':
            return f"MCTS N={config['parametro']}"
    return describir(config['algoritmo'], config.get('nivel', 'medio'),
                     config.get('heuristica', 'h1'))


def agente_desde_config(juego, config: dict, semilla: int = None):
    """Crea el agente descrito por una configuración."""
    agente = crear_agente(juego,
                          algoritmo=config['algoritmo'],
                          nivel=config.get('nivel', 'medio'),
                          heuristica=config.get('heuristica', 'h1'),
                          semilla=semilla,
                          parametro=config.get('parametro'))
    return agente


def jugar_partida(juego, agente_1, agente_2, estado_inicial=None,
                  guardar_traza: bool = False, al_jugar=None):
    """Juega una partida completa entre dos agentes.

    Input:
        - juego, objeto Conecta4
        - agente_1, agente que juega con las fichas del jugador 1
        - agente_2, agente que juega con las fichas del jugador 2
        - estado_inicial (opcional), tablero desde el que se empieza
        - guardar_traza, si se guarda la traza de cada búsqueda
        - al_jugar (opcional), función que se llama después de cada jugada
    Output:
        - diccionario con:
            'ganador': 0 (empate), 1 o 2
            'num_fichas': fichas en el tablero al terminar
            'jugadas': lista de columnas jugadas
            'registros': lista con las métricas de cada jugada
            'estado_final': tablero final
    """
    estado = juego.estado_inicial if estado_inicial is None else estado_inicial
    agentes = {1: agente_1, 2: agente_2}
    jugadas = []
    registros = []
    while not juego.es_terminal(estado):
        jugador = juego.player(estado)
        agente = agentes[jugador]
        agente.guardar_traza = guardar_traza
        accion = agente.decidir(estado)
        registro = agente.metricas.como_dict()
        registro['jugador'] = jugador
        registro['num_jugada'] = len(jugadas)
        registros.append(registro)
        jugadas.append(accion)
        estado = juego.resultado(estado, accion)
        if al_jugar is not None:
            al_jugar(estado, jugador, accion)
    return {
        'ganador': juego.ganador(estado),
        'num_fichas': int((estado != 0).sum()),
        'jugadas': jugadas,
        'registros': registros,
        'estado_final': estado,
    }


def resumir_registros(registros: list, jugador: int) -> dict:
    """Promedia las métricas de las jugadas de un jugador en una partida."""
    propios = [r for r in registros if r['jugador'] == jugador]
    n = max(len(propios), 1)
    return {
        'jugadas': len(propios),
        'tiempo_total': sum(r['tiempo'] for r in propios),
        'tiempo_medio': sum(r['tiempo'] for r in propios) / n,
        'generados_medio': sum(r['nodos_generados'] for r in propios) / n,
        'expandidos_medio': sum(r['nodos_expandidos'] for r in propios) / n,
        'memoria_max': max([r['memoria_max'] for r in propios] + [0]),
        'podas_medio': sum(r['podas'] for r in propios) / n,
    }


def comparar_jugada(juego, estado, configuraciones: list, semilla: int = 0,
                    solver: SolverExacto = None, progreso=None):
    """Ejecuta cada configuración sobre la misma instancia (tablero).

    Input:
        - juego, objeto Conecta4
        - estado, tablero no terminal sobre el que deciden todos
        - configuraciones, lista de diccionarios de configuración
        - semilla, semilla común para que el resultado sea reproducible
        - solver (opcional), SolverExacto para verificar optimalidad
        - progreso (opcional), función progreso(i, total)
    Output:
        - lista de diccionarios, uno por configuración, con las métricas
          de la decisión y las columnas:
            'optima': True/False, o None si no se pudo verificar
            'valor_exacto': valor minimax verdadero de la jugada elegida
    """
    if solver is None:
        solver = SolverExacto(juego)
    exactos = None
    if solver.se_puede_resolver(estado):
        try:
            exactos = solver.valores_acciones(estado)
        except Exception:
            exactos = None
    filas = []
    for i, config in enumerate(configuraciones):
        agente = agente_desde_config(juego, config, semilla)
        agente.guardar_traza = False
        accion = agente.decidir(estado)
        fila = agente.metricas.como_dict()
        fila['configuracion'] = nombre_config(config)
        if exactos is not None:
            fila['optima'] = exactos[accion] == max(exactos.values())
            fila['valor_exacto'] = exactos[accion]
        else:
            fila['optima'] = None
            fila['valor_exacto'] = None
        filas.append(fila)
        if progreso is not None:
            progreso(i + 1, len(configuraciones))
    return filas


def torneo(juego, configuraciones: list, aperturas: list, semilla: int = 0,
           progreso=None, cancelar=None):
    """Torneo todos contra todos.

    Cada par de configuraciones juega, desde cada apertura, dos partidas:
    una con cada configuración como jugador 1. Así todos los algoritmos
    se enfrentan sobre las mismas instancias y en igualdad de condiciones.

    Input:
        - juego, objeto Conecta4
        - configuraciones, lista de diccionarios de configuración
        - aperturas, lista de listas de jugadas iniciales, p.ej. [[], [3]]
        - semilla, semilla base (cada partida usa una semilla distinta
          derivada de esta, para que el torneo sea reproducible)
        - progreso (opcional), función progreso(hechas, total)
        - cancelar (opcional), función que devuelve True para detener
    Output:
        - lista de diccionarios, uno por partida
    """
    partidas = []
    pares = [(i, j) for i in range(len(configuraciones))
             for j in range(len(configuraciones)) if i != j]
    total = len(pares) * len(aperturas)
    hechas = 0
    for num_apertura, apertura in enumerate(aperturas):
        estado_inicial = juego.desde_jugadas(apertura)
        for i, j in pares:
            if cancelar is not None and cancelar():
                return partidas
            semilla_partida = semilla + 1000 * num_apertura + 10 * i + j
            agente_1 = agente_desde_config(juego, configuraciones[i],
                                           semilla_partida)
            agente_2 = agente_desde_config(juego, configuraciones[j],
                                           semilla_partida + 1)
            # El jugador 1 del torneo es quien mueve primero en la
            # apertura; si la apertura tiene un número impar de fichas,
            # el primero en mover es el jugador 2 del tablero.
            primero = juego.player(estado_inicial)
            if primero == 1:
                partida = jugar_partida(juego, agente_1, agente_2,
                                        estado_inicial)
                gana_i, gana_j = 1, 2
            else:
                partida = jugar_partida(juego, agente_2, agente_1,
                                        estado_inicial)
                gana_i, gana_j = 2, 1
            if partida['ganador'] == gana_i:
                resultado = 'primero'
            elif partida['ganador'] == gana_j:
                resultado = 'segundo'
            else:
                resultado = 'empate'
            fila = {
                'apertura': num_apertura,
                'primero': nombre_config(configuraciones[i]),
                'segundo': nombre_config(configuraciones[j]),
                'resultado': resultado,
                'num_fichas': partida['num_fichas'],
            }
            resumen_i = resumir_registros(partida['registros'], gana_i)
            resumen_j = resumir_registros(partida['registros'], gana_j)
            for llave, valor in resumen_i.items():
                fila[f'primero_{llave}'] = valor
            for llave, valor in resumen_j.items():
                fila[f'segundo_{llave}'] = valor
            partidas.append(fila)
            hechas += 1
            if progreso is not None:
                progreso(hechas, total)
    return partidas


def tabla_posiciones(partidas: list) -> list:
    """Resume un torneo: victorias, empates, derrotas y métricas medias
    de cada configuración.

    Output: lista de diccionarios ordenada por puntos (3 por victoria,
            1 por empate).
    """
    tabla = {}

    def fila_de(nombre):
        if nombre not in tabla:
            tabla[nombre] = {'configuracion': nombre, 'partidas': 0,
                             'victorias': 0, 'empates': 0, 'derrotas': 0,
                             'tiempo': 0.0, 'generados': 0.0,
                             'expandidos': 0.0, 'memoria_max': 0,
                             'fichas': 0}
        return tabla[nombre]

    for p in partidas:
        for rol, otro in (('primero', 'segundo'), ('segundo', 'primero')):
            fila = fila_de(p[rol])
            fila['partidas'] += 1
            if p['resultado'] == rol:
                fila['victorias'] += 1
            elif p['resultado'] == otro:
                fila['derrotas'] += 1
            else:
                fila['empates'] += 1
            fila['tiempo'] += p[f'{rol}_tiempo_medio']
            fila['generados'] += p[f'{rol}_generados_medio']
            fila['expandidos'] += p[f'{rol}_expandidos_medio']
            fila['memoria_max'] = max(fila['memoria_max'],
                                      p[f'{rol}_memoria_max'])
            fila['fichas'] += p['num_fichas']
    filas = []
    for fila in tabla.values():
        n = max(fila['partidas'], 1)
        filas.append({
            'configuracion': fila['configuracion'],
            'partidas': fila['partidas'],
            'victorias': fila['victorias'],
            'empates': fila['empates'],
            'derrotas': fila['derrotas'],
            'puntos': 3 * fila['victorias'] + fila['empates'],
            'tiempo_medio': fila['tiempo'] / n,
            'generados_medio': fila['generados'] / n,
            'expandidos_medio': fila['expandidos'] / n,
            'memoria_max': fila['memoria_max'],
            'fichas_medio': fila['fichas'] / n,
        })
    filas.sort(key=lambda f: (-f['puntos'], f['tiempo_medio']))
    return filas
