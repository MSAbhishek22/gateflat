// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title GateAudit — append-only audit log for TapeOut Gate decisions.
/// @notice Stores ONLY hashes + verdicts + receipt ids. Payload content
///   and secrets NEVER go onchain. A record proves a decision was logged
///   at a time by a sender; it does NOT prove the scan ran — the receipt's
///   replay string is the off-chain proof (re-run the scan, same verdict).
/// @dev Status 9 Nov 2026: WRITTEN, NOT COMPILED, NOT DEPLOYED.
///   No solc/Foundry in the Day-1 sandbox. Compile + testnet deploy is a
///   Week-2 step (Remix, free, no card). Do not cite an address until one
///   exists on the X Layer testnet explorer.
contract GateAudit {
    event GateDecision(
        uint256 indexed index,
        address indexed sender,
        bytes32 indexed payloadHash,
        uint8 verdict, // 0 = ALLOW, 1 = HOLD, 2 = BLOCK
        bytes32 rulesHash,
        string receiptId,
        uint256 timestamp
    );

    struct Decision {
        address sender;
        bytes32 payloadHash;
        uint8 verdict;
        bytes32 rulesHash;
        string receiptId;
        uint256 timestamp;
    }

    Decision[] private _decisions;

    /// @notice Log one gate decision. Callable by anyone: the log is
    ///   public evidence, and a spammer can only add their own entries.
    ///   Callers SHOULD be the gate operator; the event's `sender` field
    ///   makes that auditable.
    function recordDecision(
        bytes32 payloadHash,
        uint8 verdict,
        bytes32 rulesHash,
        string calldata receiptId
    ) external {
        require(verdict <= 2, "GateAudit: bad verdict");
        require(bytes(receiptId).length > 0, "GateAudit: empty receiptId");
        uint256 index = _decisions.length;
        _decisions.push(
            Decision({
                sender: msg.sender,
                payloadHash: payloadHash,
                verdict: verdict,
                rulesHash: rulesHash,
                receiptId: receiptId,
                timestamp: block.timestamp
            })
        );
        emit GateDecision(
            index, msg.sender, payloadHash, verdict, rulesHash,
            receiptId, block.timestamp
        );
    }

    function count() external view returns (uint256) {
        return _decisions.length;
    }

    function getDecision(uint256 index)
        external
        view
        returns (Decision memory)
    {
        require(index < _decisions.length, "GateAudit: out of range");
        return _decisions[index];
    }
}
