# setup_env.py

import os
import sys
import shutil

def setup_environment(env_type):
    """Set up environment variables based on the specified type (dev/prod)."""
    env_file = '.env.development' if env_type == 'dev' else '.env.production'
    
    # Create default environment file if it doesn't exist
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write(f'FLASK_APP=app.py\n')
            f.write(f'FLASK_DEBUG={"1" if env_type == "dev" else "0"}\n')
            f.write(f'ENV={env_type}\n')
            if env_type == 'prod':
                f.write('REDIRECT_URI=https://foodlog.theespeys.com/oauth2callback\n')
            else:
                f.write('REDIRECT_URI=http://localhost:5001/foodlog/oauth2callback\n')
    
    # Copy the environment file to .env
    shutil.copy2(env_file, '.env')
    print(f"Environment set up for {env_type} mode")

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ['dev', 'prod']:
        print("Usage: python setup_env.py [dev|prod]")
        sys.exit(1)
    
    setup_environment(sys.argv[1]) 