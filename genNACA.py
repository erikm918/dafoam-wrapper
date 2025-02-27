import numpy as np

def naca0012(x):
    """Calculate the y-coordinates of a NACA 0012 airfoil for a given array of x-coordinates."""
    return 0.6 * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)

def generate_xyz_file(filename, x_num, z_num, cord_len, y_num=2):
    """Generate a .xyz file for a NACA 0012 airfoil."""
    x = np.linspace(0, cord_len, x_num)  # x-coordinates
    y_upper = naca0012(x)  # upper surface y-coordinates
    y_lower = -naca0012(x)  # lower surface y-coordinates

    x_val = []
    y_val = []
    z_val = []
    # Prepare the data for the .xyz file
    for i in range(z_num):
        for j in range(y_num):
            for k in range(x_num):
                x_val.append(x[k])
                if j % 2 == 0:
                    y_val.append(y_lower[k])
                else:
                    y_val.append(y_upper[k])
                z_val.append(0.1*i)

    with open(filename, 'w') as f:
        f.write("1\n")
        f.write(f"{x_num} {y_num} {z_num}\n")

        for val in x_val:
            f.write(f"{val:.6f} ")
        f.write("\n")

        for val in y_val:
            f.write(f"{val:.6f} ")
        f.write("\n")

        for val in z_val:
            f.write(f"{val:.6f} ")
        f.write("\n")

generate_xyz_file("naca0012.xyz", 15, 2, 1)