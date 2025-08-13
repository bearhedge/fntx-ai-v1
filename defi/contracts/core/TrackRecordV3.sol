// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC721/ERC721Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "./interfaces/IFNTX.sol";

/**
 * @title TrackRecordV3
 * @dev Trading track record with NFT visualization and grace period for corrections
 * Each daily record becomes an NFT that can be burned and reissued within 24 hours
 */
contract TrackRecordV3 is 
    Initializable, 
    OwnableUpgradeable, 
    UUPSUpgradeable,
    ERC721Upgradeable,
    ERC721URIStorageUpgradeable 
{
    // FNTX token contract
    IFNTX public fntxToken;
    
    // Amount of FNTX to burn per record
    uint256 public burnAmount;
    
    // Grace period for corrections (24 hours)
    uint256 public constant GRACE_PERIOD = 24 hours;
    
    // NFT token ID counter
    uint256 private _tokenIdCounter;
    
    // Simplified daily record focusing on essential metrics
    struct DailyRecord {
        // Core identification
        uint32 date;              // YYYYMMDD format
        uint256 timestamp;        // Unix timestamp of submission
        uint8 version;           // Version number for corrections
        
        // Essential metrics hash
        bytes32 metricsHash;     // Hash of all 36 metrics stored off-chain
        
        // Key on-chain metrics for queries
        int128 netPnl;           // Net P&L in cents
        uint128 balanceEnd;      // Ending balance in cents
        uint16 winRate;          // Win rate % x10 (82.5% = 825)
        int32 sharpe30d;         // 30-day Sharpe ratio x100 (2.1 = 210)
        uint256 impliedTurnover; // Total volume traded
        
        // Status
        bool isImmutable;        // Becomes true after grace period
        uint256 nftTokenId;      // Associated NFT token ID
    }
    
    // Mapping from trader address to date to daily record
    mapping(address => mapping(uint256 => DailyRecord)) public records;
    
    // Mapping from NFT token ID to trader and date
    mapping(uint256 => address) public tokenTrader;
    mapping(uint256 => uint256) public tokenDate;
    
    // Track if a record exists
    mapping(address => mapping(uint256 => bool)) public recordExists;
    
    // Track trader's statistics
    mapping(address => uint256) public firstRecordDate;
    mapping(address => uint256) public lastRecordDate;
    mapping(address => uint256) public totalRecords;
    
    // IPFS base URI for NFT metadata
    string public baseTokenURI;
    
    // Events
    event RecordPosted(
        address indexed trader,
        uint256 indexed date,
        uint256 indexed tokenId,
        uint8 version,
        bytes32 metricsHash,
        int128 netPnl
    );
    
    event RecordCorrected(
        address indexed trader,
        uint256 indexed date,
        uint256 oldTokenId,
        uint256 newTokenId,
        uint8 newVersion
    );
    
    event RecordFinalized(
        address indexed trader,
        uint256 indexed date,
        uint256 tokenId
    );
    
    event BurnAmountUpdated(uint256 oldAmount, uint256 newAmount);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /**
     * @dev Initialize the contract
     */
    function initialize(
        address _fntxToken, 
        uint256 _burnAmount,
        string memory _name,
        string memory _symbol,
        string memory _baseTokenURI
    ) public initializer {
        __Ownable_init();
        __UUPSUpgradeable_init();
        __ERC721_init(_name, _symbol);
        __ERC721URIStorage_init();
        
        fntxToken = IFNTX(_fntxToken);
        burnAmount = _burnAmount;
        baseTokenURI = _baseTokenURI;
        _tokenIdCounter = 1; // Start token IDs at 1
    }

    /**
     * @dev Post a daily trading record with NFT minting
     */
    function postDailyRecord(
        uint32 date,
        bytes32 metricsHash,
        int128 netPnl,
        uint128 balanceEnd,
        uint16 winRate,
        int32 sharpe30d,
        uint256 impliedTurnover,
        string memory tokenURI
    ) external {
        require(date > 0, "Invalid date");
        require(metricsHash != bytes32(0), "Invalid metrics hash");
        
        // If record exists and is still in grace period, this is a correction
        if (recordExists[msg.sender][date]) {
            DailyRecord storage existingRecord = records[msg.sender][date];
            require(!existingRecord.isImmutable, "Record is immutable");
            require(
                block.timestamp <= existingRecord.timestamp + GRACE_PERIOD,
                "Grace period expired"
            );
            
            // Burn the old NFT
            _burn(existingRecord.nftTokenId);
            
            // Increment version
            uint8 newVersion = existingRecord.version + 1;
            
            // Mint new NFT
            uint256 newTokenId = _tokenIdCounter++;
            _safeMint(msg.sender, newTokenId);
            _setTokenURI(newTokenId, tokenURI);
            
            // Update record
            existingRecord.version = newVersion;
            existingRecord.metricsHash = metricsHash;
            existingRecord.netPnl = netPnl;
            existingRecord.balanceEnd = balanceEnd;
            existingRecord.winRate = winRate;
            existingRecord.sharpe30d = sharpe30d;
            existingRecord.impliedTurnover = impliedTurnover;
            existingRecord.nftTokenId = newTokenId;
            existingRecord.timestamp = block.timestamp; // Reset grace period
            
            // Update token mappings
            tokenTrader[newTokenId] = msg.sender;
            tokenDate[newTokenId] = date;
            
            emit RecordCorrected(
                msg.sender,
                date,
                existingRecord.nftTokenId,
                newTokenId,
                newVersion
            );
        } else {
            // New record
            require(!recordExists[msg.sender][date], "Record already exists");
            
            // Burn FNTX tokens
            fntxToken.burnFrom(msg.sender, burnAmount);
            
            // Mint NFT
            uint256 tokenId = _tokenIdCounter++;
            _safeMint(msg.sender, tokenId);
            _setTokenURI(tokenId, tokenURI);
            
            // Create record
            DailyRecord memory record = DailyRecord({
                date: date,
                timestamp: block.timestamp,
                version: 1,
                metricsHash: metricsHash,
                netPnl: netPnl,
                balanceEnd: balanceEnd,
                winRate: winRate,
                sharpe30d: sharpe30d,
                impliedTurnover: impliedTurnover,
                isImmutable: false,
                nftTokenId: tokenId
            });
            
            // Store record
            records[msg.sender][date] = record;
            recordExists[msg.sender][date] = true;
            
            // Update token mappings
            tokenTrader[tokenId] = msg.sender;
            tokenDate[tokenId] = date;
            
            // Update trader stats
            if (firstRecordDate[msg.sender] == 0 || date < firstRecordDate[msg.sender]) {
                firstRecordDate[msg.sender] = date;
            }
            if (date > lastRecordDate[msg.sender]) {
                lastRecordDate[msg.sender] = date;
            }
            totalRecords[msg.sender]++;
            
            emit RecordPosted(
                msg.sender,
                date,
                tokenId,
                1,
                metricsHash,
                netPnl
            );
        }
    }

    /**
     * @dev Finalize a record (can be called by anyone after grace period)
     */
    function finalizeRecord(address trader, uint256 date) external {
        require(recordExists[trader][date], "Record does not exist");
        
        DailyRecord storage record = records[trader][date];
        require(!record.isImmutable, "Already immutable");
        require(
            block.timestamp > record.timestamp + GRACE_PERIOD,
            "Grace period not expired"
        );
        
        record.isImmutable = true;
        
        emit RecordFinalized(trader, date, record.nftTokenId);
    }

    /**
     * @dev Correct a record within grace period (burns and remints NFT)
     * @param correctionFee Additional FNTX to burn for correction (50% of burn amount)
     */
    function correctRecord(
        uint32 date,
        bytes32 newMetricsHash,
        int128 netPnl,
        uint128 balanceEnd,
        uint16 winRate,
        int32 sharpe30d,
        uint256 impliedTurnover,
        string memory newTokenURI
    ) external {
        require(recordExists[msg.sender][date], "Record does not exist");
        
        DailyRecord storage record = records[msg.sender][date];
        require(!record.isImmutable, "Record is immutable");
        require(
            block.timestamp <= record.timestamp + GRACE_PERIOD,
            "Grace period expired"
        );
        
        // Burn correction fee (50% of original burn amount)
        uint256 correctionFee = burnAmount / 2;
        fntxToken.burnFrom(msg.sender, correctionFee);
        
        // Update via postDailyRecord (will handle NFT burn/mint)
        postDailyRecord(
            date,
            newMetricsHash,
            netPnl,
            balanceEnd,
            winRate,
            sharpe30d,
            impliedTurnover,
            newTokenURI
        );
    }

    /**
     * @dev Check if a record is still correctable
     */
    function isCorrectableRecord(address trader, uint256 date) external view returns (bool) {
        if (!recordExists[trader][date]) return false;
        
        DailyRecord memory record = records[trader][date];
        return !record.isImmutable && 
               block.timestamp <= record.timestamp + GRACE_PERIOD;
    }

    /**
     * @dev Get time remaining in grace period
     */
    function getGracePeriodRemaining(address trader, uint256 date) external view returns (uint256) {
        require(recordExists[trader][date], "Record does not exist");
        
        DailyRecord memory record = records[trader][date];
        if (record.isImmutable) return 0;
        
        uint256 gracePeriodEnd = record.timestamp + GRACE_PERIOD;
        if (block.timestamp >= gracePeriodEnd) return 0;
        
        return gracePeriodEnd - block.timestamp;
    }

    /**
     * @dev Get a specific daily record
     */
    function getRecord(address trader, uint256 date) external view returns (DailyRecord memory) {
        require(recordExists[trader][date], "Record does not exist");
        return records[trader][date];
    }

    /**
     * @dev Get trader statistics
     */
    function getTraderStats(address trader) external view returns (
        uint256 firstDate,
        uint256 lastDate,
        uint256 totalDays,
        uint256 immutableDays,
        uint256 currentBalance
    ) {
        firstDate = firstRecordDate[trader];
        lastDate = lastRecordDate[trader];
        totalDays = totalRecords[trader];
        
        // Count immutable records
        for (uint256 date = firstDate; date <= lastDate; date++) {
            if (recordExists[trader][date] && records[trader][date].isImmutable) {
                immutableDays++;
            }
        }
        
        // Get current balance from last record
        if (lastDate > 0) {
            currentBalance = records[trader][lastDate].balanceEnd;
        }
    }

    /**
     * @dev Update burn amount (only owner)
     */
    function updateBurnAmount(uint256 _newBurnAmount) external onlyOwner {
        require(_newBurnAmount > 0, "Burn amount must be greater than 0");
        
        uint256 oldAmount = burnAmount;
        burnAmount = _newBurnAmount;
        
        emit BurnAmountUpdated(oldAmount, _newBurnAmount);
    }

    /**
     * @dev Update base token URI (only owner)
     */
    function setBaseTokenURI(string memory _baseTokenURI) external onlyOwner {
        baseTokenURI = _baseTokenURI;
    }

    /**
     * @dev Get NFT token URI
     */
    function tokenURI(uint256 tokenId) public view override(ERC721Upgradeable, ERC721URIStorageUpgradeable) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    /**
     * @dev Override _burn to handle URI storage
     */
    function _burn(uint256 tokenId) internal override(ERC721Upgradeable, ERC721URIStorageUpgradeable) {
        super._burn(tokenId);
    }

    /**
     * @dev Override supportsInterface for multiple inheritance
     */
    function supportsInterface(bytes4 interfaceId) public view override(ERC721Upgradeable, ERC721URIStorageUpgradeable) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @dev Required by UUPSUpgradeable
     */
    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
}