import random
import sys
import os
import argparse
import logging
import signal
from collections import namedtuple

import solver
import lns

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s [%(process)d:%(processName)s] %(module)s:%(lineno)d %(levelname)s: %(message)s')

select_pred = "_lns_select"
fix_pred = "_lns_fix"

Solution = namedtuple("Solution", "cost select fix atoms")


class ClingoVLNS(lns.AbstractClingoLNS):

    def __init__(self, asp_program, move_timeout, lns_size, lns_rate, solver_type,
                 solver_options, min_variable, pt, seed, forget_on_shot, native_opt_in_move,
                 min_lns_rate, max_lns_rate, change_threshold):
        self.program = asp_program
        self.lns_size = lns_size
        self.lns_rate = lns_rate
        self.solver_type = solver_type
        self.solver_options = solver_options
        self.min_variable = min_variable
        self.seed = seed
        self.__forget_on_shot = forget_on_shot
        self.__min_lns_rate = min_lns_rate
        self.__max_lns_rate = max_lns_rate
        self.__change_threshold = change_threshold

        super().__init__(move_timeout=move_timeout, strict_bound_prob=1, pre_optimize_timeout=pt, native_opt_in_move=native_opt_in_move)

    def _program(self):
        return self.program

    def _instance_to_facts(self, instance):
        return None

    def _construct_initial_solution(self, instance):
        return None

    def _model_to_solution(self, model, instance):
        cost = model.cost
        select = []
        fix = []

        for s in model.symbols:
            if s.match(select_pred, 1):
                select.append(s.arguments[0])
            elif s.match(fix_pred, 2):
                fix.append((s.arguments[0], s.arguments[1]))

        return Solution(cost, select, fix, model.shown)

    def _get_move_assumptions(self, instance, incumbent):
        asm = []
        max_selection_sz = len(incumbent.select)

        no_select = False
        if max_selection_sz == 0:
            max_selection_sz = len(incumbent.atoms)
            no_select = True

        if self.lns_size is None:
            assert 0 <= self.lns_rate <= 1
            if self.__change_threshold != None:
                if self._unsat_count > self.__change_threshold:
                    self.lns_rate = max(self.__min_lns_rate, self.lns_rate - 0.1)
                    self._unsat_count = 0
                    logger.debug('decreasing lns-rate to %f' % self.lns_rate)
                elif self._timeout_count > self.__change_threshold:
                    self.lns_rate = min(self.__max_lns_rate, self.lns_rate + 0.1)
                    self._timeout_count
                    logger.debug('increasing lns-rate to %f' % self.lns_rate)

            selection_sz = round(max_selection_sz * self.lns_rate)
        else:
            if self.lns_size > max_selection_sz:
                selection_sz = max_selection_sz
            elif 0 < self.lns_size <= max_selection_sz:
                selection_sz = self.lns_size
            elif -max_selection_sz <= self.lns_size < 0:
                selection_sz = max_selection_sz - abs(self.lns_size)
            else:
                selection_sz = 0

        if no_select:
            asm = random.sample(incumbent.atoms, selection_sz)
        else:
            selection = random.sample(incumbent.select, selection_sz)
            for sel in selection:
                for atom, s in incumbent.fix:
                    if sel == s:
                        asm.append(atom)

        logger.debug(f'neighbourhood: {selection_sz} / {max_selection_sz} elements = {len(asm)} atom.')

        return asm

    def _solution_to_assumptions(self, sol):
        return []

    def _internal_solver(self):
        if self.solver_type == 'clingo':
            return solver.Clingo(options=self.solver_options, seed=self.seed, forget_on_shot=self.__forget_on_shot)
        elif self.solver_type == 'clingo-dl':
            return solver.ClingoDl(options=self.solver_options, minimize_variable=self.min_variable, seed=self.seed, forget_on_shot=self.__forget_on_shot)
        elif self.solver_type == 'clingcon':
            return solver.Clingcon(options=self.solver_options, seed=self.seed, forget_on_shot=self.__forget_on_shot)
        else:
            assert False, "Not a valid solver type!"


def print_model(atoms):
    for a in atoms:
        print(a, end=' ')
    print(" ")


def main(input_program, global_timeout, move_timeout, lns_size, lns_rate, solver_type, solver_options,
         min_variable, pt, seed, forget_on_shot, native_opt_in_move, min_lns_rate, max_lns_rate, change_threshold):
    solver = ClingoVLNS(input_program, move_timeout, lns_size, lns_rate, solver_type, solver_options,
                            min_variable, pt, seed, forget_on_shot, native_opt_in_move, min_lns_rate, max_lns_rate, change_threshold)
    solution = solver.solve([], global_timeout)
    if solution is not None:
        print_model(solution.atoms)
        print("Costs: " + str(solution.cost))
    else:
        print("No solution found!")


