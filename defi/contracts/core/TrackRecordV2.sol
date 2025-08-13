// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "./interfaces/IFNTX.sol";

/**
 * @title TrackRecordV2
 * @dev Comprehensive on-chain trading track record with 36 fields
 * Stores complete daily trading data immutably on blockchain
 */
contract TrackRecordV2 is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    // FNTX token contract
    IFNTX public fntxToken;
    
    // Amount of FNTX to burn per record
    uint256 public burnAmount;
    
    // Comprehensive daily trading record (36 fields)
    struct DailyRecord {
        // Box 1: Identity & Time (3 fields)
        uint32 date;              // YYYYMMDD format
        uint32 tradingDayNum;     // Sequential trading day counter
        uint32 timestamp;         // HHMMSS format
        
        // Box 2: Account State (4 fields)
        uint128 balanceStart;     // Starting balance in cents
        uint128 balanceEnd;       // Ending balance in cents
        uint128 deposits;         // Daily deposits in cents
        uint128 withdrawals;      // Daily withdrawals in cents
        
        // Box 3: P&L Breakdown (5 fields)
        int128 grossPnl;          // Gross P&L in cents
        int64 commissions;        // Commissions paid (negative)
        int64 interestExpense;    // Interest expense (negative)
        int64 otherFees;          // Other fees (negative)
        int128 netPnl;            // Net P&L in cents
        
        // Box 4: Performance Metrics (6 fields)
        int32 netReturnPct;       // Net return % x1000 (0.524% = 524)
        int32 returnAnnualized;   // Annualized return % x10 (191.2% = 1912)
        int32 sharpe30d;          // 30-day Sharpe ratio x100 (2.1 = 210)
        int32 sortino30d;         // 30-day Sortino ratio x100 (2.8 = 280)
        int32 volatility30d;      // 30-day volatility % x100 (11.2% = 1120)
        int32 maxDrawdown30d;     // 30-day max drawdown % x100 (-2.1% = -210)
        
        // Box 5: Trading Activity (7 fields)
        uint16 contractsTotal;    // Total contracts traded
        uint16 putContracts;      // Put contracts sold
        uint16 callContracts;     // Call contracts sold
        uint64 premiumCollected;  // Premium collected in cents
        uint64 marginUsed;        // Margin/buying power used in cents
        uint16 positionSizePct;   // Position size as % of account x100 (1.0% = 100)
        uint256 impliedTurnover;  // Contracts x 100 x SPY price in cents
        
        // Box 6: Greeks (4 fields)
        int16 deltaExposure;      // Portfolio delta x100 (-0.12 = -12)
        int16 gammaExposure;      // Portfolio gamma x1000 (-0.008 = -8)
        int32 thetaIncome;        // Daily theta income in cents
        int16 vegaExposure;       // Portfolio vega x1 (-120 = -120)
        
        // Box 7: Win/Loss Tracking (4 fields)
        uint16 positionsExpired;  // Positions expired worthless (wins)
        uint16 positionsAssigned; // Positions assigned (losses)
        uint16 positionsStopped;  // Positions stopped out (losses)
        uint16 winRate;           // Win rate % x10 (82.5% = 825)
        
        // Box 8: Fund Metrics (3 fields)
        uint32 dpi;               // Distributions/Paid-In x10000 (0.15 = 1500)
        uint32 tvpi;              // Total Value/Paid-In x10000 (10.25 = 102500)
        uint32 rvpi;              // Residual Value/Paid-In x10000 (10.10 = 101000)
    }
    
    // Mapping from trader address to date to daily record
    mapping(address => mapping(uint256 => DailyRecord)) public records;
    
    // Track if a record exists
    mapping(address => mapping(uint256 => bool)) public recordExists;
    
    // Track trader's first and last record date
    mapping(address => uint256) public firstRecordDate;
    mapping(address => uint256) public lastRecordDate;
    mapping(address => uint256) public totalRecords;
    
    // Events
    event RecordPosted(
        address indexed trader,
        uint256 indexed date,
        uint32 tradingDayNum,
        int128 netPnl,
        uint256 impliedTurnover
    );
    
    event BurnAmountUpdated(uint256 oldAmount, uint256 newAmount);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /**
     * @dev Initialize the contract
     */
    function initialize(address _fntxToken, uint256 _burnAmount) public initializer {
        __Ownable_init();
        __UUPSUpgradeable_init();
        
        fntxToken = IFNTX(_fntxToken);
        burnAmount = _burnAmount;
    }

    /**
     * @dev Post a comprehensive daily trading record
     */
    function postDailyRecord(DailyRecord memory record) external {
        require(record.date > 0, "Invalid date");
        require(!recordExists[msg.sender][record.date], "Record already exists for this date");
        require(record.tradingDayNum > 0, "Invalid trading day number");
        
        // Verify balance consistency
        int256 calculatedEnd = int256(uint256(record.balanceStart)) + 
                              int256(uint256(record.deposits)) - 
                              int256(uint256(record.withdrawals)) + 
                              int256(record.netPnl);
        require(calculatedEnd == int256(uint256(record.balanceEnd)), "Balance mismatch");
        
        // Burn FNTX tokens
        fntxToken.burnFrom(msg.sender, burnAmount);
        
        // Store the record
        records[msg.sender][record.date] = record;
        recordExists[msg.sender][record.date] = true;
        
        // Update trader stats
        if (firstRecordDate[msg.sender] == 0 || record.date < firstRecordDate[msg.sender]) {
            firstRecordDate[msg.sender] = record.date;
        }
        if (record.date > lastRecordDate[msg.sender]) {
            lastRecordDate[msg.sender] = record.date;
        }
        totalRecords[msg.sender]++;
        
        // Emit event
        emit RecordPosted(
            msg.sender,
            record.date,
            record.tradingDayNum,
            record.netPnl,
            record.impliedTurnover
        );
    }

    /**
     * @dev Get a specific daily record
     */
    function getRecord(address trader, uint256 date) external view returns (DailyRecord memory) {
        require(recordExists[trader][date], "Record does not exist");
        return records[trader][date];
    }

    /**
     * @dev Get records for a date range
     */
    function getRecordRange(
        address trader,
        uint256 startDate,
        uint256 endDate
    ) external view returns (DailyRecord[] memory) {
        require(startDate <= endDate, "Invalid date range");
        
        // Count existing records in range
        uint256 count = 0;
        for (uint256 date = startDate; date <= endDate; date++) {
            if (recordExists[trader][date]) {
                count++;
            }
        }
        
        // Collect records
        DailyRecord[] memory result = new DailyRecord[](count);
        uint256 index = 0;
        for (uint256 date = startDate; date <= endDate; date++) {
            if (recordExists[trader][date]) {
                result[index] = records[trader][date];
                index++;
            }
        }
        
        return result;
    }

    /**
     * @dev Get trader statistics
     */
    function getTraderStats(address trader) external view returns (
        uint256 firstDate,
        uint256 lastDate,
        uint256 totalDays,
        int256 totalNetPnl,
        uint256 currentBalance
    ) {
        firstDate = firstRecordDate[trader];
        lastDate = lastRecordDate[trader];
        totalDays = totalRecords[trader];
        
        // Calculate total P&L and current balance if records exist
        if (lastDate > 0) {
            DailyRecord memory lastRecord = records[trader][lastDate];
            currentBalance = lastRecord.balanceEnd;
            
            // Calculate total net P&L by summing daily records
            // Note: This is a simplified calculation for demo
            // In production, might want to track this separately
            totalNetPnl = int256(currentBalance) - int256(records[trader][firstDate].balanceStart);
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
     * @dev Required by UUPSUpgradeable
     */
    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
}