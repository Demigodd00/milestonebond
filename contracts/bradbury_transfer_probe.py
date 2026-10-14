# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Test-only Bradbury probe for finalized EVM receiver rejection."""
from genlayer import *


@gl.evm.contract_interface
class ProbeRecipient:
    class View:
        pass

    class Write:
        pass


class BradburyTransferProbe(gl.Contract):
    attempted: u256
    recipient: str

    def __init__(self):
        self.attempted = u256(0)
        self.recipient = ""

    @gl.public.write.payable
    def trigger(self, recipient: str) -> None:
        if gl.message.value == u256(0) or self.attempted != u256(0):
            raise gl.vm.UserError("Probe permits one positive transfer")
        target = Address(recipient)
        self.attempted = gl.message.value
        self.recipient = str(target)
        ProbeRecipient(target).emit_transfer(value=gl.message.value)

    @gl.public.view
    def state(self) -> dict:
        return {"attempted": str(self.attempted), "recipient": self.recipient,
                "balance": str(self.balance)}
