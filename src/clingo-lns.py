import random
import sys
import os
import argparse
import logging
import signal
from collections import namedtuple

import solver
import lns
import relax

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-15s [%(process)d:%(processName)s] %(module)s:%(lineno)d %(levelname)s: %(message)s')

PREDICATE_SELECT = "_lns_select"
PREDICATE_FIX = "_lns_fix"

Solution = namedtuple("Solution", "cost select fix atoms")

current_incumbent = None

class ClingoLNS(lns.AbstractClingoLNS):

    def __init__(self, asp_program, relax_operators, move_timeout, solver_type,
                 solver_options, min_variable, pt, seed, forget_on_shot, native_opt_in_move):
        self.__solver_type = solver_type
        self.__solver_options = solver_options
        self.__min_variable = min_variable
        self.__seed = seed
        self.__forget_on_shot = forget_on_shot

        super().__init__(asp_program, relax_operators, move_timeout=move_timeout, strict_bound_prob=1, pre_optimize_timeout=pt, native_opt_in_move=native_opt_in_move)

    def _model_to_solution(self, model, instance):
        cost = model.cost
        select = []
        fix = []

        for s in model.symbols:
            if s.match(PREDICATE_SELECT, 1):
                select.append(s.arguments[0])
            elif s.match(PREDICATE_FIX, 2):
                fix.append((s.arguments[0], s.arguments[1]))

        current_incumbent = Solution(cost, select, fix, model.shown)

        return current_incumbent

    def _internal_solver(self):
        if self.__solver_type == 'clingo':
            return solver.Clingo(options=self.__solver_options, seed=self.__seed, forget_on_shot=self.__forget_on_shot)
        elif self.__solver_type == 'clingo-dl':
            return solver.ClingoDl(options=self.__solver_options, minimize_variable=self.__min_variable, seed=self.__seed, forget_on_shot=self.__forget_on_shot)
        elif self.__solver_type == 'clingcon':
            return solver.Clingcon(options=self.__solver_options, seed=self.__seed, forget_on_shot=self.__forget_on_shot)
        else:
            assert False, "Not a valid solver type!"


def print_model(atoms):
    for a in atoms:
        print(a, end=' ')
    print(" ")


def main(input_program, relax_operators, global_timeout, move_timeout, solver_type, solver_options,
         min_variable, pt, seed, forget_on_shot, native_opt_in_move):
    solver = ClingoLNS(input_program, relax_operators, move_timeout, solver_type, solver_options,
                            min_variable, pt, seed, forget_on_shot, native_opt_in_move)
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
        if current_incumbent is not None:
            print_model(current_incumbent.atoms)
            print("Costs: " + str(current_incumbent.cost))
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

    group.add_argument("-r", "--lns-rate", type=valid_rate, metavar='<n>', default=0.2,
                       help='rate of how many atoms are relaxed')

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

    relax_operators = []
    relax_operators += [ relax.RandomAtomRelaxOperator(args.lns_rate) ]


    main(
        input_program=program,
        relax_operators=relax_operators,
        global_timeout=args.time_limit,
        move_timeout=args.move_timeout,
        solver_type=args.solver_type,
        solver_options=parsed_options,
        min_variable=args.minimize_variable,
        pt=args.pre_optimize_timeout,
        seed=seed_value,
        forget_on_shot=args.forget_on_shot, 
        native_opt_in_move=args.native_opt_in_move
    )
