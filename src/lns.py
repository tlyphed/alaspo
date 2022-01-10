import time
import logging
import random

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s [%(process)d:%(processName)s] %(module)s:%(lineno)d %(levelname)s: %(message)s')

# keep track of best solution found so far
best_solution = None

class AbstractClingoLNS():
    
    def __init__(self, move_timeout=5, strict_bound_prob=1.0, use_greedy=True, pre_optimize_timeout=0, native_opt_in_move=False):
        '''
        instantiated the VLNS solver with the optional move timeout in seconds (default 5)
        '''
        self.__move_timeout = move_timeout
        self.__strict_bound_prob = strict_bound_prob
        self.__use_greedy = use_greedy
        self.__pre_optimize_timeout = pre_optimize_timeout
        self.__native_opt_in_move = native_opt_in_move
        self._unsat_count = 0
        self._timeout_count = 0        

    def _program(self):
        '''
        returns the problem encoding as a string containing an asp program
        '''
        pass

    def _instance_to_facts(self, instance):
        '''
        converts the given instance to a string consisting of asp facts
        '''
        pass

    def _construct_initial_solution(self, instance):
        '''
        returns the initial solution used in VLNS. if None, the algorithm will use the interal solver to obtain the initial solution.
        '''
        return None

    def _get_move_assumptions(self, instance, incumbent):
        '''
        returns the assumptions for the next VLNS move i.e. which parts of the solution are fixed
        '''
        pass

    def _solution_to_assumptions(self, solution):
        '''
        encodes a solution as assumptions which can be used by the internal solver
        '''
        pass

    def _model_to_solution(self, model, instance):
        '''
        transforms an ASP model into a solution
        '''
        pass

    def _internal_solver(self):
        '''
        returns a new instance of the internal solver to be used in VLNS
        '''
        pass

    def solve(self, instance, timeout):
        '''
        runs the VLNS algorithm on the given instance for the given timelimit
        '''

        self._unsat_count = 0
        self._timeout_count = 0

        start_time = time.time()
        time_left = lambda: timeout - (time.time() - start_time)

        # get internal solver
        internal_solver = self._internal_solver()

        # load clear and program
        internal_solver.load_string(self._program())
        
        # transform instance to asp facts
        input_facts = self._instance_to_facts(instance)

        # if the '_instance_to_facts' method is not implemented, the instance comes already parsed
        if not input_facts and instance:
            input_facts = instance

        if input_facts != None:
            # give facts to solver
            internal_solver.load_string(input_facts)

        # ground base
        internal_solver.ground()

        incumbent = None

        # obtain initial solution
        initial_assumptions = []
        if self.__use_greedy:
            initial_solution = self._construct_initial_solution(instance)
            if initial_solution != None:
                initial_assumptions = self._solution_to_assumptions(initial_solution)
                
        solution = None
        if self.__pre_optimize_timeout > 0:
            solution = internal_solver.solve(assumptions=initial_assumptions, timelimit=self.__pre_optimize_timeout)

        if solution == None:
            solution = internal_solver.solve(assumptions=initial_assumptions, modellimit=1, timelimit=time_left())

        if not solution.sat:
            return None
        logger.info('initial cost: ' + str(solution.cost))

        incumbent = self._model_to_solution(solution.model, instance)

        if solution.exhausted:
            logger.info('OPTIMAL SOLUTION FOUND')
            return incumbent

        global best_solution
        best_solution = incumbent

        # LNS loop
        assumptions = None
        while time_left() > 0:
            # get assumptions
            # assumptions = None   # new neighbourhood every time!
            if assumptions == None:
                assumptions = self._get_move_assumptions(instance, incumbent)
            # perform move
            if self.__move_timeout == -1:
                move_timeout = time_left()
            else:
                move_timeout = min(self.__move_timeout, time_left())

            if move_timeout <= 0:
                # preparing move used up remaining time, abort to avoid nontermination
                break

            if self.__native_opt_in_move and internal_solver.supports_native_opt():
                solution = internal_solver.solve(timelimit=move_timeout, assumptions=assumptions, strict_bound = self.__strict_bound_prob > random.random())
                assumptions = None
            else:
                solution = internal_solver.solve(timelimit=move_timeout, modellimit=1, assumptions=assumptions, strict_bound = self.__strict_bound_prob > random.random())

            if solution.sat:
                # solution found, update incumbent
                prev_cost = incumbent.cost
                incumbent = self._model_to_solution(solution.model, instance)
                logger.info('found solution with cost: ' + str(incumbent.cost))
                best_solution = incumbent
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

        return incumbent



        
        





