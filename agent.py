import pygame
import torch
import numpy as np
from flappy import Big_Game
from model import Linear_QNet, LR
import copy

pygame.init()

AGENTS_PER_GEN = 750
TAKE_BEST_MODEL_FOR_MUTATE = 100
SHOW_SCREEN_EVERY = 10
print(torch.cuda.is_available())

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Agent:

    def __init__(self, i):
        self.model = Linear_QNet(4, 2,device)
        self.i = i

    def get_action(self, state):
        state0 = torch.tensor(state, dtype=torch.float)
        prediction = self.model(state0)
        move = torch.argmax(prediction).item()
        return move

    def calc_fitness(self, score):
        self.model.fitness = score ** 2


def agents_for_new_gen_v1(agents, n, lr=LR):
    sum_fitness = sum([agent.model.fitness for agent in agents])
    if sum_fitness == 0:
        new_gen_agents = [copy.deepcopy(agent) for agent in
                          np.random.choice(agents, size=n)]
        for i in range(len(new_gen_agents)):
            new_gen_agents[i].model.mutate(lr)
    else:
        prob_to_be_parent = [agent.model.fitness / sum_fitness for agent in agents]
        new_gen_agents = [copy.deepcopy(agent) for agent in
                          np.random.choice(agents, size=n - 1, p=prob_to_be_parent)]
        for i in range(len(new_gen_agents)):
            new_gen_agents[i].model.mutate(lr)
        best_agent = agents[np.argmax(prob_to_be_parent)]
        new_gen_agents.append(best_agent)
    for val in range(len(new_gen_agents)):
        new_gen_agents[val].i = val
    return new_gen_agents


def agents_for_new_gen(agents, lr=LR):
    n = len(agents)
    new_gen_agents = [agent for agent in agents_from_learned_model(int(n / 2), lr)]
    new_gen_agents += agents_for_new_gen_v1(agents, n - int(n / 2), lr)
    for val in range(int(n / 2), n):
        new_gen_agents[val].i = val
    return new_gen_agents


def agents_from_learned_model(n, lr=LR):
    agents_list = [Agent(i) for i in range(n)]
    for agent in agents_list:
        agent.model.load()
        agent.model.mutate(lr)
    agents_list[0].model.load()
    return agents_list
    # new_gen_agents = [Agent(i) for i in range(n - 1)]
    # for agent in new_gen_agents:
    #     agent.model.load()
    #     agent.model.mutate(lr)
    # agent = Agent(n-1)
    # agent.model.load()
    # new_gen_agents.append(agent)
    # return new_gen_agents


def show_off_best_model(path):
    agents_list = [Agent(0)]
    agents_list[0].model.load(path)
    agents_alive = [0]
    game = Big_Game(1)
    while True:
        while len(agents_alive) > 0:
            old_states = {}
            final_moves = {}
            for i in agents_alive:
                # get old state
                old_states[i] = game.get_state(i)
                # get move
                final_moves[i] = agents_list[i].get_action(old_states[i])

            # perform move and get new state
            dones, scores = game.play_step(final_moves, agents_alive)

            if dones[0]:
                agents_alive.remove(0)
        print("score:", scores[0])
        agents_list = [Agent(0)]
        agents_list[0].model.load(path)
        agents_alive = [0]
        game = Big_Game(1)


