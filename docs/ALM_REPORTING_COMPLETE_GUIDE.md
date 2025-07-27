# ALM Reporting: Final Specification and Guide

## 1. Objective

The primary objective is to generate a daily, narrative-style financial report that provides a clear, chronologically accurate accounting of all events impacting the account's Net Asset Value (NAV).

The report must be generated from the perspective of an observer in **Hong Kong Time (HKT)**, even though the trading activity occurs during US market hours.

## 2. Core Logic & Structure

The report must follow a precise logical structure for each US Trading Day (defined as 16:00 EDT on Day D-1 to 16:00 EDT on Day D).

1.  **Start with Previous Official Close:** The timeline for a given day begins with the Official Closing NAV from the *previous* trading day. This is the starting point for all subsequent calculations.
2.  **Process Overnight & Pre-Market Events:** All events occurring after the previous close but before the current day's market open (e.g., assignments, pre-market trades) must be processed first. The NAV must be adjusted chronologically for each of these events.
3.  **State Market Open NAVs:** At the market open time (09:30 EDT / 21:30 HKT), the report must state two figures:
    *   The **Official Opening NAV** as reported by the broker.
    *   The **Calculated Opening NAV**, which is the result of the adjustments from the overnight/pre-market events.
4.  **Process Intraday Events:** All events during the trading day are then processed chronologically, with the NAV adjusted after each event or group of events. Trades occurring in a tight window should be grouped into a single narrative block with a net P&L impact.
5.  **Reconcile at Market Close:** The report for the day concludes by stating the **Official Closing NAV** and reconciling it against the final Calculated NAV.

## 3. Implementation Detail: Identifying Assignments vs. Expirations

A critical piece of logic in the data processing engine is the correct identification of assignments and expirations, which are often ambiguous in the raw data as both are logged as a `BookTrade`.

*   **The `BookTrade` Heuristic:**
    1.  If a `BookTrade` transaction involves an **option contract** (e.g., `SPY 250717C00628000`), it is an **Expiration**.
    2.  If a `BookTrade` transaction involves the **underlying stock** (e.g., `SPY`), it is an **Assignment**.

This logic is essential for correctly categorizing these events and their financial impacts in the database.

## 4. Ground Truth: The Role Model Example

The following manually created analysis for July 17-18, 2025, serves as the **definitive template and ground truth** for the required output. Any automated script **must** replicate this structure, narrative style, and financial logic precisely.

---

### **US Trading Day: Thursday, July 17, 2025**

*   **Market Open (21:30 HKT / 09:30 EDT):** The day begins.
    *   **Opening NAV:** 79,498.68 HKD

*   **Day Trades (00:46 - 00:50 HKT, July 18 / 12:46 - 12:50 EDT, July 17):** You adjust your option positions.
    *   **Events:** Based on the XML, you opened and closed a SPY 623 Put (the typo) and day-traded a SPY 628 Call, ultimately leaving a short SPY 626 Put and a short SPY 628 Call open.
    *   **Net P&L Impact:** The net result of these rapid trades was a small realized loss.
        *   Realized Loss: -6.46 USD
        *   Commissions: -5.83 USD
        *   **Total P&L Impact:** -12.29 USD * 7.8472 = **-96.46 HKD**
    *   **NAV becomes:** 79,498.68 - 96.46 = **79,402.22 HKD**

*   **Market Close (04:00 HKT, July 18 / 16:00 EDT, July 17):**
    *   **Event:** The market closes. Your open positions (short SPY 626 Put, short SPY 628 Call) are marked to the closing prices.
    *   **Mark-to-Market P&L:** The unrealized P&L for the day on these open positions is calculated by the broker.
        *   Unrealized P&L = (79,754.81 - 79,402.22) = **+352.59 HKD**
    *   **Official Closing NAV (at 16:00 EDT):** After all calculations, the official end-of-day NAV is booked.
        *   **Closing NAV: 79,754.81 HKD**

---

