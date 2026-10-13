# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Test-only StudioNet probe. Never use this contract to hold user escrow."""
from genlayer import *


class TransferFailureProbe(gl.Contract):
    attempted: u256

    def __init__(self):
        self.attempted = u256(0)

    @gl.public.write.payable
    def trigger(self) -> None:
        if gl.message.value == u256(0):
            raise gl.vm.UserError("Probe needs a positive simulated GEN amount")
        self.attempted += gl.message.value
        gl.get_contract_at(gl.message.contract_address).emit(value=gl.message.value, on="finalized").reject()

    @gl.public.write.payable
    def reject(self) -> None:
        raise gl.vm.UserError("Deliberate receiver rejection for failure probe")

    @gl.public.view
    def state(self) -> dict:
        return {"attempted": str(self.attempted), "balance": str(self.balance)}
