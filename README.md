# City-Road-Network
A library for retreiving relevant management data of cities road networks.

Installation:

0. Prerequisites: [Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) for Windows OS, Python 3.11.
1. Clone repository.
2. Create virtual environment, e.g. `python3 -m venv venv` or `conda create --name myenv -c conda-forge python=3.11`.
3. Activate virtual environment.
4. Install dependencies `pip install -r requirements.txt` or `pip install .`.

For example usage refer to `examples` directory. Expected sequence is to download data, run gravity to model to obtain OD matrix and run simulation (naive, smarter or sumo). Additionally you can export the data to PostgreSQL w/ PostGIS or Neo4j.

Note that in order to use export to PostgreSQL or Neo4j you need to create `.env` file using `.env.example` as a template and fill in values accordingly.
