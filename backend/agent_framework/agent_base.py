
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class Agent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.status = AgentStatus.PENDING
        self.input_data: Optional[Dict[str, Any]] = None
        self.output_data: Optional[Dict[str, Any]] = None
        self.logs: List[Dict[str, str]] = []

    def log(self, message: str) -> None:
        """Add a timestamped log message"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        self.logs.append(log_entry)

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data and return results"""
        pass

    def report(self, max_logs: int = 10) -> Dict[str, Any]:
        """Generate a report of the agent's current state"""
        return {
            "name": self.name,
            "status": self.status.value,
            "recent_logs": self.logs[-max_logs:] if self.logs else [],
            "output": self.output_data
        }

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing wrapper that handles status and errors"""
        self.input_data = input_data
        self.status = AgentStatus.RUNNING
        self.log(f"{self.name} started processing")
        
        try:
            self.output_data = self.run(input_data)
            self.status = AgentStatus.SUCCESS
            self.log(f"{self.name} completed successfully")
            return self.output_data
        except Exception as e:
            self.status = AgentStatus.FAILED
            error_msg = f"{self.name} failed: {str(e)}"
            self.log(error_msg)
            self.output_data = {"error": error_msg}
            return self.output_data

