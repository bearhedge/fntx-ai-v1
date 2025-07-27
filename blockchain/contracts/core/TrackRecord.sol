// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "./interfaces/IFNTX.sol";

/**
 * @title TrackRecord
 * @dev Upgradeable contract for storing immutable trading track records
 * Users burn FNTX tokens to post their daily performance
 */
contract TrackRecord is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    // FNTX token contract
    IFNTX public fntxToken;
    
    // Amount of FNTX to burn per record (can be updated)
    uint256 public burnAmount;
    
    // Mapping from user address to their daily record hashes
    // user => date => IPFS hash
    mapping(address => mapping(uint256 => bytes32)) public dailyRecords;
    
    // Event emitted when a record is posted
    event RecordPosted(
        address indexed trader,
        uint256 indexed date,
        bytes32 dataHash,
        uint256 tokensBurned
    );
    
    // Event emitted when burn amount is updated
    event BurnAmountUpdated(uint256 oldAmount, uint256 newAmount);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /**
     * @dev Initialize the contract
     * @param _fntxToken Address of the FNTX token contract
     * @param _burnAmount Initial amount of FNTX to burn per record
     */
    function initialize(address _fntxToken, uint256 _burnAmount) public initializer {
        __Ownable_init();
        __UUPSUpgradeable_init();
        
        fntxToken = IFNTX(_fntxToken);
        burnAmount = _burnAmount;
    }

    /**
     * @dev Post a daily trading record
     * @param date The date of the record (YYYYMMDD format)
     * @param dataHash IPFS hash of the detailed trading data
     */
    function postDailyRecord(uint256 date, bytes32 dataHash) external {
        require(dataHash != bytes32(0), "Invalid data hash");
        require(dailyRecords[msg.sender][date] == bytes32(0), "Record already exists for this date");
        
        // Burn FNTX tokens from the user
        fntxToken.burnFrom(msg.sender, burnAmount);
        
        // Store the record hash
        dailyRecords[msg.sender][date] = dataHash;
        
        // Emit event
        emit RecordPosted(msg.sender, date, dataHash, burnAmount);
    }

    /**
     * @dev Update the burn amount (only owner)
     * @param _newBurnAmount New amount of FNTX to burn per record
     */
    function updateBurnAmount(uint256 _newBurnAmount) external onlyOwner {
        require(_newBurnAmount > 0, "Burn amount must be greater than 0");
        
        uint256 oldAmount = burnAmount;
        burnAmount = _newBurnAmount;
        
        emit BurnAmountUpdated(oldAmount, _newBurnAmount);
    }

    /**
     * @dev Get a trader's record for a specific date
     * @param trader Address of the trader
     * @param date Date to query (YYYYMMDD format)
     * @return The IPFS hash of the record
     */
    function getRecord(address trader, uint256 date) external view returns (bytes32) {
        return dailyRecords[trader][date];
    }

    /**
     * @dev Batch get records for a trader over a date range
     * @param trader Address of the trader
     * @param startDate Start date (YYYYMMDD format)
     * @param endDate End date (YYYYMMDD format)
     * @return Array of IPFS hashes
     */
    function getRecordRange(
        address trader,
        uint256 startDate,
        uint256 endDate
    ) external view returns (bytes32[] memory) {
        require(startDate <= endDate, "Invalid date range");
        
        uint256 days = endDate - startDate + 1;
        bytes32[] memory records = new bytes32[](days);
        
        for (uint256 i = 0; i < days; i++) {
            records[i] = dailyRecords[trader][startDate + i];
        }
        
        return records;
    }

    /**
     * @dev Required by UUPSUpgradeable
     */
    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
}