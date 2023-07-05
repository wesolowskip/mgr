FROM cuml-prod

SHELL ["/bin/bash", "-i", "-c"]
RUN conda activate rapids
RUN conda update -n base -c conda-forge conda

RUN pip3 install torch --index-url https://download.pytorch.org/whl/cu118
RUN pip3 install lightning
RUN conda install -y -c conda-forge -c nvidia merlin-core merlin-models merlin-systems nvtabular transformers4rec
RUN pip install graphviz

