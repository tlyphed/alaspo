import argparse
import os.path
import sys
import time
from typing import Sequence
import clingo
import clingo.ast
import clingo.control
import clingo.theory
import clingodl
from clingo.symbol import Number
import clingcon

import logging
logger = logging.getLogger('root')


class Clingo:
    """ 
    presents the the api of clingo.Control in a different way.
    """

    def __init__(self, *, options=None, seed=None, heuristic=None, theory=None, forget_on_shot=False):

        # --forget-on-step=<opts>: Configure forgetting on(incremental) step
        # <opts>: < list {varScores | signs | lemmaScores | lemmas} > | < mask{0..15} >
        # "--opt-strategy=usc,3" for core guided optimization, see shift-scheduling paper
        clingoargs = []

        if forget_on_shot:
            clingoargs += ["--forget-on-step=varScores,signs,lemmaScores,lemmas"]

        if seed:
            # clingo only accepts unsigned 32bit seed:
            cseed = seed & ((1 << 32) - 1)
            cseed = str(cseed)
            logger.debug("cseed: %s", cseed)
            clingoargs.append(f"--seed={cseed}")

        if heuristic:
            clingoargs.append(f"--heuristic={heuristic}")

        # the normal clingo.Control object is used. it is ground by the
        # initial operator and can then be used by the other operators.
        if options:
            clingoargs += options

        def my_logger(m, msg):
            if m != clingo.MessageCode.Other:
                print(msg, file=sys.stderr)

        self._ctl = clingo.control.Control(clingoargs, logger=my_logger)

        self._theory = theory
        if self._theory is not None:
            self._theory.register(self._ctl)

    def supports_native_opt(self):
        return True

    def _timestamp(self):
        """
        returns a new timestamp object

        if changes here, also change CommonWorker._timestamp()!
        """
        return time.time()

    def _make_model(self, rawmodel):
        """helper method to make a long-lived copy of rawmodel.

        see clingo.Model, the return value somewhat mirrors it.
        """
        logger.debug("rawmodel: %s", rawmodel)
        model = argparse.Namespace()
        model.cost = rawmodel.cost.copy()
        model.number = rawmodel.number
        model.optimality_proven = rawmodel.optimality_proven
        model.thread_id = rawmodel.thread_id
        model.type = rawmodel.type
        model.symbols = list(rawmodel.symbols(atoms=True, terms=True, theory=True)).copy()
        model.shown = list(rawmodel.symbols(shown=True)).copy()
        model.assignments = {}

        return model

    def _read_cost(self, model):
        assert model
        if len(model.cost) == 1:
            return model.cost[0]

        return model.cost

    def _make_solution(self, result, model):
        """makes a solution object

        Returns:
            a pickleable object, with attributes:
             - sat
                True ... the logic program is proven to be satisfiable
                False ... the logic program is proven to be un-satisfiable
                None ... satisfiability was not proven
             - cost
                None ... the cost is undefined / unknown
                int ... this solution's cost
             - model
                None ... no answer set was found
                Model ... the found answer set
        """
        sol = argparse.Namespace()
        sol.sat = result.satisfiable if result else None
        sol.cost = self._read_cost(model) if model else None
        sol.model = model
        sol.exhausted = result.exhausted if result else None
        return sol

    def _ast_visitor(self, ast, pb):
        """
        called on the addition of a new ast node to the program
        """
        pass

    def load_files(self, inputfiles):
        """
        see clingo.Control.load(str)
        """
        logger.debug("loading files: %s", inputfiles)

        with clingo.ast.ProgramBuilder(self._ctl) as pb:
            def callback(ast):
                self._ast_visitor(ast, pb)
                self._theory.rewrite_ast(ast, pb.add) if self._theory else pb.add(ast)

            clingo.ast.parse_files(
                files=inputfiles,
                callback=callback)

    def load_string(self, inputstring):
        """
        see clingo.Control.load(str)
        """
        logger.debug("loading string")

        with clingo.ast.ProgramBuilder(self._ctl) as pb:
            def callback(ast):
                self._ast_visitor(ast, pb)
                self._theory.rewrite_ast(ast, pb.add) if self._theory else pb.add(ast)

            clingo.ast.parse_string(
                inputstring,
                callback=callback)

    def ground(self):
        """
        see clingo.Control.ground([("base", [])])
        """
        logger.debug("grounding 'base'")
        self._ctl.ground([("base", [])])

    def _collect_models_on_model(self, rawmodel, models):
        if self._theory:
            self._theory.on_model(model=rawmodel)

        models.append(self._make_model(rawmodel))

    def _add_bound_less_than(self, bound):
        """
        adds the given bound(s) to the program
        """
        assert bound is not None
        assert type(bound) == list or type(bound) == int

        bound_eff = None
        if type(bound) == list:
            bound_eff = bound.copy()
            bound_eff[-1] -= 1
        else:
            bound_eff = [bound - 1]

        logger.debug('added bound: ' + 'opt, ' + ', '.join([str(b) for b in bound_eff]))

        self._ctl.configuration.solve.opt_mode = 'opt, ' + ', '.join([str(b) for b in bound_eff])

    def solve(self, assumptions=[], timelimit=None, modellimit=None, strict_bound=True):
        """
        Args:
          assumptions ... iterable of symbols to assume to be true. en
              empty array is equivalent to no assumptions.
          timelimit ... time limit in seconds. clingo.Control will be kindly
              asked to take no more than this amount of seconds to return.
              The time limit is not externally enforced.
              A value of ``None`` means no time limit.
          modellimit ... the maximal number of models returned by the solver
              (default = None)

        Returns:
            a solution or None if timelimit exceeded
        """
        # execute solve, and keep a copy of all models.
        models = []
        on_model = lambda rawmodel: self._collect_models_on_model(
            rawmodel, models)
        assmpts = [(s, True) for s in assumptions]
        result = None

        n_models = 0
        if modellimit is not None:
            n_models = modellimit

        self._ctl.configuration.solve.models = n_models
        with self._ctl.solve(
                async_=True,
                assumptions=assmpts,
                on_model=on_model
        ) as solveHandle:

            finished = solveHandle.wait(timelimit)
            if not finished:
                solveHandle.cancel()

            result = solveHandle.get()
            # print(result)

        if result is not None and not result.unknown:
            if not result.satisfiable:
                # solve() determined UNSAT
                assert 0 == len(models)
                return self._make_solution(result=result, model=None)
            else:
                # => some result&model was found within timelimit
                assert result.satisfiable is True
                assert 1 <= len(models)
                model = models[len(models) - 1]
                solution = self._make_solution(result=result, model=model)
                bound = None
                if strict_bound:
                    bound = solution.cost
                else:
                    bound = solution.cost + 1
                self._add_bound_less_than(bound)
                return solution
        else:
            # timeout
            # Note: even if `models` contains some solution, it arrived
            # due to a race after the time was up.
            return self._make_solution(result=None, model=None)


