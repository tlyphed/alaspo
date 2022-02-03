
import random

class RandomStrategy():

    def prepare(self, relax_operators, search_operators):
        if relax_operators is None or len(relax_operators) == 0:
            raise ValueError('there has to be at least one relax operator')

        if search_operators is None or len(search_operators) == 0:
            raise ValueError('there has to be at least one search operator')
            
        self.__relax_operators = relax_operators
        self.__search_operators = search_operators

    def select_operators(self):
        relax_operator = random.choice(self.__relax_operators)
        search_operator = random.choice(self.__search_operators)

        return relax_operator, search_operator

    def on_move_finished(self, operators, prev_cost, result, time_used):
        pass