"""Paquete del proyecto: entorno 4 en raya y agentes de búsqueda adversaria."""
from conecta4.juego import Conecta4, VENTANAS, FILAS, COLUMNAS
from conecta4.agentes import (AgenteMinimax, AgenteAlfaBeta, AgenteMCTS,
                              AgenteAleatorio)

__all__ = ['Conecta4', 'VENTANAS', 'FILAS', 'COLUMNAS', 'AgenteMinimax',
           'AgenteAlfaBeta', 'AgenteMCTS', 'AgenteAleatorio']