class ClingoDl(Clingo):

    def __init__(self, *, options=None, seed=None, minimize_variable=None,
                 heuristic=None, forget_on_shot=False):

        self._theory = clingodl.ClingoDLTheory()

        super().__init__(options=options, seed=seed, heuristic=heuristic, theory=self._theory, forget_on_shot=forget_on_shot)

        self._minimize_variable = minimize_variable

        if self._minimize_variable:
            # if there is a minimization objective, we add the bound program module
            self._bound_id = 0
            part = f"#program bound(b). &diff {{ {self._minimize_variable} - 0 }} <= b."
            with clingo.ast.ProgramBuilder(self._ctl) as pb:
                clingo.ast.parse_string(
                    program=part,
                    callback=lambda ast: self._theory.rewrite_ast(ast, pb.add))

    def _make_model(self, rawmodel):
        model = super()._make_model(rawmodel)

        model.assignments = {}
        dl_assignments = []
        for dl_variable, dl_value in self._theory.assignment(rawmodel.thread_id):
            dl_assignments.append((str(dl_variable), dl_value))
        dl_assignments.sort()
        for dl_variable, dl_value in dl_assignments:
            model.assignments[str(dl_variable)] = dl_value

        return model

    def _read_cost(self, model):
        assert model
        cost = None
        if self._minimize_variable:
            for symb, value in model.assignments.items():
                if symb == self._minimize_variable:
                    cost = value
                    break
        else:
            logger.warning("no cost formula specified! (see options), "
                           "cost will be taken from clingo API.")
            cost = super()._read_cost(model)

        return cost

    def _add_bound_less_than(self, bound):
        """adds the given bound to the program

        the given bound is added to the logic program, such that the value of
        the minimize_variable (as named when invoking the constructor)
        MUST be LESS than the specified bound.

        this effect is currently  implemented via an additional difference
        constraint: ``&diff {variable - 0} <= boundeff.``
        In order to get "less-than" semantics while clingo-dl only supports
        the ``<=`` operator, the effective bound is: ``boundeff = bound - 1``
        """
        assert None != self._minimize_variable, ("cannot add a bound "
                                                 "without minimize_variable specified to constructor!")
        assert bound is not None
        boundeff = bound - 1
        # ground new bound
        self._ctl.ground([('bound', [Number(boundeff)])])
        logger.debug('added bound: ' + str(boundeff))

    def supports_native_opt(self):
        return False

    def solve(self, assumptions=[], timelimit=None, modellimit=None, strict_bound=True):
        logger.debug("solving for %is" % timelimit)

        if not self._minimize_variable:
            logger.debug('falling back to default clingo solve')
            # no clingo-dl minimization, defaulting to standard clingo solve
            return super().solve(assumptions=assumptions, timelimit=timelimit, modellimit=modellimit)
        else:
            self._ctl.configuration.solve.models = 1

            models = []
            on_model = lambda rawmodel: self._collect_models_on_model(
                rawmodel, models)
            assmpts = [(s, True) for s in assumptions]
            result = None
            solution = None

            starttime = self._timestamp()
            endtime = None
            if timelimit:
                endtime = starttime + timelimit

            logger.debug("starttime: %s", starttime)
            logger.debug("endtime: %s", endtime)

            result = None
            solution = None
            while (result is None or result.satisfiable) and (modellimit is None or len(models) < modellimit):
                nowtime = self._timestamp()
                if endtime:
                    timeleft = endtime - nowtime
                else:
                    timeleft = None

                with self._ctl.solve(
                        async_=True,
                        assumptions=assmpts,
                        on_model=on_model
                ) as solveHandle:

                    if solveHandle.wait(timeleft):
                        # not a timeout => retrieve the result
                        result = solveHandle.get()
                        assert result is not None
                        if result.satisfiable:
                            assert 1 <= len(models)
                            solution = self._make_solution(result=result, model=models[len(models) - 1])
                            if strict_bound:
                                bound = solution.cost
                            else:
                                bound = solution.cost + 1
                            self._add_bound_less_than(bound)
                    else:
                        solveHandle.cancel()
                        break
            
            if None != result:
                if result.satisfiable is False and len(models) == 0:
                    # UNSAT under given assumptions
                    return self._make_solution(result=result, model=None)
                else:
                    # there has to be some solution
                    assert solution is not None
                    if result.satisfiable is False:
                        solution.exhausted = True

                    return solution
            else:
                # timeout
                # Note: even if `models` contains some solution, it arrived
                # due to a race after the time was up.
                return self._make_solution(result=None, model=None)


