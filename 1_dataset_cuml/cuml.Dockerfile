FROM rapidsai/rapidsai-dev:23.02-cuda11.8-devel-ubuntu22.04-py3.10 as base
RUN mv /opt/conda/envs/rapids/include/boost/mp11 /opt/conda/envs/rapids/include/boost/mp11_do_not_use

# The following environment variable require change!
ENV METAJSONPARSER_PATH="/home2/faculty/pwesolowski/praca-mgr/parser-repo"

RUN <<EOF cat > /root/tmp_bashrc && mv /root/tmp_bashrc /root/.bashrc
export PATH='/opt/conda/bin:/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
export NVARCH="$NVARCH"
export NVIDIA_REQUIRE_CUDA="$NVIDIA_REQUIRE_CUDA"
export NV_CUDA_CUDART_VERSION="$NV_CUDA_CUDART_VERSION"
export NV_CUDA_COMPAT_PACKAGE="$NV_CUDA_COMPAT_PACKAGE"
export CUDA_VERSION="$CUDA_VERSION"
export LD_LIBRARY_PATH="${METAJSONPARSER_PATH}/build:/opt/conda/envs/rapids/bin:${LD_LIBRARY_PATH}" # useful
export NVIDIA_VISIBLE_DEVICES="$NVIDIA_VISIBLE_DEVICES"
export NVIDIA_DRIVER_CAPABILITIES="$NVIDIA_DRIVER_CAPABILITIES"
export NV_CUDA_LIB_VERSION="$NV_CUDA_LIB_VERSION"
export NV_NVTX_VERSION="$NV_NVTX_VERSION"
export NV_LIBNPP_VERSION="$NV_LIBNPP_VERSION"
export NV_LIBNPP_PACKAGE="$NV_LIBNPP_PACKAGE"
export NV_LIBCUSPARSE_VERSION="$NV_LIBCUSPARSE_VERSION"
export NV_LIBCUBLAS_PACKAGE_NAME="$NV_LIBCUBLAS_PACKAGE_NAME"
export NV_LIBCUBLAS_VERSION="$NV_LIBCUBLAS_VERSION"
export NV_LIBCUBLAS_PACKAGE="$NV_LIBCUBLAS_PACKAGE"
export NV_LIBNCCL_PACKAGE_NAME="$NV_LIBNCCL_PACKAGE_NAME"
export NV_LIBNCCL_PACKAGE_VERSION="$NV_LIBNCCL_PACKAGE_VERSION"
export NCCL_VERSION="$NCCL_VERSION"
export NV_LIBNCCL_PACKAGE="$NV_LIBNCCL_PACKAGE"
export NV_CUDA_CUDART_DEV_VERSION="$NV_CUDA_CUDART_DEV_VERSION"
export NV_NVML_DEV_VERSION="$NV_NVML_DEV_VERSION"
export NV_LIBCUSPARSE_DEV_VERSION="$NV_LIBCUSPARSE_DEV_VERSION"
export NV_LIBNPP_DEV_VERSION="$NV_LIBNPP_DEV_VERSION"
export NV_LIBNPP_DEV_PACKAGE="$NV_LIBNPP_DEV_PACKAGE"
export NV_LIBCUBLAS_DEV_VERSION="$NV_LIBCUBLAS_DEV_VERSION"
export NV_LIBCUBLAS_DEV_PACKAGE_NAME="$NV_LIBCUBLAS_DEV_PACKAGE_NAME"
export NV_LIBCUBLAS_DEV_PACKAGE="$NV_LIBCUBLAS_DEV_PACKAGE"
export NV_LIBNCCL_DEV_PACKAGE_NAME="$NV_LIBNCCL_DEV_PACKAGE_NAME"
export NV_LIBNCCL_DEV_PACKAGE_VERSION="$NV_LIBNCCL_DEV_PACKAGE_VERSION"
export NV_LIBNCCL_DEV_PACKAGE="$NV_LIBNCCL_DEV_PACKAGE"
export LIBRARY_PATH="${METAJSONPARSER_PATH}/build:$LIBRARY_PATH" # useful
export CONDA_DIR="/opt/conda"
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
export LANGUAGE="en_US:en"
export DEBIAN_FRONTEND="$DEBIAN_FRONTEND"
export CC="/usr/bin/gcc"
export CXX="/usr/bin/g++"
export CUDAHOSTCXX="/usr/bin/g++"
export CUDA_HOME="$CUDA_HOME"
export CONDARC="$CONDARC"
export RAPIDS_DIR="$RAPIDS_DIR"
export DASK_LABEXTENSION__FACTORY__MODULE="$DASK_LABEXTENSION__FACTORY__MODULE"
export DASK_LABEXTENSION__FACTORY__CLASS="$DASK_LABEXTENSION__FACTORY__CLASS"
export NCCL_ROOT="$NCCL_ROOT"
export PARALLEL_LEVEL="$PARALLEL_LEVEL"
export CUDAToolkit_ROOT="$CUDAToolkit_ROOT"
export CUDACXX="$CUDACXX"
export CPLUS_INCLUDE_PATH="${METAJSONPARSER_PATH}/meta_cudf:${CPLUS_INCLUDE_PATH}" # useful
`cat /root/.bashrc`
EOF

# https://ubuntuforums.org/archive/index.php/t-914151.html
# https://stackoverflow.com/questions/69259311/why-do-i-got-conda-command-not-found-when-building-a-docker-while-in-base-im
SHELL ["/bin/bash", "-i", "-c"]


RUN conda activate rapids
RUN conda develop ${METAJSONPARSER_PATH}/python_binding # alternative: setting PYTHONPATH every time
RUN pip install unidecode lxml joblib

RUN sed -i '2i DISABLE_JUPYTER=true' /opt/docker/bin/entrypoint_source

# The following commands are commentected out due to convenience. Singularity containers are readonly by default
# hence I store the repos under $HOME directory in the cluster which are then mounted to the container.
#RUN git clone https://github.com/wesolowskip/mgr.git /mgr
#
#RUN git clone https://github.com/wesolowskip/meta-json-parser.git -b rmm ${METAJSONPARSER_PATH}
#RUN git clone https://github.com/CLIUtils/CLI11.git -b v2.0.0 ${METAJSONPARSER_PATH}/third_parties/CLI11
#RUN git clone https://github.com/boostorg/mp11.git -b boost-1.82.0 ${METAJSONPARSER_PATH}/third_parties/mp11
#WORKDIR ${METAJSONPARSER_PATH}
#RUN git submodule update --init --recursive; exit 0 # git clone did not work (probably due to invalid version)
#
#RUN mkdir -p build

RUN <<EOF cat > /build.sh
#!/bin/bash
cd ${METAJSONPARSER_PATH}/build
cmake -DCMAKE_BUILD_TYPE=Release -DUSE_LIBCUDF=1 -DLOCAL_LIB=1 -DMEASURE_THROUGHPUT=1 ..
make -j meta-cudf-parser-1
cd ${METAJSONPARSER_PATH}/python_binding
make
EOF

RUN chmod a+x /build.sh

WORKDIR /
