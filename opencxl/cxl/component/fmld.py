"""
 Copyright (c) 2024, Eeum, Inc.

 This software is licensed under the terms of the Revised BSD License.
 See LICENSE for details.
"""

from asyncio import create_task, gather
from typing import Optional, cast

from opencxl.util.component import RunnableComponent
from opencxl.util.logger import logger
from opencxl.pci.component.fifo_pair import FifoPair
from opencxl.cxl.transport.transaction import (
    CciRequestPacket,
    CciMessagePacket,
    GetLdInfoResponsePacket,
    GetLdAllocationsResponsePacket,
    SetLdAllocationsResponsePacket,
)
from opencxl.cxl.component.cxl_memory_device_component import CxlMemoryDeviceComponent

# import MctpPacketProcessor
from opencxl.pci.component.mctp_packet_processor import MctpPacketProcessor
from opencxl.cxl.device.cxl_type3_device import CXL_T3_DEV_TYPE


# Replaces MctpPacketProcessor
class FMLD(RunnableComponent):
    def __init__(
        self,
        upstream_fifo: FifoPair,
        ld_count: int,
        dev_type: CXL_T3_DEV_TYPE,
        allocated_ld: Optional[int] = [],
        downstream_fifo: Optional[FifoPair] = None,  # LD로 가는 FM API를 구한할 때 추가해야함.
        label: Optional[str] = None,
    ):
        super().__init__(label)
        self._downstream_fifo = downstream_fifo
        self._upstream_fifo = upstream_fifo
        self._ld_count = ld_count
        self._dev_type = dev_type
        self._allocated_ld = 12
        
    async def _process_get_ld_info_packet(self, get_ld_info_request_packet: CciRequestPacket):
        if get_ld_info_request_packet.get_command_opcode() != 0x5400:
            raise Exception("Invalid command opcode")
        logger.info(f"Get LD Info Request: {get_ld_info_request_packet}")
        memory_size = self._ld_count * 1024 * 1024 * 256
        logger.info(f"Memory Size: {memory_size}")
        logger.info(f"LD Count: {self._ld_count}")
        get_ld_info_response_packet = GetLdInfoResponsePacket.create(
            memory_size=memory_size, ld_count=self._ld_count
        )
        logger.info(f"Get LD Info Response: {get_ld_info_response_packet}")
        await self._upstream_fifo.target_to_host.put(get_ld_info_response_packet)
        logger.info(f"Get LD Info Response sent done")

    async def _process_get_ld_allocations_packet(self, get_ld_allocations_packet: CciRequestPacket):
        if get_ld_allocations_packet.get_command_opcode() != 0x5401:
            raise Exception("Invalid command opcode")
        logger.info(f"Get LD Allocations: {get_ld_allocations_packet}")
        get_ld_allocations_response_packet = GetLdAllocationsResponsePacket.create(
            number_of_lds=4, memory_granularity=0, start_ld_id=0, ld_allocation_list_length=4, ld_allocation_list=self._allocated_ld
            )
                                                                                   
        await self._upstream_fifo.target_to_host.put(get_ld_allocations_response_packet)
        logger.info(f"Get LD Allocations Response sent done")

    async def _process_set_ld_allocations_packet(self, set_ld_allocations_packet: CciRequestPacket):
        if set_ld_allocations_packet.get_command_opcode() != 0x5402:
            raise Exception("Invalid command opcode")
        logger.info(f"Set LD Allocations: {set_ld_allocations_packet}")
        set_ld_allocations_response_packet = SetLdAllocationsResponsePacket.create(
            number_of_lds=4, start_ld_id=0, ld_allocation_list_length=4, ld_allocation_list=self._allocated_ld
            )
        await self._upstream_fifo.target_to_host.put(set_ld_allocations_response_packet)
        logger.info(f"Set LD Allocations Response sent done")


    async def _process_fm_to_target(self):
        logger.info(self._create_message("Started processing fm to ld packets"))
        while True:
            packet = await self._upstream_fifo.host_to_target.get()
            print("fmld received packet", packet)
            if packet is None:
                logger.info(self._create_message("Stopped fm to ld packets"))
                break
            logger.info(self._create_message("Received fm to ld Packet"))

            packet = cast(CciRequestPacket, packet)
            if packet.get_command_opcode() == 0x5400:  # Get Ld info
                await self._process_get_ld_info_packet(packet)
            elif packet.get_command_opcode() == 0x5401:  # Get Ld Allocations
                await self._process_get_ld_allocations_packet(packet)
            elif packet.get_command_opcode() == 0x5402:  # Set Ld Allocations
                await self._process_set_ld_allocations_packet(packet)

    #TODO : This function should be implemented for LD to FM API
    async def _process_target_to_fm(self):
        if self._downstream_fifo is None:
            logger.info(self._create_message("Skipped processing ld to fm packets"))
            return
        logger.info(self._create_message("Started processing ld to fm packets"))
        while True:
            packet = await self._downstream_fifo.target_to_host.get()
            if packet is None:
                logger.info(self._create_message("Stopped ld to fm packets"))
                break
            logger.info(self._create_message("Received ld to fm Packet"))
            await self._upstream_fifo.target_to_host.put(packet)

    async def _run(self):
        tasks = [
            create_task(self._process_fm_to_target()),
            create_task(self._process_target_to_fm()),
        ]
        await self._change_status_to_running()
        await gather(*tasks)

    async def _stop(self):
        if self._downstream_fifo is not None:
            await self._downstream_fifo.target_to_host.put(None)
        await self._upstream_fifo.host_to_target.put(None)
