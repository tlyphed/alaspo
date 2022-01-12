import time
import logging
import initial

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s [%(process)d:%(processName)s] %(module)s:%(lineno)d %(levelname)s: %(message)s')


class AbstractClingoLNS():
    
    def __init__(self, internal_solver, program, initial_operator, relax_operators, search_operators):
        '''
        instantiated the VLNS solver with required relax operators and the optional move timeout in seconds (default 5)
        '''
        self.__internal_solver = internal_solver
        self.__program = program
        self._unsat_count = 0
        self._timeout_count = 0

        if initial_operator == None:
            raise ValueError('no intial operator provided')

        self.__initial_operator = initial_operator

        if relax_operators == None or len(relax_operators) == 0: 
            raise ValueError('there has to be at least one relax operator')

        self._relax_operators = relax_operators    

        if search_operators == None or len(search_operators) == 0: 
            raise ValueError('there has to be at least one search operator')

        self._search_operators = search_operators      

    def _select_operators(self):
        '''
        selects and returns the next used relax+search operator combination
        '''
        pass
        
    def _on_move_finished(self, operators, prev_cost, result, time_used):
        '''
        called after every move and gives the used operators, the result of the move, previous cost and the time used by the move
        '''
        pass

    def solve(self, timeout):
        '''
        runs the VLNS algorithm on the given ASP instance for the given timelimit
        '''

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

        
        if solution == None or not solution.sat:
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
            # assumptions = None   # new neighbourhood every time!
            if assumptions == None:
                relax_operator, search_operator = self._select_operators()
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
                if solution.sat == False or solution.exhausted:
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
            self._on_move_finished(operators, prev_cost, solution, move_end_time - move_start_time)

        return incumbent



        
        





