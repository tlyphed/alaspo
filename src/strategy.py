
import random
import logging
logger = logging.getLogger('root')

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
        called after the finish of a move to allow for statistics and adaptability
        """
        pass


class RandomStrategy(AbstractStrategy):

    def prepare(self, relax_operators, search_operators):
        super().prepare(relax_operators, search_operators)

        relax_operators = []
        for op in self._relax_operators:
            relax_operators += op.flatten()
        self._relax_operators = relax_operators

        search_operators = []
        for op in self._search_operators:
            search_operators += op.flatten()
        self._search_operators = search_operators

        logger.debug('random strategy selected')
        logger.debug('relax operators: ' + str([ o.name() for o in relax_operators ]))
        logger.debug('search operators: ' + str([ o.name() for o in search_operators ]))

  
    def select_operators(self):
        """
        returns a random pair of relax and search operator
        """
        relax_operator = random.choice(self._relax_operators)
        search_operator = random.choice(self._search_operators)

        return relax_operator, search_operator

class RouletteStrategy(AbstractStrategy):
    
    def prepare(self, relax_operators, search_operators):
        super().prepare(relax_operators, search_operators)

        relax_operators = []
        for op in self._relax_operators:
            relax_operators += op.flatten()
        self._relax_operators = relax_operators

        search_operators = []
        for op in self._search_operators:
            search_operators += op.flatten()
        self._search_operators = search_operators
        
        self._weights = {}
        
        for r_op in self._relax_operators:
            for s_op in self._search_operators:
                self._weights[(r_op, s_op)] = 0
        
        self._to_initialize = True
        
        self._alpha = 0.5

        logger.debug('roulette strategy selected')
        logger.debug('relax operators: ' + str([ o.name() for o in relax_operators ]))
        logger.debug('search operators: ' + str([ o.name() for o in search_operators ]))

    def select_operators(self):
        """
        returns a pair of relax and search operators depending on the weights
        """        

        relax_operator, search_operator = random.choices(list(self._weights.keys()), list(self._weights.values()))[0]

        return relax_operator, search_operator
    
        
    def on_move_finished(self, operators, prev_cost, result, time_used):   
        
        if result.cost is not None:
            if self._to_initialize:
                for s_r_pair in self._weights:
                    self._weights[s_r_pair] = result.cost
                    
                self._to_initialize = False

            
            ratio = (result.cost - prev_cost) / time_used
            self.update_weights(operators, ratio)
            
        else:
            self.update_weights(operators, 0)
            
        print(self._weights.values())
    def update_weights(self, operators, ratio):

        self._weights[operators] = (1 - self._alpha) * self._weights[operators] - self._alpha * ratio 

# Strategy Factory

def get_strategy(type):
    """
    returns a new strategy of the given type
    """
    if type == 'random':
        return RandomStrategy()
    elif type == 'roulette':
        return RouletteStrategy()
    else:
        raise ValueError("no strategy '%s'" % type)