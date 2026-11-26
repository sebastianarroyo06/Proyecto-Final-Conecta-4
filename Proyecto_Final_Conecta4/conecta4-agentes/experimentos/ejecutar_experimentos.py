"""
Experimentos del informe (reproducibles).

Ejecutar desde la carpeta del proyecto:

    python experimentos/ejecutar_experimentos.py            # completo
    python experimentos/ejecutar_experimentos.py --rapido   # versión corta
    python experimentos/ejecutar_experimentos.py --figuras  # solo gráficas

Experimentos:
    E1 costo        -> costo de UNA jugada sobre las mismas instancias:
                       tiempo, nodos generados, expandidos y memoria
                       según la profundidad (o el número de simulaciones).
    E2 torneo       -> todos contra todos en nivel medio y en nivel
                       difícil, desde las mismas aperturas.
    E3 heuristicas  -> h1 contra h2 a igual profundidad.
    E4 optimalidad  -> porcentaje de jugadas óptimas en finales de
                       partida, comparando con el solucionador exacto.
    E5 dificultad   -> cada algoritmo contra sí mismo en otro nivel.

Todas las instancias, aperturas y agentes usan semillas fijas, de modo
que al repetir el script se obtienen los mismos resultados (los tiempos
cambian según el computador). Los datos quedan en
``experimentos/resultados`` (CSV) y las gráficas en
``experimentos/figuras`` (PNG).
"""
import argparse
import os
import random
import sys
import time
from multiprocessing import Pool

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from conecta4.agentes import AgenteAlfaBeta  # noqa: E402
from conecta4.config import NIVELES  # noqa: E402
from conecta4.experimentos import agente_desde_config  # noqa: E402
from conecta4.experimentos import jugar_partida, nombre_config  # noqa: E402
from conecta4.experimentos import resumir_registros  # noqa: E402
from conecta4.juego import Conecta4  # noqa: E402
from conecta4.solver import LimiteSuperado, SolverExacto  # noqa: E402

CARPETA_RESULTADOS = os.path.join(RAIZ, 'experimentos', 'resultados')
CARPETA_FIGURAS = os.path.join(RAIZ, 'experimentos', 'figuras')
SEMILLA = 2026


# ----------------------------------------------------------------------
# Instancias reproducibles
# ----------------------------------------------------------------------
def generar_aperturas(cantidad, semilla=SEMILLA):
    """Aperturas de dos jugadas (una por jugador) elegidas al azar con
    semilla. La primera apertura siempre es el tablero vacío."""
    juego = Conecta4()
    rng = random.Random(semilla)
    aperturas = [[]]
    while len(aperturas) < cantidad:
        apertura = juego.jugadas_aleatorias(2, rng)
        if apertura not in aperturas:
            aperturas.append(apertura)
    return aperturas


def generar_instancias_costo(por_tamano, semilla=SEMILLA):
    """Tableros aleatorios legales con 2, 6, 10, 14 y 18 fichas."""
    juego = Conecta4()
    rng = random.Random(semilla + 1)
    instancias = []
    for fichas in (2, 6, 10, 14, 18):
        for _ in range(por_tamano):
            instancias.append(juego.jugadas_aleatorias(fichas, rng))
    return instancias


def generar_finales(cantidad, semilla=SEMILLA):
    """Finales de partida (20 a 28 fichas) para medir la optimalidad.

    Para que las posiciones se parezcan a las de una partida real (y no
    tengan una victoria inmediata evidente), cada una se obtiene de una
    partida entre dos agentes alfa-beta de profundidad 2 que juegan al
    azar una de cada cuatro jugadas. Solo se conservan las posiciones
    que el solucionador exacto puede resolver y en las que NO todas las
    jugadas son óptimas.
    """
    juego = Conecta4()
    rng = random.Random(semilla + 2)
    agente = AgenteAlfaBeta(juego, max_lim=2, heuristica='h1')
    agente.guardar_traza = False
    finales = []
    while len(finales) < cantidad:
        fichas = rng.randint(20, 28)
        estado = juego.estado_inicial
        jugadas = []
        while len(jugadas) < fichas and not juego.es_terminal(estado):
            if len(jugadas) < 4 or rng.random() < 0.25:
                columna = rng.choice(juego.acciones(estado))
            else:
                columna = agente.decidir(estado)
            jugadas.append(columna)
            estado = juego.resultado(estado, columna)
        if juego.es_terminal(estado) or jugadas in [f[0] for f in finales]:
            continue
        solver = SolverExacto(juego, max_vacias=42, limite_nodos=200000)
        try:
            valores = solver.valores_acciones(estado)
        except LimiteSuperado:
            continue
        if len(set(valores.values())) > 1:
            # Se guarda la posición junto con el valor exacto de cada jugada
            finales.append((jugadas, valores))
    return finales


