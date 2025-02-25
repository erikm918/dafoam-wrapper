from pyhyp import pyHyp
import numpy as np
import argparse

'''
Converts given FFD file to a surface mesh and volume mesh to be used in DAFoam optimization.

Reads FFD file and outputs a list of points as numpy arrays x, y, and z. These points are then
iterated through and converted into a surface mesh and stored in a .xyz file (default is 
surfaceMesh.xyz). This surface mesh is then converted into a volume mesh using pyHyp and 
stored in a different .xyz file (default is volumeMesh.xyz).
'''

# ======================================================================================================
# Runtime Arguments
# ======================================================================================================
parser = argparse.ArgumentParser()
parser.add_argument("--ffd_file", help="Path to FFD .xyz file", type=str, required=True)
parser.add_argument("--output_surface", help="Specifies surface mesh file", type=str,
                    default="surfaceMesh.xyz")
parser.add_argument("--output_volue", help="Specifies volume mesh file", type=str,
                    default="volumeMesh.xyz")
parser.add_argument("--z_span", help="Width in z-direction", type=float, default=0.1)
parser.add_argument("--n_span", help="Number of points in z-drection", type=int, default=2)
parser.add_argument("--n_extrude", help="Number of points to extrude for 3D volume mesh in y-direction", 
                    type=int, default=33)
parser.add_argument("--y_wall", help="First layer mesh length", type=float, default=4e-3)
parser.add_argument("--march_dist", help="March distance for extruding", type=float, default=20)

'''
Read FFD file and separate into x, y, z values to be converted into a mesh. Both volume and surface
meshes are required to run DAFoam.
'''
def read_ffd(ffd_file):
    x = []
    y = []
    z = []
    
    with open(ffd_file, "r") as f:
        rows = f.readlines()
        
        for row in rows:
            column = row.split()
            x.append(float(column[0]))
            y.append(float(column[1]))
            z.append(float(column[2]))
        
        return np.array(x), np.array(y), np.array(z)

def generate_surface_mesh(x, y, z, z_span, n_span, output_surface):
    with open(output_surface, "w") as f:
        # Write mesh file "headers"
        f.write("1\n")
        f.write("%d %d %d\n" % (len(x), z_span, n_span))
        
        # Iterate through x, y, z
        for j in range(3):
            # Iterate through number of z-values given
            for z_val in np.linspace(0., z_val, n_span):
                # For each z-value, write down the x, y, z coordinates of the mesh
                for i in range(len(x)):
                    # x-values of mesh
                    if j == 0:
                        f.write("%20.16f\n" % x[i])
                    # y-values of mesh
                    elif j == 1:
                        f.write("%20.16f\n" % y[i])
                    # z-values of mesh
                    else:
                        f.write("%20.16f\n" % z[i])
                        
    print("Surface mesh file written to {output_surface}.")

def generate_volume_mesh(output_surface, output_volume, n_extrude, y_wall, march_dist):
    # Options for pyHyp
    options = {
        # ====================================
        # Input params
        # ====================================
        "inputFile": output_surface,
        "unattachedEdgesAreSymmetry": False,
        "outerFaceBC": "farfield",
        "autoConnect": True,
        "BC": {1: {"jLow": "zSymm", "jHigh": "zSymm"}},
        "families": "wall",
        # ====================================
        # Grid params
        # ====================================
        "N": n_extrude,
        "s0": y_wall,
        "marchDist": march_dist,
        # ====================================
        # Pseudo grid params
        # ====================================
        "ps0": -1.0,
        "pGridRatio": -1.0,
        "cMax": 1.0,
        # ====================================
        # Smoothing params
        # ====================================
        "epsE": 2.0,
        "epsI": 4.0,
        "theta": 2.0,
        "volCoef": 0.20,
        "volBlend": 0.0005,
        "volSmoothIter": 20,
    }

    # Initialize and run pyHyp to generate volume mesh
    hyp = pyHyp(options=options)
    hyp.run()
    # Write volume mesh to file
    hyp.writePlot3D(output_volume)
    
    print(f"Volume mesh written to {output_volume}")