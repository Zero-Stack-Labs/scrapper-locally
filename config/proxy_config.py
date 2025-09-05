from typing import Dict, List
import os
import random

class ProxyConfig:
    
    @classmethod
    def _get_endpoints_from_env(cls) -> List[str]:
        endpoints_str = os.getenv('OXYLABS_DATACENTER_ENDPOINTS')
        return [endpoint.strip() for endpoint in endpoints_str.split(',') if endpoint.strip()]
    
    @classmethod
    def get_random_oxylabs_config(cls) -> Dict:
        endpoints = cls._get_endpoints_from_env()
        endpoint = random.choice(endpoints)
        return {
            'endpoint': endpoint,
            'username': os.getenv('OXYLABS_DATACENTER_USERNAME', ''),
            'password': os.getenv('OXYLABS_DATACENTER_PASSWORD', '')
        }
