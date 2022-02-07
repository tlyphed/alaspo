
import random
import pprint
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

class JohannesStrategy(AbstractStrategy):
    
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
        
        self._current_relax_operator = random.choice(self._relax_operators)
        self._current_search_operator = random.choice(self._search_operators)
        
        self._strikes = 0

        logger.debug('johannes strategy selected')
        logger.debug('relax operators: ' + str([ o.name() for o in relax_operators ]))
        logger.debug('search operators: ' + str([ o.name() for o in search_operators ]))

  
    def select_operators(self):
        
        relax_operator = self._current_relax_operator
        search_operator = self._current_search_operator

        return relax_operator, search_operator

    def on_move_finished(self, operators, prev_cost, result, time_used):   

        """             
        LOOP:

        RUN LNS iteration with (S,N)

        CASES:
            1. Improvement found:
            -> Do nothing ("Never change a winning team!")

            2. UNSAT
            (do this only after 3 times in a row, "1st strike, 2nd strike, out!")
            (N cannot produce better solutions => size of N needs to be increased or
            type of N needs to be changed)
                -> INCREASE size for N to the next level; if there is none
                (S,N) = SELECT_NEW_PAIR() where type of S or type of N is different

            3. TIMEOUT:
            (do this only after 3 times in a row, "1st strike, 2nd strike, out!")
            (S cannot find better solutions => extensiveness of S needs to be
            increased or size of N needs to be decreased)
            -> DECIDE by coin flip:
                a) DECREASE size for N to the next level; if there is none
                (S,N) = SELECT_NEW_PAIR() where type of S or type of N is different

                b) INCREASE extensiveness of S to the next level; if there is none
                (S,N) = SELECT_NEW_PAIR() where type of S or type of N is different
        """
        if result.cost is not None:
            return
        elif not result.sat and result.exhausted:
            if self._strikes == 3:
                if not self._current_relax_operator.increase_size():
                    self._select_new_pair(operators)
                else:
                    self._strikes = 0
            else:
                self._strikes += 1
        else:
            if self._strikes == 3:
                if random.random() > 0.5:
                    if not self._current_relax_operator.decrease_size():
                        self._select_new_pair(operators)
                    else:
                        self._strikes = 0
                else:
                    if not self._current_search_operator.increase_size():
                        self._select_new_pair(operators)
                    else:
                        self._strikes = 0
            else:
                self._strikes += 1
                    
    def _select_new_pair(self, operators):
        print(operators)
        print(self._search_operators)
        
    
        filtered = list(filter(lambda so: type(so) == type(operators[0]), self._relax_operators))
        print(filtered)
        self._current_relax_operator = random.choice(filtered)
        self._current_search_operator = random.choice(self._search_operators)
        self._strikes = 0

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
            
        logger.debug('roulette weights: ' + pprint.pprint(self._weights))

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
    elif type == 'johannes':
        return JohannesStrategy()
    else:
        raise ValueError("no strategy '%s'" % type)