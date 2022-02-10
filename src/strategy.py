
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

class DynamicStrategy(AbstractStrategy):
    
    def __init__(self, unsat_strike_limit=3, timeout_strike_limit=1):
        self.__unsat_strike_limit = unsat_strike_limit
        self.__timeout_strike_limit = timeout_strike_limit


    def prepare(self, relax_operators, search_operators):
        super().prepare(relax_operators, search_operators)
        
        self.__current_relax_operator = random.choice(self._relax_operators)
        self.__current_search_operator = random.choice(self._search_operators)

        self.__unsat_strikes = 0
        self.__timeout_strikes = 0

        logger.debug('variable strategy selected')
        logger.debug('relax operators: ' + str([ o.name() for o in relax_operators ]))
        logger.debug('search operators: ' + str([ o.name() for o in search_operators ]))

  
    def select_operators(self):
        return self.__current_relax_operator, self.__current_search_operator


    def on_move_finished(self, operators, prev_cost, result, time_used):   
        if not result.sat:
            if result.exhausted:
                # UNSAT
                self.__unsat_strikes += 1
                if self.__unsat_strikes >= self.__unsat_strike_limit:
                    if not self.__current_relax_operator.increase_size():
                        self.__select_new_pair()
                    else:
                        self.__unsat_strikes = 0
                        logger.debug('increased relax size')
                
            else:
                # TIMEOUT
                self.__timeout_strikes += 1
                if self.__timeout_strikes >= self.__timeout_strike_limit:
                        if random.random() > 0.5:
                            # increase search time
                            if not self.__current_search_operator.increase_size():
                                self.__select_new_pair()
                            else:
                                self.__timeout_strikes = 0
                                logger.debug('increased search size')
                        else:
                            # reset relax size
                            self.__current_relax_operator.reset_size()
                            logger.debug('reset relax size')
        else:
            # IMPROVEMENT
            self.__unsat_strikes = 0
            self.__timeout_strikes = 0
                    
    def __select_new_pair(self):
        logger.debug('selecting new operators')
        if len(self._relax_operators) > 1:
            relax_choices = [ o for o in self._relax_operators if o != self.__current_relax_operator ]
            self.__current_relax_operator = random.choice(relax_choices)

        self.__current_search_operator = random.choice(self._search_operators)

        self.__current_relax_operator.reset_size()
        self.__current_search_operator.reset_size()
        self.__unsat_strikes = 0
        self.__timeout_strikes = 0

        logger.debug('relax operator: ' + self.__current_relax_operator.name())
        logger.debug('search operator: ' + self.__current_search_operator.name())

class RouletteStrategy(AbstractStrategy):

    def __init__(self, alpha=0.5, lex_weight=1000):
        self.__alpha = alpha
        self.__lex_weight = lex_weight
    
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
                self._weights[(r_op, s_op)] = 1
        
        self._to_initialize = True

        logger.debug('roulette strategy selected')
        logger.debug('relax operators: ' + str([ o.name() for o in relax_operators ]))
        logger.debug('search operators: ' + str([ o.name() for o in search_operators ]))

    def select_operators(self):
        """
        returns a pair of relax and search operators depending on the weights
        """        
        
        logger.debug('weights: ' + str([ ((r.name(), s.name()), self._weights[(r,s)]) for r, s in self._weights ]))
        logger.debug('cummulative sum of weights: ' + str(sum(self._weights.values())))
        
        relax_operator, search_operator = random.choices(list(self._weights.keys()), list(self._weights.values()))[0]

        return relax_operator, search_operator
    
        
    def on_move_finished(self, operators, prev_cost, result, time_used):   
        cost = result.cost

        if cost is not None:
            if type(cost) == list:
                cost = self.calculate_weighted_sum(cost)
                
            if type(prev_cost) == list:
                prev_cost = self.calculate_weighted_sum(prev_cost)
            
            if self._to_initialize:
                for s_r_pair in self._weights:
                    self._weights[s_r_pair] = cost
                    
                self._to_initialize = False

            ratio = (cost - prev_cost) / time_used
            self.update_weights(operators, ratio)
            
        else:
            self.update_weights(operators, 0)
            
        logger.debug('roulette weights: ' + str([ ((r.name(), s.name()), self._weights[(r,s)]) for r, s in self._weights ]))

    def update_weights(self, operators, ratio):
        new_weight = (1 - self.__alpha) * self._weights[operators] - self.__alpha * ratio
        if new_weight < 0.001:
            self._weights[operators] = 0.001
        else:    
            self._weights[operators] = new_weight
            
    def calculate_weighted_sum(self, list):
        size = len(list) - 1
        cost = 0
        for i in range(len(list)):
            cost += list[i]*(self.__lex_weight**(size-i))
        return cost

# Strategy Factory

def get_strategy(type, args):
    """
    returns a new strategy of the given type
    """    
    if type == 'random':
        return RandomStrategy()
    elif type == 'roulette':
        alpha = None
        if 'alpha' in args:
            alpha = args['alpha']
        lex_weight = None
        if 'lexWeight' in args:
            lex_weight = args['lexWeight']
        return RouletteStrategy(alpha=alpha, lex_weight=lex_weight)
    elif type == 'dynamic':
        unsat_strikes = None
        if 'unsatStrikes' in args:
            unsat_strikes = args['unsatStrikes']
        timeout_strikes = None
        if 'timeoutStrikes' in args:
            timeout_strikes = args['timeoutStrikes']
        return DynamicStrategy(unsat_strike_limit=unsat_strikes, timeout_strike_limit=timeout_strikes)
    else:
        raise ValueError("no strategy '%s'" % type)