from app.agents import get_agent
from app.tools import get_tool

class Registry:
    def __init__(self):
        pass
        
    def find_agent(self, name: str):
        return get_agent(name)
        
    def find_tool(self, name: str):
        return get_tool(name)

registry = Registry()
