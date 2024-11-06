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
    BasePacket,
    CciRequestPacket,
    CciMessagePacket,
    GetLdInfoResponsePayload,
    CciResponsePacket,
    GetLdInfoResponsePacket,
    GetLdInfoRequestPacket,
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
        downstream_fifo: Optional[FifoPair] = None,  # LD로 가는 FM API를 구한할 때 추가해야함.
        label: Optional[str] = None,
    ):
        super().__init__(label)
        # self._memory_device_component: Optional[CxlMemoryDeviceComponent] = None
        self._downstream_fifo = downstream_fifo
        self._upstream_fifo = upstream_fifo

        self._ld_count = ld_count
        self._dev_type = dev_type
        self._allocated_ld = []  # Get/Set LD allocations에 사용될 예정

    # LD용 Mctp Manager를 따로 만들까 생각중임.
    # def set_memory_device_component(self, memory_device_component: CxlMemoryDeviceComponent):
    #     self._memory_device_component = memory_device_component
    async def _process_get_ld_info_packet(self, get_ld_info_request_packet: CciRequestPacket):
        if get_ld_info_request_packet.get_command_opcode() != 0x5400:
            raise Exception("Invalid command opcode")
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
        pass

    async def _process_set_ld_allocations_packet(self, set_ld_allocations_packet: CciRequestPacket):
        pass

    # FMLD receive response packet from the LD, and send it to the host
    async def _process_fmld_cci_response_packet(self, cci_message: CciMessagePacket):
        pass

    async def _process_fm_to_target(self):
        # if self._downstream_fifo is None:
        #     logger.info(self._create_message("Skipped processing fm to ld packets"))
        #     return
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

    async def _process_target_to_fm(self):
        # LD가 FMLD에게 Get LD allocations나 Set LD allocations Response를 보냈을 때
        # 추후 구현 필요
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
        logger.info("I'm here")
        tasks = [
            create_task(self._process_fm_to_target()),
            create_task(self._process_target_to_fm()),
        ]
        logger.info("I'm here")
        await self._change_status_to_running()
        logger.info("I'm here")
        await gather(*tasks)
        logger.info("I'm here")

    async def _stop(self):
        logger.info("I'm here")
        if self._downstream_fifo is not None:
            logger.info("I'm here")
            await self._downstream_fifo.target_to_host.put(None)
        logger.info("I'm here")
        await self._upstream_fifo.host_to_target.put(None)
        logger.info("I'm here")
        logger.info(self._create_message("Stopped"))
        logger.info("I'm here")
