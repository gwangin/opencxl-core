"""
 Copyright (c) 2024, Eeum, Inc.

 This software is licensed under the terms of the Revised BSD License.
 See LICENSE for details.
"""

from dataclasses import dataclass, field
from struct import pack, unpack
from typing import ClassVar
from opencxl.cxl.component.cci_executor import (
    CciBackgroundCommand,
    CciRequest,
    CciResponse,
    ProgressCallback,
)

from opencxl.cxl.cci.common import CCI_FM_API_COMMAND_OPCODE, CCI_RETURN_CODE
from opencxl.util.logger import logger


@dataclass
class GetLdAllocationsRequestPayload:
    start_ld_id: int = field(default=0) # 1byte
    ld_allocation_list_limit: int = field(default=0) # 1byte

    @classmethod
    def parse(cls, data: bytes):
        if len(data) < 2:
            raise ValueError("Data provided is too short to parse.")
        
        start_ld_id = data[0]
        ld_allocation_list_limit = data[1]
        return cls(start_ld_id, ld_allocation_list_limit)
    
    def dump(self):
        data = bytearray(2)
        data[0] = self.start_ld_id
        data[1] = self.ld_allocation_list_limit
        return bytes(data)
    
    def get_pretty_print(self):
        return (
            f"- Start LD ID: {self.start_ld_id}\n"
            f"- LD Allocation List Limit: {self.ld_allocation_list_limit}\n"
        )
    


@dataclass
class GetLdAllocationsResponsePayload:
    number_of_lds: int = field(default=0) # 1byte
    memory_granularity: int = field(default=0) # 1byte
    start_ld_id: int = field(default=0) # 1byte
    ld_allocation_list_length: int = field(default=0) # 1byte
    ld_allocation_list: bytes = field(default=b"")

    @classmethod
    def parse(cls, data: bytes):
        if len(data) < 4:
            raise ValueError("Data provided is too short to parse.")
        
        number_of_lds = data[0]
        memory_granularity = data[1]
        start_ld_id = data[2]
        ld_allocation_list_length = data[3]
        ld_allocation_list = data[4:]
        return cls(number_of_lds, memory_granularity, start_ld_id, ld_allocation_list_length, ld_allocation_list)
    

    def dump(self):
        data = bytearray(4)
        data[0] = self.number_of_lds
        data[1] = self.memory_granularity
        data[2] = self.start_ld_id
        data[3] = self.ld_allocation_list_length
        data += self.ld_allocation_list
        return bytes(data)
    
    def get_pretty_print(self):
        return (
            f"- Number of LDs: {self.number_of_lds}\n"
            f"- Memory Granularity: {self.memory_granularity}\n"
            f"- Start LD ID: {self.start_ld_id}\n"
            f"- LD Allocation List Length: {self.ld_allocation_list_length}\n"
            f"- LD Allocation List: {self.ld_allocation_list}\n"
        )
    

class GetLdAllocationsCommand(CciBackgroundCommand):
    OPCODE = CCI_FM_API_COMMAND_OPCODE.GET_LD_ALLOCATIONS




    def __init__(self):
        super().__init__(self.OPCODE)


    async def _execute(self, request: CciRequest) -> CciResponse:
        pass


    @classmethod
    def create_cci_request(cls, request: GetLdAllocationsRequestPayload) -> CciRequest:
        cci_request = CciRequest()
        cci_request.opcode = cls.OPCODE
        cci_request.payload = request.dump()
        return cci_request
    
    @staticmethod
    def create_cci_response(response: GetLdAllocationsResponsePayload) -> CciResponse:
        cci_response = CciResponse()
        cci_response.payload = response.dump()
        return cci_response


    @classmethod
    def parse_request_payload(cls, payload: bytes) -> GetLdAllocationsRequestPayload:
        return GetLdAllocationsRequestPayload.parse(payload)
    
    @classmethod
    def parse_response_payload(cls, payload: bytes) -> GetLdAllocationsResponsePayload:
        return GetLdAllocationsResponsePayload.parse(payload)