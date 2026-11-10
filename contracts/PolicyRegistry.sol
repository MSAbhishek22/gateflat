// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title PolicyRegistry — allowlist / blocklist of destination contracts.
/// @notice The onchain source of truth for "may the gate dispatch to this
///   address?". The off-chain gate reads this contract before dispatch;
///   an address on NEITHER list is UNKNOWN and the gate HOLDs it.
/// @dev Status 9 Nov 2026: WRITTEN, NOT COMPILED, NOT DEPLOYED.
///   No solc/Foundry in the Day-1 sandbox. Compile + testnet deploy is a
///   Week-2 step. Honest limit: v1 has a single owner (the deployer).
///   That is a pragmatic starting point for a hackathon demo, not a
///   decentralisation claim — a multisig owner is a stated v2 step.
///   A blocklisted address always wins over an allowlisted one.
contract PolicyRegistry {
    event AllowedSet(address indexed target, bool allowed, address setter);
    event BlockedSet(address indexed target, bool blocked, address setter);
    event OwnershipTransferred(address indexed from, address indexed to);

    address public owner;
    mapping(address => bool) private _allowed;
    mapping(address => bool) private _blocked;

    modifier onlyOwner() {
        require(msg.sender == owner, "PolicyRegistry: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address next) external onlyOwner {
        require(next != address(0), "PolicyRegistry: zero owner");
        emit OwnershipTransferred(owner, next);
        owner = next;
    }

    function setAllowed(address target, bool allowed) external onlyOwner {
        _allowed[target] = allowed;
        emit AllowedSet(target, allowed, msg.sender);
    }

    function setBlocked(address target, bool blocked) external onlyOwner {
        _blocked[target] = blocked;
        emit BlockedSet(target, blocked, msg.sender);
    }

    function isAllowed(address target) external view returns (bool) {
        return _allowed[target];
    }

    function isBlocked(address target) external view returns (bool) {
        return _blocked[target];
    }

    /// @notice Single source of truth for the gate: BLOCK > ALLOW > UNKNOWN.
    /// @return 0 = UNKNOWN, 1 = ALLOW, 2 = BLOCK
    function status(address target) external view returns (uint8) {
        if (_blocked[target]) return 2;
        if (_allowed[target]) return 1;
        return 0;
    }
}
