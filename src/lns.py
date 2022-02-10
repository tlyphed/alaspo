import time
import initial
import logging
logger = logging.getLogger('root')


class ClingoLNS:
    
    def __init__(self, internal_solver, program, initial_operator, relax_operators, search_operators, strategy):
        """
        instantiated the VLNS solver with required relax operators and the optional move timeout in seconds (default 5)
        """
        self.__internal_solver = internal_solver
        self.__program = program
        self._unsat_count = 0
        self._timeout_count = 0

        if initial_operator is None:
            raise ValueError('no initial operator provided')

        self.__initial_operator = initial_operator

        self.__strategy = strategy

        self.__strategy.prepare(relax_operators, search_operators)


    def solve(self, timeout):
        """
        runs the VLNS algorithm on the given ASP instance for the given timelimit
        """

        self._unsat_count = 0
        self._timeout_count = 0

        start_time = time.time()
        time_left = lambda: timeout - (time.time() - start_time)

        # get internal solver
        internal_solver = self.__internal_solver

        # load clear and program
        internal_solver.load_string(self.__program)

        # ground base
        internal_solver.ground()

        incumbent = None

        # obtain initial solution
        solution = self.__initial_operator.construct()

        if not isinstance(self.__initial_operator, initial.ClingoInitialOperator):
            # non default init operator was used, hence we seed the solver with the greedy solution 
            internal_solver.solve(assumptions=solution.model.symbols)

        if solution is None or not solution.sat:
            logger.info('COULD NOT FIND INITIAL SOLUTION')
            return None

        logger.info('initial cost: ' + str(solution.cost))

        incumbent = solution

        if solution.exhausted:
            logger.info('OPTIMAL SOLUTION FOUND')
            return incumbent

        global best_solution
        best_solution = incumbent

        # LNS loop
        assumptions = None
        while time_left() > 0:
            move_start_time = time.time()
            
            # get assumptions
            if assumptions is None or not self.__strategy.supports_intensification():
                relax_operator, search_operator = self.__strategy.select_operators()
                logger.debug('selected relax operator %s and search operator %s' % (relax_operator.name(), search_operator.name()))
                assumptions = relax_operator.get_move_assumptions(incumbent)
            # perform move
            solution = search_operator.execute(assumptions, time_left())

            prev_cost = incumbent.cost
            if solution.sat:
                # solution found, update incumbent
                incumbent = solution
                logger.info('found solution with cost: ' + str(incumbent.cost))
                if prev_cost == solution.cost:
                    assumptions = None
                self._unsat_count = 0
                self._timeout_count = 0
            else:
                # unsat or timeout, do not change incumbent and reset assumptions
                if solution.sat is False or solution.exhausted:
                    self._timeout_count = 0
                    if len(assumptions) == 0:
                        logger.info('OPTIMAL SOLUTION FOUND')
                        return incumbent
                    else:
                        logger.debug('unsat/optimal under current assumptions')
                        self._unsat_count += 1
                else:
                    logger.debug('move timed out')
                    self._unsat_count = 0
                    self._timeout_count += 1
                assumptions = None

            move_end_time = time.time()
            operators = (relax_operator, search_operator)
            self.__strategy.on_move_finished(operators, prev_cost, solution, move_end_time - move_start_time)

        return incumbent



        
        





