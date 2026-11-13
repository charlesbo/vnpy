Feature: Remote options trading workstation
  Scenario: Use an existing Python 3.13 installation
    Given the Windows trader has CPython 3.13 64-bit
    When the client bootstrap runs
    Then it creates the editable RPC client environment without requiring Python 3.11

  Scenario: Load options and spread applications in the RPC client
    Given the client is connected to the OpenCTP server through RPC
    When Trader starts
    Then OptionMaster and SpreadTrading are available in the Function menu
    And Black-76, Black-Scholes, and Binomial-Tree pricing return prices and Greeks

  Scenario: Connect while the Windows client is outside the office network
    Given the server is reachable through an approved VPN route
    When the trader starts an SSH local-forward tunnel
    Then Trader uses loopback RPC endpoints and the public internet never reaches raw RPC ports

  Scenario: Configure and trade an option combination
    Given the RPC server has published option contract metadata and market data
    When the trader configures OptionMaster and creates a multi-leg spread
    Then option prices and Greeks are calculated on the client and leg orders route to the server
    And partial fills are treated as unhedged risk until each leg is reconciled
