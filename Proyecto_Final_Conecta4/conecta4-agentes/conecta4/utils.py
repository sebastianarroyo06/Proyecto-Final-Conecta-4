'''
Clases para correr episodios de un juego contra otro jugador.

Vienen del módulo ``utils.py`` del taller de Juegos del curso:

    EnvfromGameAndPl2 -> convierte un juego y un segundo jugador
                         automático en un entorno con el método step().
    Episode           -> corre el entorno durante varias rondas y lleva
                         el registro de estados, acciones y recompensas.

Se conserva el código del curso; solo se quitaron las gráficas y las
dependencias que este proyecto no necesita.
'''
from copy import deepcopy
from time import sleep

import numpy as np
import pandas as pd


class EnvfromGameAndPl2:
    '''
    Implementa un entorno a partir de un juego y del segundo jugador.
    '''

    def __init__(self, game: any, other_player: any):
        self.other_player = other_player
        self.initial_game = deepcopy(game)
        self.game = game
        self.state = self.game.estado_inicial

    def reset(self):
        self.game = self.initial_game
        self.state = self.game.estado_inicial
        self.other_player.reset()
        self.other_player.states.append(self.state)
        return self.state

    def render(self):
        self.game.render(self.state)

    def test_objetivo(self, state):
        if not self.game.es_terminal(state):
            return False
        else:
            player = self.game.player(state)
            return self.game.utilidad(state, player) > 0

    def acciones_aplicables(self, state):
        return self.game.acciones(state)

    def step(self, action):
        state = self.state
        playing = self.game.player(state)
        # First player made a move. Get new state, reward, done
        new_state = self.game.resultado(state, action)
        reward = self.game.utilidad(new_state, playing)
        reward = reward if reward is not None else 0
        done = self.game.es_terminal(new_state)
        # If not done, second player makes a move
        if not done:
            # Actualize second player with previous move
            self.other_player.states.append(new_state)
            if hasattr(self.other_player, 'choices'):
                possible_actions = self.game.acciones(new_state)
                self.other_player.choices = possible_actions
            # Second player makes a move
            other_player_action = self.other_player.make_decision()
            # Get new state, reward, done
            new_state = self.game.resultado(new_state, other_player_action)
            # La recompensa siempre es la del primer jugador (el agente)
            reward = self.game.utilidad(new_state, playing)
            reward = reward if reward is not None else 0
            done = self.game.es_terminal(new_state)
        # Bookkeeping
        self.state = new_state
        return new_state, reward, done


class Episode:
    '''
    Runs the environment for a number of rounds and keeps tally of everything.
    '''

    def __init__(self, environment, agent, model_name: str, num_rounds: int,
                 id: int = 0):
        self.environment = environment
        self.agent = agent
        self.model_name = model_name
        self.num_rounds = num_rounds
        self.done = False
        self.T = 1
        self.id = id
        self.sleep_time = 0.3
        state = self.environment.reset()
        self.initial_state = state
        self.state = state
        if agent is not None:
            self.agent.restart()
            self.agent.states.append(state)

    def play_round(self, verbose: int = 0):
        '''
        Plays one round of the game.
        Input:
            - verbose, to print information.
        '''
        # Make sure agent has the appropriate possible actions
        if hasattr(self.agent, 'choices'):
            possible_actions = self.environment.acciones_aplicables(self.state)
            self.agent.choices = possible_actions
        # Ask agent to make a decision
        action = self.agent.make_decision()
        self.agent.actions.append(action)
        # Runs the environment and obtains the next_state, reward, done
        next_state, reward, done = self.environment.step(action)
        # Print info
        if verbose > 3:
            print(f'\tAgent takes action => {action}')
            print(f'\tThe reward obtained is => {reward}')
            print(f'\tEnvironment is finished? => {done}')
        self.agent.states.append(next_state)
        self.agent.rewards.append(reward)
        self.agent.dones.append(done)
        self.state = next_state
        self.T += 1
        self.done = done

    def run(self, verbose: int = 0):
        '''
        Plays the specified number of rounds.
        '''
        for round in range(self.num_rounds):
            if not self.done:
                if verbose > 2:
                    print('\n' + '-' * 10 + f'Round {round}' + '-' * 10 + '\n')
                self.play_round(verbose=verbose)
            else:
                break
        return self.to_pandas()

    def to_pandas(self) -> pd.DataFrame:
        '''
        Creates a pandas dataframe with the information from the current
        objects.
        Output:
            - pandas dataframe with the following variables:
                    * episode: a unique identifier for the episode
                    * round: the round number
                    * action: the player's action
                    * reward: the player's reward
                    * done: whether the environment is active or not
                    * model: the model's name
        '''
        # Include last item in actions list
        self.agent.actions.append(np.nan)
        data = {}
        data["episode"] = []
        data["round"] = []
        data["action"] = []
        data["reward"] = []
        data["done"] = []
        for r in range(self.T):
            data["episode"].append(self.id)
            data["round"].append(r)
            data["action"].append(self.agent.actions[r])
            data["reward"].append(self.agent.rewards[r])
            data["done"].append(self.agent.dones[r])
        df = pd.DataFrame.from_dict(data)
        df["model"] = self.model_name
        return df

    def reset(self):
        '''
        Reset the episode. This entails:
            reset the environment
            restart the agent
        '''
        state = self.environment.reset()
        self.initial_state = state
        self.state = state
        self.agent.restart()
        self.agent.states.append(state)
        self.T = 1
        self.done = False

    def renderize(self):
        '''
        Plays the specified number of rounds showing the board.
        '''
        from IPython.display import clear_output
        for round in range(self.num_rounds):
            if not self.done:
                self.play_round(verbose=0)
                clear_output(wait=True)
                self.environment.render()
                sleep(self.sleep_time)
            else:
                break

    def simulate(self, num_episodes: int = 1, file: str = None,
                 verbose: int = 0):
        '''
        Runs the specified number of episodes for the given number of rounds.
        Input:
            - num_episodes, int with the number of episodes.
            - file, string with the name of file to save the data on.
        Output:
            - Pandas dataframe with the information of all the episodes.
        '''
        # Create the list of dataframes
        data_frames = []
        # Run the number of episodes
        for ep in range(num_episodes):
            if verbose > 1:
                print('\n' + '=' * 10 + f'Episode {ep}' + '=' * 10 + '\n')
            # Reset the episode
            self.reset()
            self.id = ep
            # Run the episode
            df = self.run(verbose=verbose)
            # Include episode in list of dataframes
            data_frames.append(df)
        # Concatenate dataframes
        data = pd.concat(data_frames, ignore_index=True)
        if file is not None:
            data.to_csv(file)
        return data
