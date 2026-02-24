#!/usr/bin/env python3
"""Test Polymarket connectivity without requiring wallet."""
import requests
import time
from config import Config

def test_polygon_rpc():
    """Test Polygon RPC endpoint latency."""
    print("Testing Polygon RPC...")
    try:
        start = time.time()
        response = requests.post(
            Config.POLYGON_RPC,
            json={"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1},
            timeout=5
        )
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            block = int(data.get("result", "0x0"), 16) if "result" in data else 0
            print(f"✅ Polygon RPC: {latency:.0f}ms (Block: {block})")
            return True, latency
        else:
            print(f"❌ Polygon RPC returned status {response.status_code}")
            return False, 0
    except Exception as e:
        print(f"❌ Polygon RPC failed: {e}")
        return False, 0

def test_polymarket_api():
    """Test Polymarket CLOB API endpoint."""
    print("Testing Polymarket API...")
    try:
        start = time.time()
        response = requests.get(f"{Config.CLOB_URL}/markets", timeout=5)
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            markets = len(data.get("data", []))
            print(f"✅ Polymarket API: {latency:.0f}ms ({markets} markets)")
            return True, latency
        else:
            print(f"❌ Polymarket API returned status {response.status_code}")
            return False, 0
    except Exception as e:
        print(f"❌ Polymarket API failed: {e}")
        return False, 0

def test_binance_api():
    """Test Binance API endpoint."""
    print("Testing Binance API...")
    try:
        start = time.time()
        response = requests.get(
            f"{Config.BINANCE_API}/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=5
        )
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            price = float(data.get("price", 0))
            print(f"✅ Binance API: {latency:.0f}ms (BTC: ${price:,.2f})")
            return True, latency
        else:
            print(f"❌ Binance API returned status {response.status_code}")
            return False, 0
    except Exception as e:
        print(f"❌ Binance API failed: {e}")
        return False, 0

def estimate_cancel_replace_latency(polygon_lat, poly_lat):
    """Estimate cancel/replace loop latency."""
    # Cancel + Create both hit Polymarket CLOB
    estimated = poly_lat * 2
    return estimated

def main():
    """Run all connectivity tests."""
    print("=" * 60)
    print("Polymarket Bot - Connection Test")
    print("=" * 60)
    print()
    
    Config.print_config()
    print()
    
    # Run tests
    polygon_ok, polygon_lat = test_polygon_rpc()
    print()
    
    poly_ok, poly_lat = test_polymarket_api()
    print()
    
    binance_ok, binance_lat = test_binance_api()
    print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    if polygon_ok and poly_ok and binance_ok:
        print("✅ All connections successful!")
        print()
        
        # Estimate performance
        cancel_replace_lat = estimate_cancel_replace_latency(polygon_lat, poly_lat)
        print(f"Estimated Cancel/Replace Loop: {cancel_replace_lat:.0f}ms")
        
        if cancel_replace_lat < 200:
            print("   🟢 EXCELLENT - Highly competitive")
        elif cancel_replace_lat < 300:
            print("   🟡 GOOD - Competitive for 15-min markets")
        else:
            print("   🟠 OK - Target 1-hour+ markets")
        
        print()
        print("✅ Ready to run bot:")
        print("   python bot.py          # Dry-run mode")
        print("   python bot.py --live   # Live trading")
    else:
        print("❌ Some connections failed")
        print("   Check your internet connection and retry")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
