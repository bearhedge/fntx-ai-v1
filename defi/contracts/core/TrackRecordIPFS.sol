// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC721/ERC721Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "./interfaces/IFNTX.sol";

/**
 * @title TrackRecordIPFS
 * @dev Cheaper version using IPFS - stores only hash on-chain
 * Full 36 fields + ASCII art stored on IPFS
 * Gas cost: ~50,000-80,000 (vs 200,000+ for full on-chain)
 */
contract TrackRecordIPFS is 
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
    
    // Minimal on-chain record with IPFS hash
    struct DailyRecord {
        uint32 date;              // YYYYMMDD format
        uint256 timestamp;        // Unix timestamp of submission
        uint8 version;           // Version number for corrections
        
        // IPFS hash containing all 36 metrics + ASCII art
        string ipfsHash;         // e.g., "QmXoypizjW3WknFjJnKLwHCnL72vedxjQkDDP..."
        
        // Minimal on-chain metrics for basic queries
        int128 netPnl;           // Net P&L in cents
        uint16 winRate;          // Win rate % x10 (82.5% = 825)
        
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
    mapping(address => int256) public totalNetPnl;
    
    // Events
    event RecordPosted(
        address indexed trader,
        uint256 indexed date,
        uint256 indexed tokenId,
        string ipfsHash,
        int128 netPnl,
        uint16 winRate
    );
    
    event RecordCorrected(
        address indexed trader,
        uint256 indexed date,
        uint256 oldTokenId,
        uint256 newTokenId,
        string newIpfsHash,
        uint8 newVersion
    );
    
    event RecordFinalized(
        address indexed trader,
        uint256 indexed date,
        uint256 tokenId
    );

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
        string memory _symbol
    ) public initializer {
        __Ownable_init();
        __UUPSUpgradeable_init();
        __ERC721_init(_name, _symbol);
        __ERC721URIStorage_init();
        
        fntxToken = IFNTX(_fntxToken);
        burnAmount = _burnAmount;
        _tokenIdCounter = 1; // Start token IDs at 1
    }

    /**
     * @dev Post a daily trading record with IPFS storage
     * @param date Trading date in YYYYMMDD format
     * @param ipfsHash IPFS hash containing full data and ASCII art
     * @param netPnl Net P&L for basic queries
     * @param winRate Win rate for basic queries
     * @param tokenURI Full IPFS URI for NFT metadata
     */
    function postDailyRecord(
        uint32 date,
        string memory ipfsHash,
        int128 netPnl,
        uint16 winRate,
        string memory tokenURI
    ) external {
        require(date > 0, "Invalid date");
        require(bytes(ipfsHash).length > 0, "Invalid IPFS hash");
        
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
            existingRecord.ipfsHash = ipfsHash;
            existingRecord.netPnl = netPnl;
            existingRecord.winRate = winRate;
            existingRecord.nftTokenId = newTokenId;
            existingRecord.timestamp = block.timestamp; // Reset grace period
            
            // Update token mappings
            tokenTrader[newTokenId] = msg.sender;
            tokenDate[newTokenId] = date;
            
            // Update total P&L
            totalNetPnl[msg.sender] = totalNetPnl[msg.sender] - existingRecord.netPnl + netPnl;
            
            emit RecordCorrected(
                msg.sender,
                date,
                existingRecord.nftTokenId,
                newTokenId,
                ipfsHash,
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
                ipfsHash: ipfsHash,
                netPnl: netPnl,
                winRate: winRate,
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
            totalNetPnl[msg.sender] += netPnl;
            
            emit RecordPosted(
                msg.sender,
                date,
                tokenId,
                ipfsHash,
                netPnl,
                winRate
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
        int256 totalPnl,
        uint256 avgWinRate
    ) {
        firstDate = firstRecordDate[trader];
        lastDate = lastRecordDate[trader];
        totalDays = totalRecords[trader];
        totalPnl = totalNetPnl[trader];
        
        // Calculate average win rate
        if (totalDays > 0) {
            uint256 totalWinRate = 0;
            for (uint256 date = firstDate; date <= lastDate; date++) {
                if (recordExists[trader][date]) {
                    totalWinRate += records[trader][date].winRate;
                }
            }
            avgWinRate = totalWinRate / totalDays;
        }
    }

    /**
     * @dev Get IPFS data for verification
     * Frontend/CLI will fetch from IPFS using this hash
     */
    function getIPFSHash(address trader, uint256 date) external view returns (string memory) {
        require(recordExists[trader][date], "Record does not exist");
        return records[trader][date].ipfsHash;
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
     * @dev Update burn amount (only owner)
     */
    function updateBurnAmount(uint256 _newBurnAmount) external onlyOwner {
        require(_newBurnAmount > 0, "Burn amount must be greater than 0");
        burnAmount = _newBurnAmount;
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