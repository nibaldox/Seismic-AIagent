import os
import sys

# ensure project root in path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('OPENROUTER_API_KEY','test_key')

from src.ai_agent.seismic_interpreter import load_agent_suite

def main():
    agents = load_agent_suite('config/agents_config.yaml')
    keys = sorted(agents.keys())
    print('AGENTS_KEYS:', keys)
    print('AGENTS_COUNT:', len(agents))
    print('PASS' if len(agents) in (5,6) else 'FAIL')

if __name__ == '__main__':
    main()
