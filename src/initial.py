

import logging
logger = logging.getLogger('root')


class ClingoInitialOperator:

    def __init__(self, internal_solver, global_timeout, pre_opt_time=0):
        self.__timeout = global_timeout
        self.__internal_solver = internal_solver
        self.__pre_opt_time = pre_opt_time

    def construct(self):
        logger.debug(f'default initial operator executing for {self.__timeout} seconds')
        if self.__pre_opt_time > 0:
            return self.__internal_solver.solve(timelimit=min(self.__pre_opt_time, self.__timeout))
        else:
            return self.__internal_solver.solve(timelimit=self.__timeout, modellimit=1)
      