import sys
import logging
from ib_insync import IB

# Set up logging to show info/warning
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_connection():
    ports = [7497, 7496, 4002, 4001]
    connected = False
    ib = IB()
    
    print("====================================================")
    print("Interactive Brokers API Connection Test Utility")
    print("====================================================")
    
    for port in ports:
        print(f"Attempting connection on port {port} (localhost)...")
        try:
            # Connect with a short timeout
            ib.connect('127.0.0.1', port, clientId=99, timeout=3)
            print(f"SUCCESS: Connected to IBKR on port {port}!")
            connected = True
            break
        except Exception as e:
            print(f"Failed to connect on port {port}: {str(e)}")
            
    if not connected:
        print("\nERROR: Could not connect to any IBKR TWS or IB Gateway instance.")
        print("Please check:")
        print("1. TWS or IB Gateway is running.")
        print("2. API settings are enabled ('Enable ActiveX and Socket Clients' is checked).")
        print("3. The port matches one of: 7497 (Paper TWS), 7496 (Live TWS), 4002 (Paper Gateway), 4001 (Live Gateway).")
        sys.exit(1)
        
    print("\n--- Account Summary ---")
    try:
        acc_summary = ib.accountSummary()
        if not acc_summary:
            print("No account summary data returned.")
        else:
            for item in acc_summary:
                if item.tag in ['NetLiquidation', 'TotalCashValue', 'UnrealizedPnL', 'RealizedPnL']:
                    print(f"{item.tag}: {item.value} {item.currency}")
    except Exception as e:
        print(f"Error fetching account summary: {e}")
        
    print("\n--- Active Positions ---")
    try:
        positions = ib.positions()
        if not positions:
            print("No active positions.")
        else:
            for pos in positions:
                contract = pos.contract
                print(f"Symbol: {contract.symbol:<6} | Shares: {pos.position:<5} | Average Cost: {pos.avgCost:<8.2f}")
    except Exception as e:
        print(f"Error fetching positions: {e}")
        
    # Clean disconnect
    ib.disconnect()
    print("\nDisconnected successfully. Test complete.")
    sys.exit(0)

if __name__ == '__main__':
    test_connection()
