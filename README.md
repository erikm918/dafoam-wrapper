# Running DAFoam

### From Docker Image
Open directory storing DAFoam script and mount docker:
```
$ cd dafaom-wrapper/
$ docker run -it --rm -u dafoamuser --mount "type=bind,src=$(pwd),target=/home/dafoamuser/mount" \
    -w /home/dafoamuser/mount dafoam/opt-packages:latest bash
```
This will download the DAFoam Docker image (if not already on the system) and open a terminal interface with on the Docker image. Will see something like:
`dafoamuser@796a7c03fbfa:~/mount$ `. From here, run the DAFoam wrapper in the main file using MPI:
`mpirun -np {core-count} python main.py 2>&1`. Select cores depending on the amount allowed by your system or by desired number.