import asyncio
import logging
import os
import json
from datetime import datetime
import shutil
import traceback
from jira_utils import fetch_jira_tickets
from ticket_processor import process_ticket, cleanup_old_tickets, active_tickets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/controller_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bugfix-controller")

# Configuration for log rotation (days to keep logs)
LOG_RETENTION_DAYS = os.environ.get('LOG_RETENTION_DAYS', 30)

# Track which tickets have already been processed
processed_tickets = set()

async def run_controller():
    """Main controller loop that runs every 60 seconds"""
    while True:
        try:
            # First, check if git is installed
            try:
                import subprocess
                result = subprocess.run(['which', 'git'], capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error("Git is not installed in the container. This will cause issues with git operations.")
                    logger.error("Please rebuild the container with git installed.")
                else:
                    logger.info(f"Git is installed at: {result.stdout.strip()}")
            except Exception as git_check_error:
                logger.error(f"Error checking for git: {git_check_error}")
            
            # Fetch new tickets from JIRA
            new_tickets = await fetch_jira_tickets()
            
            # Process each new ticket
            for ticket in new_tickets:
                ticket_id = ticket.get("ticket_id")
                if not ticket_id:
                    logger.warning("Received ticket without ID, skipping")
                    continue
                
                # Skip if already being processed or already processed
                if ticket_id in active_tickets or ticket_id in processed_tickets:
                    logger.info(f"Ticket {ticket_id} is already being processed or was previously processed, skipping")
                    continue
                    
                # Create log directory for this ticket
                ticket_log_dir = f"logs/{ticket_id}"
                os.makedirs(ticket_log_dir, exist_ok=True)
                
                # Log the input received
                with open(f"{ticket_log_dir}/controller_input.json", 'w') as f:
                    json.dump(ticket, f, indent=2)
                
                # Track that we're processing this ticket
                processed_tickets.add(ticket_id)
                
                # Process the ticket
                try:
                    # Create task to process ticket asynchronously
                    task = asyncio.create_task(process_ticket(ticket))
                    # Add error handling callback
                    task.add_done_callback(lambda t: handle_task_completion(t, ticket_id))
                except Exception as e:
                    logger.error(f"Error creating task for ticket {ticket_id}: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Clean up old tickets
            await cleanup_old_tickets()
            
            # Clean up old logs
            await cleanup_old_logs(int(LOG_RETENTION_DAYS))
            
            # Wait for next cycle
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Controller error: {str(e)}")
            # Log the error with timestamp
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "stacktrace": traceback.format_exc()
            }
            try:
                with open(f"logs/controller_errors.json", 'a') as f:
                    f.write(json.dumps(error_log) + "\n")
            except Exception as log_error:
                logger.error(f"Error writing to error log: {str(log_error)}")
            
            await asyncio.sleep(60)

def handle_task_completion(task, ticket_id):
    """Handle completion of task processing"""
    try:
        # Check if task raised an exception
        exc = task.exception()
        if exc:
            logger.error(f"Task for ticket {ticket_id} failed: {str(exc)}")
            logger.error(traceback.format_exc())
    except asyncio.CancelledError:
        logger.warning(f"Task for ticket {ticket_id} was cancelled")
    except Exception as e:
        logger.error(f"Error handling task completion for {ticket_id}: {str(e)}")

async def cleanup_old_logs(days):
    """Delete logs older than the specified number of days"""
    try:
        current_time = datetime.now()
        log_dirs = [d for d in os.listdir("logs") if os.path.isdir(os.path.join("logs", d))]
        
        for log_dir in log_dirs:
            dir_path = os.path.join("logs", log_dir)
            
            # Skip if not a ticket log directory
            if not (log_dir.startswith("DEMO-") or log_dir.startswith("BUG-") or log_dir.startswith("FEAT-") or log_dir.startswith("SCRUM-")):
                continue
                
            # Check modification time of directory
            mtime = os.path.getmtime(dir_path)
            mod_date = datetime.fromtimestamp(mtime)
            
            # If older than retention period, delete
            if (current_time - mod_date).days > days:
                logger.info(f"Deleting old logs for ticket {log_dir} (last modified {mod_date.isoformat()})")
                shutil.rmtree(dir_path)
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {str(e)}")

def collate_logs(ticket_id):
    """Collect all logs for a ticket into a single structured file"""
    try:
        ticket_log_dir = f"logs/{ticket_id}"
        if not os.path.exists(ticket_log_dir):
            logger.warning(f"No logs found for ticket {ticket_id}")
            return
            
        # Initialize structure for collated logs
        collated_logs = {
            "ticket_id": ticket_id,
            "collated_at": datetime.now().isoformat(),
            "agents": {}
        }
        
        # Collect logs from each agent
        for agent in ["planner", "developer", "qa", "communicator"]:
            agent_logs = {}
            
            # Input logs
            input_file = f"{ticket_log_dir}/{agent}_input.json"
            if os.path.exists(input_file):
                with open(input_file, 'r') as f:
                    agent_logs["input"] = json.load(f)
            
            # Output logs
            output_file = f"{ticket_log_dir}/{agent}_output.json"
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    agent_logs["output"] = json.load(f)
            
            # Error logs
            error_file = f"{ticket_log_dir}/{agent}_errors.json"
            if os.path.exists(error_file):
                with open(error_file, 'r') as f:
                    lines = f.readlines()
                    agent_logs["errors"] = [json.loads(line) for line in lines if line.strip()]
            
            collated_logs["agents"][agent] = agent_logs
        
        # Save collated logs
        with open(f"{ticket_log_dir}/collated_logs.json", 'w') as f:
            json.dump(collated_logs, f, indent=2)
            
        logger.info(f"Logs collated successfully for ticket {ticket_id}")
    except Exception as e:
        logger.error(f"Error collating logs for ticket {ticket_id}: {str(e)}")

def start_controller():
    """Start the controller loop"""
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_controller())
    except KeyboardInterrupt:
        logger.info("Controller stopping due to keyboard interrupt")
    finally:
        loop.close()

if __name__ == "__main__":
    start_controller()