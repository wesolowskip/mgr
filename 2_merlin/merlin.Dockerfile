FROM cuml-prod

SHELL ["/bin/bash", "-i", "-c"]
RUN conda activate rapids
RUN conda update -n base -c conda-forge conda

RUN pip install --upgrade pip

RUN pip install nvidia-cudnn-cu11==8.6.0.163

RUN mkdir -p $CONDA_PREFIX/etc/conda/activate.d
RUN echo 'CUDNN_PATH=$(dirname $(python -c "import nvidia.cudnn;print(nvidia.cudnn.__file__)"))' >> $CONDA_PREFIX/etc/conda/activate.d/env_vars.sh
RUN echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CONDA_PREFIX/lib/:$CUDNN_PATH/lib' >> $CONDA_PREFIX/etc/conda/activate.d/env_vars.sh

RUN pip install tensorflow==2.12.*

RUN conda install -y -c conda-forge -c nvidia merlin-core merlin-models merlin-systems nvtabular transformers4rec
RUN pip install graphviz