# ----------------------------------------------------------------------
# Tareas (cada una corre en un proceso aparte)
# ----------------------------------------------------------------------
def tarea_costo(args):
    """Una configuración decide una jugada sobre una instancia."""
    num_instancia, jugadas, config, semilla = args
    juego = Conecta4()
    estado = juego.desde_jugadas(jugadas)
    agente = agente_desde_config(juego, config, semilla)
    agente.guardar_traza = False
    agente.decidir(estado)
    fila = agente.metricas.como_dict()
    fila.update({'instancia': num_instancia, 'fichas': len(jugadas),
                 'familia': config['familia'],
                 'parametro': config['parametro'],
                 'configuracion': nombre_config(config)})
    return fila


def tarea_partida(args):
    """Una partida entre dos configuraciones desde una apertura par (el
    primero en mover es el jugador 1)."""
    experimento, config_1, config_2, apertura, semilla = args
    juego = Conecta4()
    agente_1 = agente_desde_config(juego, config_1, semilla)
    agente_2 = agente_desde_config(juego, config_2, semilla + 1)
    partida = jugar_partida(juego, agente_1, agente_2,
                            juego.desde_jugadas(apertura))
    resultado = {1: 'primero', 2: 'segundo', 0: 'empate'}[partida['ganador']]
    fila = {'experimento': experimento,
            'primero': nombre_config(config_1),
            'segundo': nombre_config(config_2),
            'apertura': ' '.join(str(c) for c in apertura),
            'semilla': semilla,
            'resultado': resultado,
            'num_fichas': partida['num_fichas']}
    for rol, jugador in (('primero', 1), ('segundo', 2)):
        resumen = resumir_registros(partida['registros'], jugador)
        for llave, valor in resumen.items():
            fila[f'{rol}_{llave}'] = valor
    return fila


def tarea_optimalidad(args):
    """Una configuración decide sobre un final y se compara su jugada
    con el solucionador exacto."""
    num_instancia, jugadas, valores, config, nivel, semilla = args
    juego = Conecta4()
    estado = juego.desde_jugadas(jugadas)
    agente = agente_desde_config(juego, config, semilla)
    agente.guardar_traza = False
    accion = agente.decidir(estado)
    mejor = max(valores.values())
    return {'instancia': num_instancia, 'fichas': len(jugadas),
            'configuracion': nombre_config(config),
            'algoritmo': config['etiqueta'], 'nivel': nivel,
            'semilla': semilla, 'accion': accion,
            'optima': valores[accion] == mejor,
            # ¿Conserva el resultado (ganar/empatar/perder) de la mejor?
            'conserva_resultado': ((valores[accion] > 0) == (mejor > 0)
                                   and (valores[accion] < 0) == (mejor < 0)),
            'tiempo': agente.metricas.tiempo,
            'nodos_generados': agente.metricas.nodos_generados}


