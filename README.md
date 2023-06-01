# City-Road-Network
A library for retreiving relevant management data of cities road networks.

Installation:

0. Prerequisites: [Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) for Windows OS, Python 3.11.
1. Clone repository.
2. Create virtual environment, e.g. `python3 -m venv venv` or `conda create --name myenv -c conda-forge python=3.11`.
3. Activate virtual environment.
4. Install dependencies `pip install -r requirements.txt`.
5. Install GDAL.

GDAL installation for Windows:
1. `conda install -c conda-forge gdal`


GDAL installation for Linux:
1. `sudo apt install gdal-bin`
2. `sudo apt install libgdal-dev`
3. Run `gdal-config --version`. Use this version to install python package in the next step.
4. `pip install gdal==3.4.1`. Make sure to install numpy before attemting to install GDAL.

For example usage refer to `examples` directory.