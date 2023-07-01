import copy

from dask_cuda import LocalCUDACluster
from dask_cuda.utils import (
    CPUAffinity,
    PreImport,
    RMMSetup,
    cuda_visible_devices,
    get_cpu_count,
)


class CPUAgnosticCUDACluster(LocalCUDACluster):

    def new_worker_spec(self):
        try:
            name = min(set(self.cuda_visible_devices) - set(self.worker_spec))
        except Exception:
            raise ValueError(
                "Can not scale beyond visible devices", self.cuda_visible_devices
            )

        spec = copy.deepcopy(self.new_spec)
        worker_count = self.cuda_visible_devices.index(name)
        visible_devices = cuda_visible_devices(worker_count, self.cuda_visible_devices)
        spec["options"].update(
            {
                "env": {
                    "CUDA_VISIBLE_DEVICES": visible_devices,
                },
                "plugins": {
                    CPUAffinity(
                        list(range(get_cpu_count()))
                    ),
                    RMMSetup(
                        initial_pool_size=self.rmm_pool_size,
                        maximum_pool_size=self.rmm_maximum_pool_size,
                        managed_memory=self.rmm_managed_memory,
                        async_alloc=self.rmm_async,
                        release_threshold=self.rmm_release_threshold,
                        log_directory=self.rmm_log_directory,
                        track_allocations=self.rmm_track_allocations,
                    ),
                    PreImport(self.pre_import),
                },
            }
        )

        return {name: spec}
