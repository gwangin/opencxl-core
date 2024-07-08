"""
 Copyright (c) 2024, Eeum, Inc.

 This software is licensed under the terms of the Revised BSD License.
 See LICENSE for details.
"""

from asyncio import gather, create_task

from opencxl.util.component import RunnableComponent
from opencxl.cxl.device.cxl_type3_device import CxlType3Device, CXL_T3_DEV_TYPE
from opencxl.cxl.component.switch_connection_client import SwitchConnectionClient
from opencxl.cxl.component.cxl_component import CXL_COMPONENT_TYPE
from typing import List


class MultiLogicalDevice(RunnableComponent):
    def __init__(
        self,
        port_indexes: List[int],
        memory_sizes: List[int],
        memory_files: List[str],
        host: str = "0.0.0.0",
        port: int = 8000,
        num_ld: int = 2
    ):
        label = "Port " + " ".join([f"{port_index}" for port_index in port_indexes])
        super().__init__(label)

        self._sw_conn_clients = []
        self._cxl_type3_devices = []

        for ld in range(num_ld):
            sw_conn_client = SwitchConnectionClient(
                port_indexes[ld], CXL_COMPONENT_TYPE.D2, host=host, port=port
            )
            self._sw_conn_clients.append(sw_conn_client)
            cxl_type3_device = CxlType3Device(
                transport_connection=self._sw_conn_clients[ld].get_cxl_connection(),
                memory_size=memory_sizes[ld],
                memory_file=memory_files[ld],
                dev_type=CXL_T3_DEV_TYPE.MLD,
                label=label,
            )
            self._cxl_type3_devices.append(cxl_type3_device)

    async def _run(self):
        sw_conn_client_tasks = [create_task(client.run()) for client in self._sw_conn_clients]
        cxl_type3_device_tasks = [create_task(device.run()) for device in self._cxl_type3_devices]

        tasks = sw_conn_client_tasks + cxl_type3_device_tasks

        await self._change_status_to_running()
        await gather(*tasks)

    async def _stop(self):
        sw_conn_client_tasks = [create_task(client.stop()) for client in self._sw_conn_clients]
        cxl_type3_device_tasks = [create_task(device.stop()) for device in self._cxl_type3_devices]

        tasks = sw_conn_client_tasks + cxl_type3_device_tasks

        await gather(*tasks)
