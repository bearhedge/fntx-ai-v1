// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";

/**
 * @title FNTX Token
 * @dev Simple ERC20 token with burn functionality
 * Total supply: 1 trillion tokens
 * All tokens minted to deployer
 */
contract FNTX is ERC20, ERC20Burnable {
    uint256 public constant TOTAL_SUPPLY = 1_000_000_000_000 * 10**18; // 1 trillion with 18 decimals

    constructor() ERC20("FNTX", "FNTX") {
        // Mint entire supply to deployer
        _mint(msg.sender, TOTAL_SUPPLY);
    }

    /**
     * @dev Returns the number of decimals used
     */
    function decimals() public pure override returns (uint8) {
        return 18;
    }
}