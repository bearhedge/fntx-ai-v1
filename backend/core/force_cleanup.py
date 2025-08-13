#!/usr/bin/env python3
"""
Force cleanup ghost connections to IB Gateway
"""
import socket
import struct
import subprocess
import time

def force_cleanup_ghost_connections():
    """Aggressively clean up CLOSE_WAIT connections to port 4001"""
    print("🔧 Force cleaning ghost connections to IB Gateway...")
    
    try:
        # Get list of CLOSE_WAIT connections to port 4001
        result = subprocess.run(
            "ss -tn state close-wait | grep ':4001'", 
            shell=True, capture_output=True, text=True
        )
        
        if result.stdout:
            connections = result.stdout.strip().split('\n')
            print(f"Found {len(connections)} ghost connections:")
            
            for conn in connections:
                print(f"  - {conn}")
                
                # Try to extract local port and force close with SO_LINGER
                parts = conn.split()
                if len(parts) >= 2:
                    local_addr = parts[1]  # Local address:port
                    if ':' in local_addr:
                        try:
                            port_part = local_addr.split(':')[-1]
                            local_port = int(port_part)
                            
                            # Create socket with SO_LINGER to force RST
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            # Set SO_LINGER with 0 timeout to force immediate RST
                            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 
                                          struct.pack('ii', 1, 0))
                            try:
                                sock.bind(('127.0.0.1', local_port))
                                print(f"  ✅ Forced close on port {local_port}")
                            except OSError as e:
                                print(f"  ⚠️  Could not bind to port {local_port}: {e}")
                            finally:
                                sock.close()
                                
                        except (ValueError, OSError) as e:
                            print(f"  ❌ Could not process {local_addr}: {e}")
            
            print("⏳ Waiting 5 seconds for cleanup to take effect...")
            time.sleep(5)
            
            # Check if cleanup worked
            result2 = subprocess.run(
                "ss -tn state close-wait | grep ':4001'", 
                shell=True, capture_output=True, text=True
            )
            
            remaining = len(result2.stdout.strip().split('\n')) if result2.stdout.strip() else 0
            print(f"📊 Remaining ghost connections: {remaining}")
            
            if remaining == 0:
                print("✅ All ghost connections cleared!")
                return True
            else:
                print("⚠️  Some connections remain - may need IB Gateway restart")
                return False
                
        else:
            print("✅ No ghost connections found")
            return True
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

if __name__ == "__main__":
    success = force_cleanup_ghost_connections()
    if success:
        print("\n🎯 Try running your trading script now!")
    else:
        print("\n🔄 Consider restarting IB Gateway if the script still fails")