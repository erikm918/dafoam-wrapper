from dafoam import PYDAFOAM
from mpi4py import MPI
import numpy as np
import argparse
from pygeo import *
import os

parser = argparse.ArgumentParser()
parser.add_argument("--task", help="run calculations of CL, CD, CM", type=str, default="compute")
args = parser.parse_args()
comm = MPI.COMM_WORLD

'''
update mach, re, aoa -> check cl, cd, cm on simple case (e.g. basic naca airfoil)

plot and show QoI depending on Re, M, AoA
'''

# =======================================================================================================
# FFD set-up
# Can be ignored outside of testing.
# =======================================================================================================
def create_ffd(dat_file_path, ffd_file_path):
    print("Reading data from {}".format(dat_file_path))
    points = []
    with open(dat_file_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            x, y = map(float, line.split())
            points.append((x, y))
    f.close()

    print("Writing airfoil data to {}".format(ffd_file_path))
    with open(ffd_file_path, 'w') as f:
        for point in points:
            f.write(f"{point[0]} {point[1]} 0.0\n")

    print("FFD written to {}".format(ffd_file_path))

    return ffd_file_path

# =======================================================================================================
# Class for DAFoam initialization and running
# =======================================================================================================
class InitDAFoam:
    def __init__(self, aoa, p0, T0, ffd, **kwargs):
        # ==============================
        # Boundary conditions/initial conditions
        # ==============================
        self.aoa = aoa
        self.p0 = p0
        self.T0 = T0
        self.ffd = ffd
        self.nuTilda0 = 4.5e-5
        
        if "c" in kwargs:
            self.c = kwargs["c"]
        else:
            self.c = 1

        # Check kwargs for U0 definition
        if "Re" in kwargs:
            self.Re = kwargs["Re"]
            self.U0 = (self.Re * 1.57e-5) / self.c
        elif "M" in kwargs:
            self.M = kwargs["M"]
            self.U0 = self.M * np.sqrt(1.4 * 287.05 * self.T0)
        elif "U0" in kwargs:
            self.U0 = kwargs["U0"]

        # Check kwargs for DAFoam solver
        if "solverName" in kwargs:
            self.solverName = kwargs["solverName"]
        else:
            self.solverName = "DASimpleFoam"

        # ==============================
        # MPI and parser set-up
        # ==============================
        self.comm = comm
        self.parser = parser
        self.args = args

        # ==============================
        # Define DAFoam options
        # ==============================
        self.dafoam_options = {
            "solverName": self.solverName,
            "designSurfaces": ["airfoil"],
            "primalMinResTol": 1e-6,
            "primalBC": {
                "U0": {"variable": "U", "patches": ["inout"], "value": [self.U0, 0.0, 0.0]},
                "p0": {"variable": "p", "patches": ["inout"], "value": self.p0},
                "T0": {"variable": "T", "patches": ["inout"], "value": self.T0},
            },
            "function": {
                "CD": {
                    "part1": {
                        "type": "force",
                        "source": "pathToFace",
                        "patches": "airfoil",
                        "directionMode": "parallelToFlow",
                        "alphaName": "alpha",
                        "scale": 1
                    }
                },
                "CL": {
                    "part1": {
                        "type": "force",
                        "source": "pathToFace",
                        "patches": "airfoil",
                        "directionMode": "normalToFlow",
                        "alphaName": "alpha",
                        "scale": 1
                    }
                },
                "CM": {
                    "part1": {
                        "type": "force",
                        "source": "pathToFace",
                        "patches": "airfoil",
                        "momentAxis": [0.0, 0.0, 1.0],
                        "scale": 1
                    }
                }
            },
            "adjStateOrdering": "cell",
            "normalizeStates": {"U": self.U0, "p": self.p0, "nuTilda": self.nuTilda0 * 10.0, "phi": 1.0, "T": self.T0},
        }

    # ==============================
    # Run DAFoam for computation
    # ==============================
    def __call__(self):
        self.DASolver = PYDAFOAM(options=self.dafoam_options, comm=self.comm)
        self.DVGeo = self.set_geo()
        self.DASolver.setDVGeo(self.DVGeo)
        mesh = USMesh(options={"gridFile": os.getcwd(), "fileType": "OpenFOAM", "useRotations": False,
                               "symmetryPlanes": [[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]]]}, comm=self.comm)
        self.DASolver.setMesh(mesh)
        evalFuncs = ["CD", "CL", "CM"]
        self.DASolver.setEvalFuncs(evalFuncs)

        if args.task == "compute":
            self.DASolver()
            funcs = {}
            self.DASolver.evalFunctions(funcs, evalFuncs)
            results = [funcs["CD"], funcs["CL"], funcs["CM"]]
            if self.comm.rank == 0:
                print("Results: CD = {}, CL = {}, CM = {}".format(results[0], results[1], results[2]))
        else:
            print("task arg not found!")
            exit(0)

    # ==============================
    # FFD geometry set-up
    # ==============================
    def set_geo(self):
        DVGeo = DVGeometry(self.ffd)

        pts = DVGeo.getLocalIndex(0)
        indexList = pts[:, :, :].flatten()
        PS = geo_utils.PointSelect("list", indexList)

        DVGeo.addLocalDV("shape", lower=-1.0, upper=1.0, axis="y", scale=1.0, pointSelect=PS)
        self.dafoam_options["designVar"]["shape"] = {"designVarType": "FFD"}

        # Function to set angle of attack
        def setAoA(val, geo):
            aoa = val[0] * np.pi / 180.0
            inletU = [float(self.U0 * np.cos(aoa)), float(self.U0 * np.sin(aoa)), 0]
            self.DASolver.setOption("primalBC", {"U0": {"variable": "U", "patches": ["inout"], "value": inletU}})
            self.DASolver.updateDAOption()

        # Add global design variable for AoA
        DVGeo.addGlobalDV("AoA", [self.aoa], setAoA, lower=-5.0, upper=15.0, scale=1.0)
        self.dafoam_options["designVar"]["AoA"] = {"designVarType": "global"}

        return DVGeo

if __name__ == "__main__":
    ffd_file = "airfoil.xyz"

    dafoam_solver = InitDAFoam(0.0, 101325.0, 300.0, ffd_file, Re=1e6)
    dafoam_solver()