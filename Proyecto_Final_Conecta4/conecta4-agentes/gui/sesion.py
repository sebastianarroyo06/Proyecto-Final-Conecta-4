"""
Lógica de una partida en la interfaz (sin nada de dibujo).

``SesionPartida`` guarda el historial de jugadas y un cursor que indica
cuántas de ellas están aplicadas en el tablero. Gracias al cursor se
puede retroceder y volver a avanzar por la partida sin recalcular nada.

Las decisiones de los agentes se calculan en un hilo aparte para que la
ventana no se congele mientras el algoritmo "piensa".
"""
import threading
import traceback

from conecta4.agentes import BusquedaCancelada
from conecta4.config import crear_agente, describir
from conecta4.solver import SolverExacto


class Registro:
    """Una jugada de la partida con toda la información de su búsqueda."""

    def __init__(self, estado_antes, jugador, accion, es_humano,
                 descripcion, metricas=None, traza=None, cotas=None,
                 visitas=None):
        self.estado_antes = estado_antes
        self.jugador = jugador
        self.accion = accion
        self.es_humano = es_humano
        self.descripcion = descripcion
        self.metricas = metricas
        self.traza = traza
        self.cotas = cotas or {}        # Columnas cuyo valor es una cota
        self.visitas = visitas or {}    # Visitas por columna (MCTS)
        # ¿La jugada es óptima? True/False, o None si no se pudo verificar
        self.optima = None


