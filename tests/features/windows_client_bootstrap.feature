Feature: First-time Windows client setup without the optional Python launcher
  The trader can prepare a source checkout even when the py command is absent.

  Scenario: An existing CPython is discovered without py
    Given CPython 3.11 or 3.13 64-bit is installed in a standard user directory or PATH
    And the py launcher is absent
    When the trader runs setup_client.bat from the checkout
    Then the interpreter version and architecture are validated at runtime
    And the checkout is installed editable into its dedicated .venv
    And RPC, OptionMaster, and SpreadTrading packages are installed at pinned versions
    And the trader is told how to start update_client.bat

  Scenario: Python is not installed
    Given no compatible CPython 3.11 or 3.13 64-bit interpreter can be found
    When the trader runs setup_client.bat
    Then setup fails before creating or changing the virtual environment
    And it gives an official Python installer URL and a specific winget command
    And it does not automatically install system software

  Scenario: The operator supplies an incompatible interpreter
    Given the explicit PythonPath is Python 3.12 or 32-bit
    When the trader runs setup_client.bat with that path
    Then setup stops before installing packages
    And the requested CPython version and architecture are shown

  Scenario: A dependency installation fails
    Given the dedicated virtual environment was created successfully
    When a pip command fails
    Then setup returns failure without claiming the client is ready
    And it does not launch the trading GUI
