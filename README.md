# clingo-lns

An LNS framework for the Potassco ASP solver suite.

The folder `src` contains the LNS implementation template as well a simple random relaxation-based problem-independent LNS. 
Should work out-of-the-box in a conda env after running the following command:
```
conda install -c potassco/label/dev clingo clingo-dl clingcon
```

The command-line options of the problem-independent LNS can be shown as follows:
```
python src/clingo-lns.py -h
```
