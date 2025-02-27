#!/usr/bin/env python
"""
DAFoam run script for the NACA0012 airfoil at low-speed with customizable Reynolds number and aoa0
and using an FFD file for the reference airfoil
"""

# =============================================================================
# Imports
# =============================================================================
import os
import argparse
import numpy as np
from mpi4py import MPI
import openmdao.api as om
from mphys.multipoint import Multipoint
from dafoam.mphys import DAFoamBuilder, OptFuncs
from mphys.scenario_aerodynamic import ScenarioAerodynamic
from pygeo import DVGeometry
from genNACA import generate_xyz_file

# =============================================================================
# Argument Parsing
# =============================================================================
parser = argparse.ArgumentParser()
# input values for Reynolds number and aoa0
parser.add_argument("-Re", help="Reynolds number", type=float, required=True)
parser.add_argument("-aoa0", help="angle of attack in degrees", type=float, required=True)
parser.add_argument("-output", help="output file to save results", type=str, default="results.txt")
parser.add_argument('-gen_ffd', help='Generates FFD of NACA0012 airfoil', type=bool, default=False)
args = parser.parse_args()

# =============================================================================
# Constants
# =============================================================================
rho = 1.225  # Density of air in kg/m^3
mu = 1.7894e-5  # Dynamic viscosity of air in kg/(m·s)

p0 = 101325
nuTilda0 = 4.5e-5
A0 = 0.1
# rho is used for normalizing CD and CL
rho0 = 1

