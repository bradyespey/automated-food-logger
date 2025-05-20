import os
import shutil
from pathlib import Path

def setup_environment(env_type):
    """Setup environment files based on type (dev/prod)"""
    base_dir = Path(__file__).parent
    env_file = base_dir / f'.env.{env_type}'
    
    # Create .env file from template
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    # Write to .env
    with open(base_dir / '.env', 'w') as f:
        f.write(env_content)
    
    print(f"Environment set to {env_type}")
    print(f"Using settings from {env_file}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in ['dev', 'prod']:
        print("Usage: python setup_env.py [dev|prod]")
        sys.exit(1)
    
    setup_environment(sys.argv[1]) 