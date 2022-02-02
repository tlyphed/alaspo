
import random
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-15s [%(process)d:%(processName)s] %(module)s:%(lineno)d %(levelname)s: %('
                           'message)s')


class ClingoSearchOperator:

    def __init__(self, internal_solver, timeout, strict_bound_prob=1.0):
        self.__timeout = timeout
        self.__strict_bound_prob = strict_bound_prob
        self.__internal_solver = internal_solver

    def execute(self, assumptions, time_left):
        timeout = min(self.__timeout, time_left)
        logger.debug(f'operator executing search for {timeout} seconds')
        return self.__internal_solver.solve(timelimit=timeout, modellimit=1, assumptions=assumptions,
                                            strict_bound=self.__strict_bound_prob > random.random())

    def name(self):
        return '%is' % self.__timeout