def run_DAFoam(Re, aoa0, **kwargs):
    if args.gen_ffd:
        if 'file_name' in kwargs:
            file_name = kwargs['file_name']
        else:
            file_name = 'naca0012.xyz'
        if 'x_num' in kwargs:
            x_num = kwargs['x_num']
        else:
            x_num = 15
        if 'z_num' in kwargs:
            z_num = kwargs['z_num']
        else:
            z_num = 2
        if 'cord_length' in kwargs:
            cord_length = kwargs['cord_length']
        else:
            cord_length = 1
        if 'y_num' in kwargs:
            y_num = kwargs['y_num']
        else:
            y_num = 2
        
        
        generate_xyz_file(file_name, x_num, z_num, cord_length, y_num)
    
    # Calculate U0 from Reynolds number
    U0 = (Re * mu) / (rho * cord_length)
    
    # Input parameters for DAFoam
    daOptions = {
        "designSurfaces": ["wing"],
        "solverName": "DASimpleFoam",
        "primalMinResTol": 1.0e-4,
        "primalBC": {
            "U0": {"variable": "U", "patches": ["inout"], "value": [U0, 0.0, 0.0]},
            "p0": {"variable": "p", "patches": ["inout"], "value": [p0]},
            "nuTilda0": {"variable": "nuTilda", "patches": ["inout"], "value": [nuTilda0]},
            "useWallFunction": True,
        },
        "objFunc": {
            "CD": {
                "part1": {
                    "type": "force",
                    "source": "patchToFace",
                    "patches": ["wing"],
                    "directionMode": "parallelToFlow",
                    "alphaName": "aoa",
                    "scale": 1.0 / (0.5 * U0 * U0 * A0 * rho0),
                    "addToAdjoint": True,
                }
            },
            "CL": {
                "part1": {
                    "type": "force",
                    "source": "patchToFace",
                    "patches": ["wing"],
                    "directionMode": "normalToFlow",
                    "alphaName": "aoa",
                    "scale": 1.0 / (0.5 * U0 * U0 * A0 * rho0),
                    "addToAdjoint": True,
                }
            },
            "CM": {
                "part1": {
                    "type": "moment",
                    "source": "patchToFace",
                    "patches": ["wing"],
                    "axis": [0.0, 0.0, 1.0],
                    "center": [0.25, 0.0, 0.0],
                    "scale": 1.0 / (0.5 * U0 * U0 * A0 * 0.1 * rho0),
                    "addToAdjoint": True,
                }
            },
        },
        "adjEqnOption": {"gmresRelTol": 1.0e-6, "pcFillLevel": 1, "jacMatReOrdering": "rcm"},
        "normalizeStates": {
            "U": U0,
            "p": U0 * U0 / 2.0,
            "nuTilda": nuTilda0 * 10.0,
            "phi": 1.0,
        },
        "designVar": {
            "aoa": {"designVarType": "AOA", "patches": ["inout"], "flowAxis": "x", "normalAxis": "y"},
        },
    }

    # Mesh deformation setup
    meshOptions = {
        "gridFile": os.getcwd(),
        "fileType": "OpenFOAM",
        # point and normal for the symmetry plane
        "symmetryPlanes": [[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]], [[0.0, 0.0, 0.1], [0.0, 0.0, 1.0]]],
    }

    # Initialize the DVGeometry object with the FFD file
    DVGeo = DVGeometry(file_name)

    # Top class to setup the problem
    class Top(Multipoint):
        def setup(self):

            # create the builder to initialize the DASolvers
            dafoam_builder = DAFoamBuilder(daOptions, meshOptions, scenario="aerodynamic")
            dafoam_builder.initialize(self.comm)

            # add the design variable component to keep the top level design variables
            self.add_subsystem("dvs", om.IndepVarComp(), promotes=["*"])

            # add the mesh component
            self.add_subsystem("mesh", dafoam_builder.get_mesh_coordinate_subsystem())

            # add a scenario (flow condition) for calculation, we pass the builder
            # to the scenario to actually run the flow and adjoint
            self.mphys_add_scenario("cruise", ScenarioAerodynamic(aero_builder=dafoam_builder))

            # need to manually connect the x_aero0 between the mesh and cruise scenario group
            self.connect("mesh.x_aero0", "cruise.x_aero")

        def configure(self):
            # configure and setup perform a similar function, i.e., initialize the calculation.
            # But configure will be run after setup

            # add the objective function to the cruise scenario
            self.cruise.aero_post.mphys_add_funcs()

            # get the surface coordinates from the mesh component
            points = self.mesh.mphys_get_surface_mesh()

            # define an angle of attack function to change the U direction at the far field
            def aoa(val, DASolver):
                aoa = val[0] * np.pi / 180.0
                U = [float(U0 * np.cos(aoa)), float(U0 * np.sin(aoa)), 0]
                # we need to update the U value only
                DASolver.setOption("primalBC", {"U0": {"value": U}})
                DASolver.updateDAOption()

            # pass this aoa function to the cruise group
            self.cruise.coupling.solver.add_dv_func("aoa", aoa)
            self.cruise.aero_post.add_dv_func("aoa", aoa)

            # add the design variables to the dvs component's output
            self.dvs.add_output("aoa", val=np.array([aoa0]))
            # manually connect the dvs output to the cruise
            self.connect("aoa", "cruise.aoa")

            # define the design variables to the top level
            self.add_design_var("aoa", lower=0.0, upper=10.0, scaler=1.0)

            # add objective and constraints to the top level
            self.add_objective("cruise.aero_post.CD", scaler=1.0)
            # self.add_constraint("cruise.aero_post.CL", equals=CL_target, scaler=1.0)


    # OpenMDAO setup
    prob = om.Problem()
    prob.model = Top()
    prob.setup(mode="rev")
    
    # initialize the calculation function
    optFuncs = OptFuncs(daOptions, prob)
    
    return prob

Re = 6e6
aoa_list = [0, 2, 4, 6, 8, 10]

for aoa in aoa_list:
    prob = run_DAFoam(Re, aoa)

    # run the calculation
    prob.run_model()

    # get the results
    CD_value = prob['cruise.aero_post.CD']
    CL_value = prob['cruise.aero_post.CL']
    CM_value = prob['cruise.aero_post.CM']

    # print the results
    if MPI.COMM_WORLD.rank == 0:
        # save the results to a file
        with open(args.output, 'a') as f:
            f.write(f"{Re}, {aoa}, {CL_value}, {CD_value}, {CM_value}\n")