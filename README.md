# DAFoam Wrapper

## Installing DAFoam

### From Apptainer
The Docker container can also be pulled and run using Appertainer. If choosing to run programs using a container on the ROAR Collab, Apptainer is required. In order to install and run the container, use the following command:
```
apptainer build dafoam.sif docker://dafoam/opt-packages:latest
apptainer shell dafoam.sif
```

### From Docker Image
#### Installing Docker

Follow the Docker installation instructions found [here](https://www.docker.com/get-started/).

#### Running Docker
- MacOS
    1. Open working directory and run Docker image. This command will install the Docker image (if not already on the system) and mount the image.
    ```
    $ cd dafaom-wrapper/
    $ docker run -it --rm -u dafoamuser --mount "type=bind,src=$(pwd),target=/home/dafoamuser/mount" -w /home/dafoamuser/mount dafoam/opt-packages:latest bash
    ```
    2. When complete, terminal user should read something like:`dafoamuser@796a7c03fbfa:~/mount$ `. 

- Windows 10
    1. Open working directory and run Docker image. This command will install the Docker image (if not already on the system) and mount the image.
    ```
    docker run -it --rm -u dafoamuser --mount "type=bind,src=%cd%,target=/home/dafoamuser/mount" -w /home/dafoamuser/mount dafoam/opt-packages:v4.0.0 bash
    ```
    2. When complete, terminal user should read something like:`dafoamuser@796a7c03fbfa:~/mount$ `. 

- Windows 11
    1. Open working directory and run Docker image. This command will install the Docker image (if not already on the system) and mount the image.
    ```
    docker run -it --rm -u dafoamuser --mount "type=bind,src=.,target=/home/dafoamuser/mount" -w /home/dafoamuser/mount dafoam/opt-packages:v4.0.0 bash
    ```
    2. When complete, terminal user should read something like:`dafoamuser@796a7c03fbfa:~/mount$ `. 

- Linux 
    1. Open working directory and run Docker image. This command will install the Docker image (if not already on the system) and mount the image.
    ```
    docker run -it --rm -u dafoamuser --mount "type=bind,src=$(pwd),target=/home/dafoamuser/mount" -w /home/dafoamuser/mount dafoam/opt-packages:v4.0.0 bash
    ```
    2. When complete, terminal user should read something like:`dafoamuser@796a7c03fbfa:~/mount$ `. 

#### From Source
Follow the download instructions from the [DAFoam install page](https://dafoam.github.io/mydoc_installation_source.html). **Note:** This install process only works on Ubuntu and HPC systems. 

### Running DAFoam Wrapper