def train():
    record = 0
    generation = 1
    agents_list = [Agent(i) for i in range(AGENTS_PER_GEN)]
    agents_alive = list(range(AGENTS_PER_GEN))
    game = Big_Game(AGENTS_PER_GEN)
    added_score = [False] * AGENTS_PER_GEN
    calculated_fitness_this_round = [False] * AGENTS_PER_GEN
    while True:
        if generation % SHOW_SCREEN_EVERY in [0, 1]:
            game.change_screen_condition()
        record_for_this_gen = 0
        mean_score = 0
        # clock.tick(fps)
        while len(agents_alive) > 0:
            old_states = {}
            final_moves = {}
            for i in agents_alive:
                # get old state
                old_states[i] = game.get_state(i)
                # get move
                final_moves[i] = agents_list[i].get_action(old_states[i])

            # perform move and get new state
            dones, scores = game.play_step(final_moves, agents_alive)

            if max(scores.values()) > 2200:
                agents_list[agents_alive[0]].model.save('model_easy_finished.pth')
                agents_alive = []

            for i in agents_alive:
                if dones[i] and not calculated_fitness_this_round[i]:
                    calculated_fitness_this_round[i] = True
                    agents_list[i].calc_fitness(scores[i])
                    if scores[i] > record:
                        record = scores[i]
                        agents_list[i].model.save()
                    if scores[i] > record_for_this_gen:
                        record_for_this_gen = scores[i]
                    if not added_score[i]:
                        added_score[i] = True
                        mean_score += scores[i]
                    agents_alive.remove(i)
        mean_score /= AGENTS_PER_GEN
        print("gen:", generation, "record for this gen:", record_for_this_gen, "mean score:", round(mean_score, 3),
              "record:",
              record)
        generation += 1
        if record > TAKE_BEST_MODEL_FOR_MUTATE:
            agents_list = agents_for_new_gen(agents_list)
        else:
            agents_list = agents_for_new_gen_v1(agents_list, AGENTS_PER_GEN)
        game.reset_game()
        agents_alive = list(range(AGENTS_PER_GEN))
        added_score = [False] * AGENTS_PER_GEN
        calculated_fitness_this_round = [False] * AGENTS_PER_GEN


def train_from_model(record):
    generation = 0
    agents_list = [Agent(i) for i in range(AGENTS_PER_GEN)]
    for agent in agents_list:
        agent.model.load()
        agent.model.mutate(LR)
    agents_alive = list(range(AGENTS_PER_GEN))
    game = Big_Game(AGENTS_PER_GEN)
    added_score = [False] * AGENTS_PER_GEN
    calculated_fitness_this_round = [False] * AGENTS_PER_GEN
    while True:
        record_for_this_gen = 0
        mean_score = 0
        # clock.tick(fps)
        while len(agents_alive) > 0:
            old_states = {}
            final_moves = {}
            for i in agents_alive:
                # get old state
                old_states[i] = game.get_state(i)
                # get move
                final_moves[i] = agents_list[i].get_action(old_states[i])

            # perform move and get new state
            dones, scores = game.play_step(final_moves, agents_alive)

            if max(scores.values()) >= 2200:
                agents_list[agents_alive[0]].model.save('model_easy_finished.pth')
                agents_alive = []
                record_for_this_gen = 2200

            for i in agents_alive:
                if dones[i] and not calculated_fitness_this_round[i]:
                    calculated_fitness_this_round[i] = True
                    agents_list[i].calc_fitness(scores[i])
                    if scores[i] > record:
                        record = scores[i]
                        agents_list[i].model.save()
                    if scores[i] > record_for_this_gen:
                        record_for_this_gen = scores[i]
                    if not added_score[i]:
                        added_score[i] = True
                        mean_score += scores[i]
                    agents_alive.remove(i)
        mean_score /= AGENTS_PER_GEN
        print("gen:", generation, "record for this gen:", record_for_this_gen, "mean score:", round(mean_score, 3),
              "record:",
              record)
        generation += 1
        agents_list = [Agent(i) for i in range(AGENTS_PER_GEN)]
        for agent in agents_list:
            agent.model.load()
            agent.model.mutate(LR)
        agents_alive = list(range(AGENTS_PER_GEN))
        game = Big_Game(AGENTS_PER_GEN)
        added_score = [False] * AGENTS_PER_GEN
        calculated_fitness_this_round = [False] * AGENTS_PER_GEN
        # agents_list = agents_from_learned_model(AGENTS_PER_GEN, lr)
        # game.reset_game()
        # agents_alive = list(range(AGENTS_PER_GEN))
        # added_score = [False] * AGENTS_PER_GEN
        # calculated_fitness_this_round = [False] * AGENTS_PER_GEN


if __name__ == '__main__':
    show_off_best_model("easy_finished")