class Clingcon(Clingo):

    def __init__(self, *, options=None, seed=None, heuristic=None, forget_on_shot=False):

        self._theory = clingcon.ClingconTheory()

        super().__init__(options=options, seed=seed, heuristic=heuristic,
                         theory=self._theory, forget_on_shot=forget_on_shot)

        self._minimize_atom = None

    def _make_model(self, rawmodel):
        model = super()._make_model(rawmodel)

        model.assignments = {}
        csp_assignments = []
        for csp_variable, csp_value in self._theory.assignment(rawmodel.thread_id):
            csp_assignments.append((str(csp_variable), csp_value))
        csp_assignments.sort()
        for csp_variable, csp_value in csp_assignments:
            model.assignments[str(csp_variable)] = csp_value

        return model

    def _read_cost(self, model):
        assert model

        for s in model.symbols:
            if s.match('__csp_cost', 1):
                return int(s.arguments[0].string)

        return super()._read_cost(model)

    def _ast_visitor(self, ast, pb):
        for item in ast.items():
            if item[0] == 'head':
                if item[1].ast_type == clingo.ast.ASTType.TheoryAtom:
                    if item[1].term.ast_type == clingo.ast.ASTType.Function:
                        if item[1].term.name == 'minimize':
                            if self._minimize_atom is not None:
                                raise Exception('multiple minimize directives are currently not supported!')
                            self._minimize_atom = item[1]
                        elif item[1].term.name == 'maximize':
                            raise Exception('maximize directives are not supported yet!')

    def load_files(self, inputfiles):
        super().load_files(inputfiles)
        if self._minimize_atom:
            with clingo.ast.ProgramBuilder(self._ctl) as pb:
                pos = clingo.ast.Position('<string>', 1, 1)
                loc = clingo.ast.Location(pos, pos)
                program = clingo.ast.Program(loc, 'bound', [clingo.ast.Id(loc, 'b')])
                term = clingo.ast.Function(loc, 'sum', [], 0)
                sequence = list(self._minimize_atom.elements).copy()
                guard = clingo.ast.TheoryGuard('<=',
                                               clingo.ast.SymbolicTerm(loc, clingo.symbol.Function('b', [], True)))
                sum_atom = clingo.ast.TheoryAtom(loc, term, sequence, guard=guard)
                rule = clingo.ast.Rule(loc, sum_atom, [])
                self._theory.rewrite_ast(program, pb.add)
                self._theory.rewrite_ast(rule, pb.add)

    def _add_bound_less_than(self, bound):
        if self._minimize_atom:
            boundeff = bound - 1
            # ground new bound
            self._ctl.ground([('bound', [Number(boundeff)])])
        else:
            super()._add_bound_less_than(bound)