class SesionPartida:
    """Partida entre dos jugadores (agentes o humanos)."""

    def __init__(self, juego, estado_inicial, config, semilla=0):
        """
        Input:
            - juego, objeto Conecta4
            - estado_inicial, tablero desde el que empieza la partida
            - config, diccionario {1: {...}, 2: {...}} donde cada jugador
              tiene 'tipo' ('humano', 'minimax', 'alfabeta' o 'mcts'),
              'nivel' ('facil', 'medio', 'dificil') y 'heuristica'
            - semilla, semilla de los generadores aleatorios
        """
        self.juego = juego
        self.config = config
        self.semilla = semilla
        self.historial = []                 # Lista de Registro
        self.estados = [estado_inicial]     # estados[i]: tras i jugadas
        self.cursor = 0                     # Jugadas aplicadas
        self.maximo = 0                     # Mayor cursor alcanzado
        self.pensando = False
        self.error = None
        self._agentes = {}
        self._agente_en_curso = None
        self._token = 0
        self._candado = threading.Lock()
        self.solver = SolverExacto(juego, limite_nodos=150000)
        self._candado_solver = threading.Lock()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def estado(self):
        """Tablero actual (después de las jugadas aplicadas)."""
        return self.estados[self.cursor]

    def jugador_en_turno(self):
        return self.juego.player(self.estado)

    def terminado(self):
        return self.juego.es_terminal(self.estado)

    def es_humano(self, jugador):
        return self.config[jugador]['tipo'] == 'humano'

    def es_turno_humano(self):
        return not self.terminado() and self.es_humano(self.jugador_en_turno())

    def descripcion(self, jugador):
        """Nombre del jugador: 'Humano' o el algoritmo con su parámetro."""
        c = self.config[jugador]
        if c['tipo'] == 'humano':
            return 'Humano'
        return describir(c['tipo'], c['nivel'], c['heuristica'])

    def pendiente(self):
        """Siguiente jugada ya calculada pero todavía no aplicada."""
        if self.cursor < len(self.historial):
            return self.historial[self.cursor]
        return None

    def ultimo(self):
        """Última jugada aplicada en el tablero."""
        if self.cursor > 0:
            return self.historial[self.cursor - 1]
        return None

    def aplicados(self):
        """Lista de las jugadas aplicadas en el tablero."""
        return self.historial[:self.cursor]

    # ------------------------------------------------------------------
    # Avanzar y retroceder
    # ------------------------------------------------------------------
    def aplicar_pendiente(self):
        if self.cursor < len(self.historial):
            self.cursor += 1
            self.maximo = max(self.maximo, self.cursor)

    def retroceder(self):
        if self.cursor > 0:
            self.cursor -= 1

    def ir_a(self, cursor):
        self.cursor = max(0, min(cursor, len(self.historial)))
        self.maximo = max(self.maximo, self.cursor)

    def _truncar(self):
        """Borra las jugadas posteriores al cursor (cambió el futuro)."""
        self.cancelar()
        del self.historial[self.cursor:]
        del self.estados[self.cursor + 1:]
        self.maximo = self.cursor

    # ------------------------------------------------------------------
    # Jugadas
    # ------------------------------------------------------------------
    def jugar_humano(self, columna):
        """Registra la jugada de un humano (sin aplicarla todavía)."""
        estado = self.estado
        if columna not in self.juego.acciones(estado):
            return None
        self._truncar()
        jugador = self.juego.player(estado)
        registro = Registro(estado, jugador, columna, True, 'Humano')
        self.historial.append(registro)
        self.estados.append(self.juego.resultado(estado, columna))
        hilo = threading.Thread(target=self._verificar, args=(registro,),
                                daemon=True)
        hilo.start()
        return registro

    def solicitar_decision(self):
        """Pide al agente en turno que calcule su jugada en otro hilo."""
        if (self.pensando or self.pendiente() is not None
                or self.terminado() or self.es_turno_humano()):
            return
        self.pensando = True
        self._token += 1
        estado = self.estado
        jugador = self.juego.player(estado)
        agente = self._agente(jugador)
        self._agente_en_curso = agente
        hilo = threading.Thread(target=self._trabajo,
                                args=(self._token, agente, estado, jugador),
                                daemon=True)
        hilo.start()

    def _agente(self, jugador):
        if jugador not in self._agentes:
            c = self.config[jugador]
            self._agentes[jugador] = crear_agente(
                self.juego, c['tipo'], c['nivel'], c['heuristica'],
                semilla=self.semilla + jugador)
        return self._agentes[jugador]

    def _trabajo(self, token, agente, estado, jugador):
        """Función que corre en el hilo: ejecuta la búsqueda del agente."""
        try:
            accion = agente.decidir(estado)
            registro = Registro(
                estado, jugador, int(accion), False, agente.descripcion(),
                metricas=agente.metricas, traza=agente.traza,
                cotas=dict(agente.cotas_acciones),
                visitas=dict(getattr(agente, 'visitas_acciones', {})))
            self._verificar(registro)
        except BusquedaCancelada:
            return
        except Exception:
            self.error = traceback.format_exc()
            self.pensando = False
            return
        with self._candado:
            if token == self._token:
                self.historial.append(registro)
                self.estados.append(self.juego.resultado(estado, accion))
                self.pensando = False

    def _verificar(self, registro):
        """Compara la jugada con el solucionador exacto (si la posición
        tiene pocas casillas vacías)."""
        with self._candado_solver:
            registro.optima = self.solver.es_optima(registro.estado_antes,
                                                    registro.accion)

    # ------------------------------------------------------------------
    # Cambios de configuración
    # ------------------------------------------------------------------
    def cancelar(self):
        """Detiene la búsqueda que esté corriendo en el hilo."""
        with self._candado:
            self._token += 1
            if self._agente_en_curso is not None:
                self._agente_en_curso.cancelar = True
            self.pensando = False

    def cambiar_config(self, config):
        """Cambia los jugadores a mitad de la partida: se conserva lo ya
        jugado y se descartan las jugadas posteriores al cursor."""
        self._truncar()
        self.config = config
        self._agentes = {}

    # ------------------------------------------------------------------
    # Métricas de la partida
    # ------------------------------------------------------------------
    def resumen(self, jugador):
        """Métricas acumuladas de las jugadas aplicadas de un jugador."""
        propios = [r for r in self.aplicados()
                   if r.jugador == jugador and r.metricas is not None]
        n = len(propios)
        if n == 0:
            return None
        ultimo = propios[-1].metricas
        return {
            'jugadas': n,
            'tiempo_ultimo': ultimo.tiempo,
            'tiempo_medio': sum(r.metricas.tiempo for r in propios) / n,
            'generados_ultimo': ultimo.nodos_generados,
            'expandidos_ultimo': ultimo.nodos_expandidos,
            'generados_medio': sum(r.metricas.nodos_generados
                                   for r in propios) / n,
            'memoria_max': max(r.metricas.memoria_max for r in propios),
            'podas_ultimo': ultimo.podas,
        }
