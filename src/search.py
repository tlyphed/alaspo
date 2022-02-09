
import random
import logging
logger = logging.getLogger('root')

class AbstractSearchOperator:

    def __init__(self, timeouts):
        """
        initializes the operator with a non-empty set of timeouts and an optional initial timeout
        """
        if len(timeouts) <= 0:
            raise ValueError('list of timeouts is empty')
        p = None
        for timeout in timeouts:
            if not 0 <= timeout:
                raise ValueError('timeout is negative')
            if p == None:
                p = timeout
            elif p >= timeout:
                raise ValueError('timeouts have to strictly increase')
        self.__timeouts = timeouts

        self.__current_index = 0
        self._timeout = self.__timeouts[self.__current_index]

    def increase_size(self):
        """
        increases the search time to the next defined timeout. 
        returns False if no increase is possible and True otherwise
        """
        if self.__current_index < len(self.__timeouts) - 1:
            self.__current_index += 1
            self._timeout = self.__timeouts[self.__current_index]
        else:
            return False

        return True

    def decrease_size(self):
        """
        decreases the search time to the next defined timeout. 
        returns False if no decrease is possible and True otherwise
        """
        if self.__current_index > 0:
            self.__current_index -= 1
            self._timeout = self.__timeouts[self.__current_index]
        else:
            return False

        return True

    def reset_size(self):
        """
        resets the size of the operator to the lowest value
        """
        self.__current_index = 0
        self._size = self._sizes[self.__current_index]

    def flatten(self):
        """
        returns a list of operators where each contains only one of the timeouts
        """
        operators = []

        for timeout in self.__timeouts:
            operators += [ type(self)(timeouts=[timeout]) ]

        return operators
    
    def execute(self, assumptions, time_left):
        pass

    def name(self):
        pass


class ClingoSearchOperator(AbstractSearchOperator):

    def __init__(self, internal_solver, timeouts, strict_bound_prob=1.0):
        super().__init__(timeouts)
        self.__timeouts = timeouts
        self.__strict_bound_prob = strict_bound_prob
        self.__internal_solver = internal_solver

    def execute(self, assumptions, time_left):
        timeout = min(self._timeout, time_left)
        logger.debug(f'operator executing search for {timeout} seconds')
        return self.__internal_solver.solve(timelimit=timeout, modellimit=1, assumptions=assumptions,
                                            strict_bound=self.__strict_bound_prob > random.random())

    def flatten(self):
        """
        overriding to inject the internal solver
        """
        operators = []

        for timeout in self.__timeouts:
            operators += [ ClingoSearchOperator(internal_solver=self.__internal_solver, timeouts=[timeout]) ]

        return operators

    def name(self):
        return 'default: ' + str(self.__timeouts)


# SearchOperator Factory

def get_operator(type, args, internal_solver):
    """
    returns a new search operator of the given type with given args
    """
    if type == 'default':
        timeouts = args['timeouts']
        return ClingoSearchOperator(internal_solver, timeouts)
    else:
        raise ValueError('no search operator "%s"' % type)