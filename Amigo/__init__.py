import sys
import os

# Add Python directory to path so algomind is always found
pkg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Python')
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

import algomind
import algomind.schema
import algomind.position_manager
import algomind.risk_controller
import algomind.account_execution
import algomind.orderflow_lab
import algomind.orderflow_lab.schema

sys.modules['Amigo'] = algomind
sys.modules['Amigo.schema'] = algomind.schema
sys.modules['Amigo.position_manager'] = algomind.position_manager
sys.modules['Amigo.risk_controller'] = algomind.risk_controller
sys.modules['Amigo.account_execution'] = algomind.account_execution
sys.modules['Amigo.orderflow_lab'] = algomind.orderflow_lab
sys.modules['Amigo.orderflow_lab.schema'] = algomind.orderflow_lab.schema