### **Overnight Period (July 17 Close to July 18 Open)**

*   **Assignment (04:20 HKT, July 18 / 16:20 EDT, July 17):**
    *   **Event:** Your short SPY 628 Call is assigned. Your option liability is replaced with a -100 share short position in SPY at a cost basis of $628.00/share.
    *   **NAV Impact:** This asset exchange has no immediate P&L impact.
    *   **NAV remains: 79,754.81 HKD**

---

### **US Trading Day: Friday, July 18, 2025**

*   **Pre-Market Cover Trade (13:15 HKT / 01:15 EDT, July 18):**
    *   **Event:** You cover the short stock position by buying 100 shares of SPY at $629.45.
    *   **P&L Impact:** This trade realizes the total loss from the assignment event.
        *   Realized Loss: (628.00 - 629.45) * 100 shares = -145.00 USD
        *   Commissions: -1.00 USD
        *   **Total P&L Impact:** -146.00 USD * 7.8472 = **-1,145.44 HKD**
    *   **NAV at 13:15 HKT (immediately after trade):** 79,754.81 (prior day's close) - 1,145.44 (realized loss) = **78,609.37 HKD**

*   **Market Open (21:30 HKT / 09:30 EDT):**
    *   **Opening NAV:** Your true opening NAV is **~78,609.37 HKD**, reflecting the overnight loss. The broker's "Official Opening NAV" of 79,754.81 does not yet include this pre-market trade.

*   **0DTE Trades (22:32 HKT / 10:32 EDT):**
    *   **Event:** You sell 1 SPY 629 Call and 1 SPY 626 Put.
    *   **P&L Impact (Premium Received):**
        *   Premium: (0.37 + 0.40) * 100 = 77.00 USD
        *   Commissions: -1.73 USD
        *   **Total P&L Impact:** 75.27 USD * 7.8472 = **+590.64 HKD**
    *   **NAV becomes:** 78,609.37 + 590.64 = **79,200.01 HKD**

*   **Market Close (04:00 HKT, July 19 / 16:00 EDT, July 18):**
    *   **Event:** Both options expire worthless. The premium is now fully realized.
    *   **Official Closing NAV:** After accounting for any minor MTM fluctuations on other positions, the final NAV is booked.
        *   **Closing NAV: 79,231.03 HKD**
    *   **Reconciliation:** The difference between our calculated NAV and the official one is 79,231.03 - 79,200.01 = **+31.02 HKD**, which is attributable to minor fees or other positions.

---

## 5. Automation Plan (Phase 2)

### 5.1. Automation Goal

The next critical step is to **fully automate the data ingestion pipeline**. The goal is to create a system that automatically, on a daily schedule:
1.  Fetches the latest data from IBKR using their Flex Query API.
2.  Updates the local PostgreSQL database with this new data, without creating duplicates.
3.  Allows the narrative report to be generated at will, reflecting the most current data available.

This will eliminate the need for any manual file downloads and ensure the database is always up-to-date.

### 5.2. Data Update Strategy: Idempotent MTD Refresh

The chosen strategy is the **Idempotent Month-to-Date (MTD) Refresh**. This approach is the most robust and self-healing.

*   **How it Works:**
    1.  **Daily MTD Fetch:** A script runs every day to fetch the **entire Month-to-Date (MTD)** report from the IBKR API.
    2.  **Idempotent Database Update:** The script uses an `INSERT ... ON CONFLICT DO UPDATE` command. When processing the downloaded data, it will update existing records (based on a unique key like `transactionID`) and insert new ones. This automatically handles new data, historical corrections, and catching up after missed runs.

### 5.3. File Management Strategy: Download-and-Replace

To remain efficient and minimize storage, a **"download-and-replace"** strategy will be used for the raw XML files.

*   **How it Works:**
    1.  **Download Today's MTD File:** The script fetches the latest MTD report (e.g., `Trades_MTD_20250719.xml`) and saves it to a structured directory (`04_data/ibkr_flexquery/YYYY/MM/`).
    2.  **Process & Update Database:** The script immediately uses this new file to update the database.
    3.  **Delete Yesterday's File:** After a successful database update, the script **immediately deletes the previous day's MTD file** (e.g., `Trades_MTD_20250718.xml`).

This ensures only the single, most recent MTD report is kept on disk, minimizing storage while maintaining the robustness of the idempotent refresh strategy.

## 6. Performance Architecture: Preventing Timeouts

To ensure the `generate_alm_report.py` script runs efficiently and does not time out as the database grows, a critical piece of database architecture has been implemented.

### 6.1. The Problem: Slow Queries and Timeouts

The reporting script works by fetching all events for a specific 24-hour period. Without an index, the database must perform a "full table scan" for every single day in the report. This means it reads every row in the `chronological_events` table to find the ones that match the date range. As the table grows, this process becomes exponentially slower and is the primary cause of application timeouts.

### 6.2. The Solution: Database Indexing

Indexes act like a highly efficient, sorted lookup table for the database, allowing it to find data for a specific date range almost instantly.

**These indexes are not optional; they are mandatory for the performance and scalability of the reporting system.**

**SQL Commands Used to Create Indexes:**
```sql
-- For the chronological_events table (the largest table)
CREATE INDEX idx_events_timestamp ON alm_reporting.chronological_events (event_timestamp);

-- For the stock_positions table (to optimize queries with OR conditions)
CREATE INDEX idx_positions_entry_date ON alm_reporting.stock_positions (entry_date);
CREATE INDEX idx_positions_exit_date ON alm_reporting.stock_positions (exit_date);
```

## 7. Guide to Automating the IBKR Flex Query Pipeline

This section provides the blueprint for the agent responsible for building the automated data pipeline.

### 7.1. Core Challenge: Asynchronous Report Generation

The IBKR Flex Query API is not a real-time data feed. It is an **asynchronous report delivery system**. A simple request-and-download will fail. The correct, robust workflow is:

1.  **Step A: Request Report.** The script makes an initial API call with the Flex Query ID and security token. The API immediately returns a `ReferenceCode`.
2.  **Step B: Poll for Status.** The script must wait (e.g., 15-30 seconds) and then make a second API call, sending the `ReferenceCode`.
3.  **Step C: Check Response.** If the report is not ready, the API will indicate it is still processing. The script must wait and poll again. If the report is ready, the API will respond with a download URL.
4.  **Step D: Download File.** The script can now use the URL to download the XML file.

**This request-poll-download cycle is the most critical part of the automation script and is the primary source of potential timeouts if not handled correctly.**

### 7.2. Recommended Scheduling Method: `systemd` Timers

While `cron` is a traditional option, it is highly recommended to use `systemd` timers on a modern Linux system for scheduling the daily task.

*   **Why `systemd` is better:**
    *   **Robust Environment:** Services run in a predictable, configurable environment, avoiding the `PATH` and environment variable issues common with `cron`.
    *   **Superior Logging:** All output (`stdout` and `stderr`) is automatically captured by `journalctl`, making debugging vastly simpler. You can see the full history, filter by date, and check the status of the service.
    *   **Better Control:** It's easy to start, stop, and check the status of the service and its corresponding timer (`systemctl status alm_update.timer`).

*   **Implementation:**
    1.  Create a `.service` file (e.g., `alm_update.service`) that defines how to run the Python automation script.
    2.  Create a `.timer` file (e.g., `alm_update.timer`) that defines the schedule (e.g., `OnCalendar=daily`, `Persistent=true`).
    3.  Install and enable the timer with `systemctl`.

### 7.3. Script Requirements

The final automation script must include:
-   Secure management of the IBKR API token (e.g., via environment variables).
-   Implementation of the request-poll-download cycle with appropriate wait times.
-   Comprehensive error handling for all network operations and file parsing.
-   Integration with the idempotent database update logic.
-   Clear logging to `stdout`/`stderr` so `systemd` can capture it.
