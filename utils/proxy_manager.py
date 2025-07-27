#!/usr/bin/env python3
import os
import random
import requests
import time
from typing import List, Dict, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ProxyManager:
    """
    Manages proxy rotation for requests to avoid IP blocking.
    Supports both free and paid proxy services.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProxyManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ProxyManager._initialized:
            return
            
        self.current_proxy = None
        self.free_proxies = []
        self.proxy_index = 0
        self.failed_proxies = set()
        
        ProxyManager._initialized = True
        
        # Check if running in container to enable proxy usage
        self.use_proxy = os.path.exists('/.dockerenv') or os.environ.get('KUBERNETES_SERVICE_HOST')
        
        if self.use_proxy:
            logger.info("🌐 Container environment detected - proxy rotation enabled")
            self._load_free_proxies()
        else:
            logger.info("🏠 Local environment detected - using direct connection")
    
    def _load_free_proxies(self):
        """Load free proxy list from various sources"""
        free_proxy_list = []
        
        # Try to fetch from free proxy APIs first
        self._fetch_free_proxies_from_api()
        
        # Add some known working free proxies as fallback
        if not self.free_proxies:
            free_proxy_list = [
                # These are public proxies - they change frequently and may not work
                {"http": "http://proxy.toolip.io:31280", "https": "http://proxy.toolip.io:31280"},
                {"http": "http://free-proxy-list.net", "https": "http://free-proxy-list.net"},
                # Add more as needed
            ]
            self.free_proxies = free_proxy_list
        
        logger.info(f"📋 Loaded {len(self.free_proxies)} free proxy servers")
    
    def _fetch_free_proxies_from_api(self):
        """Fetch free proxies from public APIs (use with caution)"""
        try:
            # Try ProxyList API (free tier)
            response = requests.get("https://www.proxy-list.download/api/v1/get?type=http", timeout=10)
            if response.status_code == 200:
                proxies = response.text.strip().split('\n')
                for proxy in proxies[:3]:  # Limit to 3 proxies
                    if proxy and ':' in proxy:
                        proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
                        self.free_proxies.append(proxy_dict)
                        logger.debug(f"🆓 Added free proxy: {proxy}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch free proxies from API: {e}")
            
        # Try backup source
        try:
            # ProxyScrape API (another free source)
            response = requests.get("https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=US&ssl=all&anonymity=all", timeout=10)
            if response.status_code == 200:
                proxies = response.text.strip().split('\n')
                for proxy in proxies[:3]:  # Limit to 3 more proxies
                    if proxy and ':' in proxy:
                        proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
                        self.free_proxies.append(proxy_dict)
                        logger.debug(f"🆓 Added free proxy from ProxyScrape: {proxy}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch free proxies from ProxyScrape: {e}")
    
    def get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Get current proxy configuration"""
        if not self.use_proxy:
            return None
            
        # Check for paid proxy services via environment variables
        paid_proxy = self._get_paid_proxy_config()
        if paid_proxy:
            return paid_proxy
            
        # Fall back to free proxies
        return self._get_free_proxy()
    
    def _get_paid_proxy_config(self) -> Optional[Dict[str, str]]:
        """Get paid proxy configuration from environment variables"""
        
        # ProxyMesh (paid service) - with multiple endpoints for rotation
        proxymesh_user = os.environ.get('PROXYMESH_USER')
        proxymesh_pass = os.environ.get('PROXYMESH_PASS')
        
        if proxymesh_user and proxymesh_pass:
            # ProxyMesh has multiple proxy pools - rotate between them
            proxymesh_endpoints = [
                ("us-ca.proxymesh.com", "31280"),      # US West datacenter
                ("us-il.proxymesh.com", "31280"),      # US Central datacenter  
                ("us-ny.proxymesh.com", "31280"),      # US East datacenter
                ("us-wa.proxymesh.com", "31280"),      # US West datacenter 2
                ("us-tx.proxymesh.com", "31280"),      # US South datacenter
                ("open.proxymesh.com", "31280"),       # Open proxy pool
                ("rotating-residential.proxymesh.com", "31280")  # Residential pool if available
            ]
            
            # Rotate through different endpoints
            endpoint_index = self.proxy_index % len(proxymesh_endpoints)
            host, port = proxymesh_endpoints[endpoint_index]
            
            logger.debug(f"🔍 ProxyMesh rotation: proxy_index={self.proxy_index}, endpoint_index={endpoint_index}")
            
            # Increment proxy index for next call
            self.proxy_index += 1
            
            proxy_url = f"http://{proxymesh_user}:{proxymesh_pass}@{host}:{port}"
            logger.info(f"🔐 Using ProxyMesh: {host}:{port} (endpoint {endpoint_index + 1}/{len(proxymesh_endpoints)})")
            return {"http": proxy_url, "https": proxy_url}
        
        # Bright Data / Luminati (paid service)
        brightdata_host = os.environ.get('BRIGHTDATA_HOST')
        brightdata_port = os.environ.get('BRIGHTDATA_PORT', '22225')
        brightdata_user = os.environ.get('BRIGHTDATA_USER')
        brightdata_pass = os.environ.get('BRIGHTDATA_PASS')
        
        if brightdata_host and brightdata_user and brightdata_pass:
            proxy_url = f"http://{brightdata_user}:{brightdata_pass}@{brightdata_host}:{brightdata_port}"
            logger.info(f"🔐 Using Bright Data: {brightdata_host}:{brightdata_port}")
            return {"http": proxy_url, "https": proxy_url}
        
        # ScraperAPI (paid service) - Best for avoiding detection
        scraperapi_key = os.environ.get('SCRAPERAPI_KEY')
        if scraperapi_key:
            # For heavily protected sites like Footlocker, we need Ultra Premium
            # Return special marker to use ScraperAPI API instead of proxy
            logger.info("🔐 Using ScraperAPI Ultra Premium (API mode for heavily protected sites)")
            return {"scraperapi_key": scraperapi_key, "mode": "api", "ultra_premium": True}
        
        return None
    
    def _get_free_proxy(self) -> Optional[Dict[str, str]]:
        """Get next free proxy from rotation"""
        if not self.free_proxies:
            logger.warning("⚠️ No free proxies available")
            return None
        
        # Filter out failed proxies
        available_proxies = [p for i, p in enumerate(self.free_proxies) if i not in self.failed_proxies]
        
        if not available_proxies:
            logger.warning("⚠️ All proxies have failed, resetting failure list")
            self.failed_proxies.clear()
            available_proxies = self.free_proxies
        
        # Rotate through available proxies
        proxy = available_proxies[self.proxy_index % len(available_proxies)]
        self.proxy_index += 1
        
        return proxy
    
    def mark_proxy_failed(self, proxy: Dict[str, str]):
        """Mark a proxy as failed"""
        if proxy in self.free_proxies:
            index = self.free_proxies.index(proxy)
            self.failed_proxies.add(index)
            logger.warning(f"❌ Marked proxy as failed: {proxy.get('http', 'Unknown')}")
    
    def test_proxy(self, proxy: Dict[str, str]) -> bool:
        """Test if a proxy is working"""
        try:
            test_url = "https://httpbin.org/ip"
            response = requests.get(test_url, proxies=proxy, timeout=10)
            if response.status_code == 200:
                ip_info = response.json()
                logger.info(f"✅ Proxy test successful. External IP: {ip_info.get('origin', 'Unknown')}")
                return True
        except Exception as e:
            logger.warning(f"❌ Proxy test failed: {e}")
        return False
    
    def get_working_proxy(self) -> Optional[Dict[str, str]]:
        """Get a working proxy by testing multiple ones"""
        for _ in range(min(5, len(self.free_proxies))):  # Try max 5 proxies
            proxy = self.get_proxy_config()
            if proxy and self.test_proxy(proxy):
                return proxy
            elif proxy:
                self.mark_proxy_failed(proxy)
        
        logger.error("❌ No working proxies found")
        return None

# Global proxy manager instance
proxy_manager = ProxyManager()