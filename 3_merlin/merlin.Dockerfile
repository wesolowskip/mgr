FROM rapids-prod

RUN apt remove -y libopenmpi3 openmpi-common libopenmpi-dev openmpi-bin

ENV OMPI_DIR=/opt/ompi

RUN <<EOF cat > /root/tmp_bashrc && mv /root/tmp_bashrc /root/.bashrc
`cat /root/.bashrc`
export PATH=$OMPI_DIR/bin:$PATH
export LD_LIBRARY_PATH=$OMPI_DIR/lib:$LD_LIBRARY_PATH
EOF

SHELL ["/bin/bash", "-i", "-c"]
RUN conda activate rapids
RUN conda update -n base -c conda-forge conda
RUN pip install --upgrade pip

COPY pmix /usr/lib/x86_64-linux-gnu/pmix

# RUN apt update && apt install libfabric-dev libpsm2-dev

RUN mkdir -p /tmp/ompi && mkdir -p /opt && OMPI_VERSION=4.0.3 && OMPI_URL="https://download.open-mpi.org/release/open-mpi/v4.0/openmpi-$OMPI_VERSION.tar.bz2" && cd /tmp/ompi && wget -O openmpi-$OMPI_VERSION.tar.bz2 $OMPI_URL && tar -xjf openmpi-$OMPI_VERSION.tar.bz2 && cd /tmp/ompi/openmpi-$OMPI_VERSION && ./configure --disable-mpi-fortran --build=x86_64-linux-gnu --prefix=$OMPI_DIR --sysconfdir=/etc --with-package-string='Debian OpenMPI' --enable-opal-btl-usnic-unit-tests --with-libevent=external --with-pmix=/usr/lib/x86_64-linux-gnu/pmix --enable-mpi-cxx --with-libltdl --with-devel-headers --with-slurm --with-sge --without-tm --sysconfdir=/etc/openmpi && make -j8 install

RUN pip install nvidia-cudnn-cu11==8.6.0.163

RUN mkdir -p $CONDA_PREFIX/etc/conda/activate.d
RUN echo 'CUDNN_PATH=$(dirname $(python -c "import nvidia.cudnn;print(nvidia.cudnn.__file__)"))' >> $CONDA_PREFIX/etc/conda/activate.d/env_vars.sh
RUN echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CONDA_PREFIX/lib/:$CUDNN_PATH/lib' >> $CONDA_PREFIX/etc/conda/activate.d/env_vars.sh

RUN pip install tensorflow==2.12.*

RUN conda install -y -c conda-forge -c nvidia merlin-core merlin-models merlin-systems nvtabular transformers4rec
RUN pip install graphviz

RUN HOROVOD_GPU_OPERATIONS=NCCL pip install horovod


# https://stackoverflow.com/questions/49130563/could-not-determine-size-of-character-while-installing-openmpi
#./configure --disable-mpi-fortran --build=x86_64-linux-gnu --prefix=$OMPI_DIR --sysconfdir=/etc --with-package-string='Debian OpenMPI' --with-verbs --with-libfabric --with-psm2 --enable-opal-btl-usnic-unit-tests --with-libevent=external --with-pmix=/usr/lib/x86_64-linux-gnu/pmix --with-libltdl --with-slurm --with-sge --without-tm --sysconfdir=/etc/openmpi