if __name__ == '__main__':

    def existing_files(argument):
        if os.path.exists(argument) and os.path.isfile(argument):
            return argument
        else:
            raise argparse.ArgumentTypeError('File not found!')

    def valid_rate(argument):
        argument = float(argument)
        if 0 <= argument <= 1:
            return argument
        else:
            raise argparse.ArgumentTypeError('0 <= <n> <= 1 required!')


    def signal_handler(sig, frame):
        print('Search interrupted!')
        if lns.best_solution is not None:
            print_model(lns.best_solution.atoms)
            print("Costs: " + str(lns.best_solution.cost))
        else:
            print("No solution found!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='ASP + Large-Neighborhood Search')

    parser.add_argument('-i', '--input', type=existing_files, metavar='file', default=None, nargs='+',
                        help='input ASP files')

    parser.add_argument('-gt', '--time-limit', type=int, metavar='<n>', default=300,
                        help='time limit for the lns search')

    parser.add_argument('-mt', '--move-timeout', type=int, metavar='<n>', default=15,
                        help='time limit for individual solver calls')

    group = parser.add_mutually_exclusive_group()

    group.add_argument("-r", "--lns-rate", type=valid_rate, metavar='<n>', default=0.8,
                       help='rate of how many select-elements are fixed')

    group.add_argument("-s", "--lns-size", type=int, metavar='<n>', default=None,
                       help='number of select-elements to be fixed, ' 
                            'a negative value specifies the number of elements to be relaxed')

    parser.add_argument('-st', '--solver-type', type=str, choices=['clingo', 'clingo-dl', 'clingcon'],
                        metavar='<arg>', default='clingo',
                        help='the ASP solver ("clingo", "clingo-dl", "clingcon") to be used')

    parser.add_argument('-mv', '--minimize-variable', type=str, metavar='<var>', default=None,
                        help='an integer variable to minimize (only useful with solver type "clingo-dl")')

    parser.add_argument('-sa', '--solver-arguments', type=str, metavar='<args>', default='',
                        help='command-line argument string for the ASP solver ' 
                             '(separated by space)')

    parser.add_argument('-pt', '--pre-optimize-timeout', type=int, metavar='<n>', default=0,
                        help='let ASP solver optimize for <n> seconds before lns loop starts')

    parser.add_argument('-sd', '--seed', type=int, metavar='SEED', default=None,
                        help='seed for random numbers')

    parser.add_argument('-f', '--forget-on-shot', action='store_true', help='whether or not the previous state should be forgotten on each new lns iteration')
    parser.set_defaults(forget_on_shot=False)

    parser.add_argument('-no', '--native-opt-in-move', action='store_true', help='whether or not native optimization should be used in a move instead of only returning next best model (not supported by all solver backends)')
    parser.set_defaults(native_opt_in_move=False)

    parser.add_argument('-ct', '--change-threshold', type=int, metavar='<n>', default=None,
                        help='number of consecutive moves after which the lns-rate is adjusted')

    group.add_argument("--min-lns-rate", type=valid_rate, metavar='<n>', default=0.1,
                       help='the minimum lns-rate (only relevant if change threshold is set)')

    group.add_argument("--max-lns-rate", type=valid_rate, metavar='<n>', default=0.9,
                       help='the maximum lns-rate (only relevant if change threshold is set)')
    

    args = parser.parse_args()

    if args.seed == None:
        seed_value = random.randrange(sys.maxsize)
    else:
        seed_value = args.seed

    logger.info('Seed value: %i' % seed_value)

    random.seed(seed_value)

    parsed_options = None
    if args.solver_arguments:
        parsed_options = args.solver_arguments.split(' ')

    program = ''
    if args.input is not None:
        for asp_file in args.input:

            program += open(asp_file, 'r').read()
    else:
        program += sys.stdin.read()

    main(
        input_program=program,
        global_timeout=args.time_limit,
        move_timeout=args.move_timeout,
        lns_rate=args.lns_rate,
        lns_size=args.lns_size,
        solver_type=args.solver_type,
        solver_options=parsed_options,
        min_variable=args.minimize_variable,
        pt=args.pre_optimize_timeout,
        seed=seed_value,
        forget_on_shot=args.forget_on_shot, 
        native_opt_in_move=args.native_opt_in_move,
        min_lns_rate=args.min_lns_rate, 
        max_lns_rate=args.max_lns_rate, 
        change_threshold=args.change_threshold
    )