def ejecutar(funcion, tareas, nombre, procesos):
    """Corre las tareas en paralelo y guarda el resultado en un CSV."""
    inicio = time.time()
    filas = []
    with Pool(procesos) as pool:
        for i, fila in enumerate(pool.imap_unordered(funcion, tareas), 1):
            filas.append(fila)
            if i % max(1, len(tareas) // 10) == 0:
                print(f'  {nombre}: {i}/{len(tareas)} '
                      f'({time.time() - inicio:.0f} s)', flush=True)
    datos = pd.DataFrame(filas)
    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    ruta = os.path.join(CARPETA_RESULTADOS, f'{nombre}.csv')
    datos.to_csv(ruta, index=False)
    print(f'{nombre}: {len(datos)} filas en {time.time() - inicio:.0f} s '
          f'-> {os.path.relpath(ruta, RAIZ)}', flush=True)
    return datos


# ----------------------------------------------------------------------
# Definición de los experimentos
# ----------------------------------------------------------------------
def configs_nivel(nivel, con_aleatorio=False):
    """Las cuatro configuraciones del proyecto en un nivel de dificultad."""
    configs = [
        {'algoritmo': 'minimax', 'nivel': nivel, 'etiqueta': 'Minimax'},
        {'algoritmo': 'alfabeta', 'nivel': nivel, 'heuristica': 'h1',
         'etiqueta': 'Alfa-beta h1'},
        {'algoritmo': 'alfabeta', 'nivel': nivel, 'heuristica': 'h2',
         'etiqueta': 'Alfa-beta h2'},
        {'algoritmo': 'mcts', 'nivel': nivel, 'etiqueta': 'MCTS'},
    ]
    if con_aleatorio:
        configs.append({'algoritmo': 'aleatorio', 'etiqueta': 'Aleatorio'})
    return configs


def experimento_costo(rapido, procesos):
    instancias = generar_instancias_costo(1 if rapido else 4)
    prof_minimax = range(1, 6 if rapido else 7)
    prof_alfabeta = range(1, 7 if rapido else 9)
    configs = []
    for d in prof_minimax:
        configs.append({'algoritmo': 'minimax', 'parametro': d,
                        'familia': 'Minimax'})
    for heuristica, familia in (('nula', 'Alfa-beta sin heurística'),
                                ('h1', 'Alfa-beta h1'),
                                ('h2', 'Alfa-beta h2')):
        for d in prof_alfabeta:
            configs.append({'algoritmo': 'alfabeta', 'parametro': d,
                            'heuristica': heuristica, 'familia': familia})
    for n in (200, 1000) if rapido else (200, 1000, 5000):
        configs.append({'algoritmo': 'mcts', 'parametro': n,
                        'familia': 'MCTS'})
    tareas = [(i, jugadas, config, SEMILLA)
              for i, jugadas in enumerate(instancias) for config in configs]
    return ejecutar(tarea_costo, tareas, 'e1_costo', procesos)


def experimento_torneo(rapido, procesos):
    tareas = []
    planes = [('medio', 3 if rapido else 8, True)]
    if not rapido:
        planes.append(('dificil', 3, False))
    for nivel, num_aperturas, con_aleatorio in planes:
        configs = configs_nivel(nivel, con_aleatorio)
        for k, apertura in enumerate(generar_aperturas(num_aperturas)):
            for i, config_1 in enumerate(configs):
                for j, config_2 in enumerate(configs):
                    if i != j:
                        semilla = SEMILLA + 1000 * k + 10 * i + j
                        tareas.append((f'torneo_{nivel}', config_1,
                                       config_2, apertura, semilla))
    return ejecutar(tarea_partida, tareas, 'e2_torneo', procesos)


def experimento_heuristicas(rapido, procesos):
    tareas = []
    aperturas = generar_aperturas(6 if rapido else 20, SEMILLA + 5)
    for d in (2, 4) if rapido else (2, 4, 6):
        h1 = {'algoritmo': 'alfabeta', 'parametro': d, 'heuristica': 'h1'}
        h2 = {'algoritmo': 'alfabeta', 'parametro': d, 'heuristica': 'h2'}
        for k, apertura in enumerate(aperturas):
            tareas.append((f'd={d}', h1, h2, apertura, SEMILLA + k))
            tareas.append((f'd={d}', h2, h1, apertura, SEMILLA + k))
    return ejecutar(tarea_partida, tareas, 'e3_heuristicas', procesos)


def experimento_optimalidad(rapido, procesos):
    finales = generar_finales(15 if rapido else 60)
    tareas = []
    for nivel in NIVELES:
        for config in configs_nivel(nivel):
            # Minimax (desempate al azar) y MCTS son aleatorios: se
            # repiten con varias semillas
            semillas = (0, 1, 2) if config['algoritmo'] != 'alfabeta' \
                else (0,)
            for i, (jugadas, valores) in enumerate(finales):
                for semilla in semillas:
                    tareas.append((i, jugadas, valores, config, nivel,
                                   semilla))
    aleatorio = {'algoritmo': 'aleatorio', 'etiqueta': 'Aleatorio'}
    for i, (jugadas, valores) in enumerate(finales):
        for semilla in (0, 1, 2):
            tareas.append((i, jugadas, valores, aleatorio, 'base', semilla))
    return ejecutar(tarea_optimalidad, tareas, 'e4_optimalidad', procesos)


def experimento_dificultad(rapido, procesos):
    tareas = []
    aperturas = generar_aperturas(2 if rapido else 6, SEMILLA + 9)
    pares = [('facil', 'medio')] if rapido else \
        [('facil', 'medio'), ('medio', 'dificil'), ('facil', 'dificil')]
    for base in configs_nivel('medio'):
        if base['algoritmo'] == 'alfabeta' and base['heuristica'] == 'h2':
            continue
        for bajo, alto in pares:
            config_bajo = dict(base, nivel=bajo)
            config_alto = dict(base, nivel=alto)
            for k, apertura in enumerate(aperturas):
                nombre = f"{base['etiqueta']}: {bajo} vs {alto}"
                tareas.append((nombre, config_bajo, config_alto, apertura,
                               SEMILLA + k))
                tareas.append((nombre, config_alto, config_bajo, apertura,
                               SEMILLA + k))
    return ejecutar(tarea_partida, tareas, 'e5_dificultad', procesos)


# ----------------------------------------------------------------------
# Tablas resumen y gráficas
# ----------------------------------------------------------------------
def posiciones_torneo(datos):
    """Tabla de posiciones de un torneo a partir de las partidas."""
    filas = {}
    for _, p in datos.iterrows():
        for rol, otro in (('primero', 'segundo'), ('segundo', 'primero')):
            fila = filas.setdefault(p[rol], {
                'configuracion': p[rol], 'partidas': 0, 'victorias': 0,
                'empates': 0, 'derrotas': 0, 'tiempo': 0.0,
                'generados': 0.0, 'expandidos': 0.0, 'memoria_max': 0,
                'fichas': 0})
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
    tabla = pd.DataFrame(filas.values())
    n = tabla['partidas']
    tabla['puntos'] = 3 * tabla['victorias'] + tabla['empates']
    tabla['pct_victorias'] = 100 * tabla['victorias'] / n
    tabla['tiempo_medio'] = tabla.pop('tiempo') / n
    tabla['generados_medio'] = tabla.pop('generados') / n
    tabla['expandidos_medio'] = tabla.pop('expandidos') / n
    tabla['fichas_medio'] = tabla.pop('fichas') / n
    return tabla.sort_values('puntos', ascending=False)


def generar_resumenes():
    """Crea las tablas resumen (CSV) que se citan en el informe."""
    def leer(nombre):
        return pd.read_csv(os.path.join(CARPETA_RESULTADOS, nombre + '.csv'))

    def guardar(tabla, nombre):
        ruta = os.path.join(CARPETA_RESULTADOS, nombre + '.csv')
        tabla.to_csv(ruta, index=False)
        print(f'\n== {nombre} ==')
        print(tabla.to_string(index=False))

    costo = leer('e1_costo')
    resumen = (costo.groupby(['familia', 'parametro'])
               [['tiempo', 'nodos_generados', 'nodos_expandidos',
                 'memoria_max', 'podas']].mean().reset_index())
    guardar(resumen.round(4), 'resumen_e1_costo')

    torneo = leer('e2_torneo')
    for nombre, grupo in torneo.groupby('experimento'):
        guardar(posiciones_torneo(grupo).round(4), f'resumen_e2_{nombre}')
    primero = (torneo.groupby('experimento')['resultado']
               .value_counts(normalize=True).mul(100).round(1)
               .rename('porcentaje').reset_index())
    guardar(primero, 'resumen_e2_quien_empieza')

    heur = leer('e3_heuristicas')
    filas = []
    for nombre, grupo in heur.groupby('experimento'):
        gana_h1 = ((grupo['primero'].str.contains('h1')
                    & (grupo['resultado'] == 'primero'))
                   | (grupo['segundo'].str.contains('h1')
                      & (grupo['resultado'] == 'segundo'))).sum()
        empates = (grupo['resultado'] == 'empate').sum()
        filas.append({'profundidad': nombre, 'partidas': len(grupo),
                      'gana_h1': gana_h1, 'empates': empates,
                      'gana_h2': len(grupo) - gana_h1 - empates})
    guardar(pd.DataFrame(filas), 'resumen_e3_heuristicas')

    optim = leer('e4_optimalidad')
    resumen = (optim.groupby(['algoritmo', 'nivel'])
               [['optima', 'conserva_resultado']].mean().mul(100).round(1)
               .reset_index())
    guardar(resumen, 'resumen_e4_optimalidad')

    dificultad = leer('e5_dificultad')
    filas = []
    for nombre, grupo in dificultad.groupby('experimento'):
        alto = nombre.split(' vs ')[1]
        # La configuración de nivel alto es la que tiene el parámetro mayor
        nombres = sorted(set(grupo['primero']) | set(grupo['segundo']),
                         key=lambda s: int(s.split('=')[1]))
        nombre_alto = nombres[-1]
        gana_alto = (((grupo['primero'] == nombre_alto)
                      & (grupo['resultado'] == 'primero'))
                     | ((grupo['segundo'] == nombre_alto)
                        & (grupo['resultado'] == 'segundo'))).sum()
        empates = (grupo['resultado'] == 'empate').sum()
        filas.append({'enfrentamiento': nombre, 'partidas': len(grupo),
                      'gana_nivel_alto': gana_alto, 'empates': empates,
                      'gana_nivel_bajo': len(grupo) - gana_alto - empates,
                      'nivel_alto': alto})
    guardar(pd.DataFrame(filas), 'resumen_e5_dificultad')


def generar_figuras():
    """Crea las gráficas del informe a partir de los CSV."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    os.makedirs(CARPETA_FIGURAS, exist_ok=True)
    plt.rcParams.update({'font.size': 9, 'axes.grid': True,
                         'grid.alpha': 0.3, 'axes.spines.top': False,
                         'axes.spines.right': False})
    colores = {'Minimax': '#2563eb', 'Alfa-beta sin heurística': '#64748b',
               'Alfa-beta h1': '#16a34a', 'Alfa-beta h2': '#ea580c',
               'MCTS': '#9333ea', 'Aleatorio': '#94a3b8'}

    def leer(nombre):
        return pd.read_csv(os.path.join(CARPETA_RESULTADOS, nombre + '.csv'))

    # Figura 1: nodos generados y tiempo según la profundidad
    costo = leer('e1_costo')
    busqueda = costo[costo['familia'] != 'MCTS']
    fig, ejes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for familia, grupo in busqueda.groupby('familia'):
        medias = grupo.groupby('parametro')[['nodos_generados',
                                             'tiempo']].mean()
        ejes[0].plot(medias.index, medias['nodos_generados'], marker='o',
                     ms=3.5, label=familia, color=colores[familia])
        ejes[1].plot(medias.index, medias['tiempo'], marker='o', ms=3.5,
                     label=familia, color=colores[familia])
    profundidades = sorted(busqueda['parametro'].unique())
    ejes[0].plot(profundidades, [7 ** d for d in profundidades], ':',
                 color='black', lw=1, label='$7^d$')
    ejes[0].plot(profundidades, [7 ** (d / 2) for d in profundidades], '--',
                 color='black', lw=1, label='$7^{d/2}$')
    ejes[0].set_yscale('log')
    ejes[1].set_yscale('log')
    ejes[0].set_xlabel('Profundidad límite d')
    ejes[1].set_xlabel('Profundidad límite d')
    ejes[0].set_ylabel('Nodos generados por jugada')
    ejes[1].set_ylabel('Tiempo por jugada (s)')
    ejes[0].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_FIGURAS, 'fig1_costo_profundidad.png'),
                dpi=200)
    plt.close(fig)

    # Figura 2: torneos (porcentaje de victorias, empates y derrotas)
    torneo = leer('e2_torneo')
    experimentos = sorted(torneo['experimento'].unique(), reverse=True)
    fig, ejes = plt.subplots(1, len(experimentos),
                             figsize=(3.6 * len(experimentos), 2.6),
                             squeeze=False)
    for eje, experimento in zip(ejes[0], experimentos):
        tabla = posiciones_torneo(torneo[torneo['experimento']
                                         == experimento])
        tabla = tabla.iloc[::-1]
        n = tabla['partidas']
        eje.barh(tabla['configuracion'], 100 * tabla['victorias'] / n,
                 color='#16a34a', label='Victorias')
        eje.barh(tabla['configuracion'], 100 * tabla['empates'] / n,
                 left=100 * tabla['victorias'] / n, color='#94a3b8',
                 label='Empates')
        eje.barh(tabla['configuracion'], 100 * tabla['derrotas'] / n,
                 left=100 * (tabla['victorias'] + tabla['empates']) / n,
                 color='#dc2626', label='Derrotas')
        nivel = {'medio': 'medio', 'dificil': 'difícil'}[
            experimento.split('_')[1]]
        eje.set_title(f'Torneo nivel {nivel}', fontsize=9)
        eje.set_xlabel('% de partidas')
        eje.set_xlim(0, 100)
        eje.grid(False)
    ejes[0][0].legend(fontsize=7, frameon=False, ncol=3,
                      loc='upper center', bbox_to_anchor=(0.5, -0.3))
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_FIGURAS, 'fig2_torneos.png'), dpi=200,
                bbox_inches='tight')
    plt.close(fig)

    # Figura 3: optimalidad en finales de partida
    optim = leer('e4_optimalidad')
    resumen = (optim[optim['nivel'] != 'base']
               .groupby(['algoritmo', 'nivel'])['optima'].mean().mul(100)
               .unstack()[['facil', 'medio', 'dificil']])
    resumen = resumen.loc[['Minimax', 'Alfa-beta h1', 'Alfa-beta h2',
                           'MCTS']]
    base = optim[optim['nivel'] == 'base']['optima'].mean() * 100

    def dibujar_optimalidad(eje):
        resumen.plot.bar(ax=eje, color=['#bfdbfe', '#60a5fa', '#1d4ed8'],
                         width=0.75, legend=False)
        linea = eje.axhline(base, color='black', ls='--', lw=1)
        eje.set_ylabel('% de jugadas óptimas')
        eje.set_xlabel('')
        eje.set_ylim(0, 100)
        eje.set_xticklabels([nombre.replace('Alfa-beta ', 'Alfa-beta\n')
                             for nombre in resumen.index], rotation=0)
        eje.grid(axis='x', visible=False)
        barras = eje.containers
        eje.legend([barras[0], barras[1], barras[2], linea],
                   ['Fácil', 'Medio', 'Difícil', 'Aleatorio'], fontsize=7,
                   frameon=False, ncol=4, loc='lower center',
                   bbox_to_anchor=(0.5, 1.0), columnspacing=1.0,
                   handlelength=1.5)

    fig, eje = plt.subplots(figsize=(4.6, 2.8))
    dibujar_optimalidad(eje)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_FIGURAS, 'fig3_optimalidad.png'),
                dpi=200)
    plt.close(fig)

    # Figura del informe: costo de la búsqueda y optimalidad, lado a lado
    fig, ejes = plt.subplots(1, 2, figsize=(7.2, 2.7))
    for familia, grupo in busqueda.groupby('familia'):
        medias = grupo.groupby('parametro')['nodos_generados'].mean()
        ejes[0].plot(medias.index, medias, marker='o', ms=3.5,
                     label=familia, color=colores[familia])
    ejes[0].plot(profundidades, [7 ** d for d in profundidades], ':',
                 color='black', lw=1, label='$7^d$')
    ejes[0].plot(profundidades, [7 ** (d / 2) for d in profundidades], '--',
                 color='black', lw=1, label='$7^{d/2}$')
    ejes[0].set_yscale('log')
    ejes[0].set_xlabel('Profundidad límite d')
    ejes[0].set_ylabel('Nodos generados por jugada')
    ejes[0].legend(fontsize=6.5, frameon=False)
    ejes[0].set_title('(a) Costo de la búsqueda', fontsize=9, y=1.12)
    dibujar_optimalidad(ejes[1])
    ejes[1].set_title('(b) Optimalidad en 60 finales', fontsize=9, y=1.12)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_FIGURAS, 'fig4_informe.png'), dpi=220)
    plt.close(fig)
    print(f'Figuras guardadas en {os.path.relpath(CARPETA_FIGURAS, RAIZ)}')


def main():
    analizador = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    analizador.add_argument('--rapido', action='store_true',
                            help='versión corta de los experimentos')
    analizador.add_argument('--figuras', action='store_true',
                            help='solo regenera tablas resumen y gráficas')
    analizador.add_argument('--procesos', type=int,
                            default=max(1, (os.cpu_count() or 2)),
                            help='procesos en paralelo')
    analizador.add_argument('--solo', default='',
                            help='lista separada por comas: costo,torneo,'
                                 'heuristicas,optimalidad,dificultad')
    args = analizador.parse_args()
    if not args.figuras:
        experimentos = {'costo': experimento_costo,
                        'torneo': experimento_torneo,
                        'heuristicas': experimento_heuristicas,
                        'optimalidad': experimento_optimalidad,
                        'dificultad': experimento_dificultad}
        elegidos = [e for e in args.solo.split(',') if e] or \
            list(experimentos)
        inicio = time.time()
        for nombre in elegidos:
            experimentos[nombre](args.rapido, args.procesos)
        print(f'Tiempo total: {time.time() - inicio:.0f} s')
    generar_resumenes()
    generar_figuras()


if __name__ == '__main__':
    main()
