#!/usr/bin/env python3
"""Startup script for the Urban Data API backend."""

import os
import sys
import subprocess

def check_requirements():
    """Check if required services are available."""
    print("Checking required services...")
    
    # Check MongoDB
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result_mongo = sock.connect_ex(('localhost', 27017))
    sock.close()
    if result_mongo == 0:
        print("[OK] MongoDB is running on localhost:27017")
    else:
        print("[FAIL] MongoDB is NOT running on localhost:27017")
        print("  Please start MongoDB: mongod")
        return False
    
    # Check MySQL
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result_mysql = sock.connect_ex(('localhost', 3306))
    sock.close()
    if result_mysql == 0:
        print("[OK] MySQL is running on localhost:3306")
    else:
        print("[FAIL] MySQL is NOT running on localhost:3306")
        print("  Please start MySQL")
        return False
    
    return True

def main():
    """Main entry point."""
    print("Urban Data API Backend Startup")
    print("=" * 50)
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Check services
    if not check_requirements():
        print("\n[FAIL] Setup incomplete. Please start the required services first.")
        sys.exit(1)
    
    print("\nStarting FastAPI server...")
    print("=" * 50)
    
    # Launch FastAPI
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ])
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



