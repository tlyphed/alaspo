
import random

class AbstractStrategy():

    def prepare(self, relax_operators, search_operators):
        """
        prepares the strategy by providing the (non-empty) lists of relax and search operators.
        needs to be called before the strategy is used
        """
        if relax_operators is None or len(relax_operators) == 0:
            raise ValueError('there has to be at least one relax operator')

        if search_operators is None or len(search_operators) == 0:
            raise ValueError('there has to be at least one search operator')

        self._relax_operators = relax_operators
        self._search_operators = search_operators

    def select_operators(self):
        """
        returns a pair of relax and search operator
        """
        pass

    def on_move_finished(self, operators, prev_cost, result, time_used):
        """
        called after the finish of a move allow for statistics and adaptability
        """
        pass


class RandomStrategy(AbstractStrategy):
  
    def select_operators(self):
        """
        returns a random pair of relax and search operator
        """
        relax_operator = random.choice(self._relax_operators)
        search_operator = random.choice(self._search_operators)

        return relax_operator, search_operator

