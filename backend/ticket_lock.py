
"""
Module for managing ticket locks to prevent duplicate processing
"""
import os
import logging
import asyncio
import tempfile
import time
from typing import Optional
from datetime import datetime, timedelta
import fcntl  # File locking for more reliable locking

logger = logging.getLogger("ticket-lock")

class TicketLockManager:
    """Class for managing ticket locks"""
    
    def __init__(self, lock_dir: Optional[str] = None):
        """
        Initialize the lock manager
        
        Args:
            lock_dir: Directory to store lock files. If None, a system temp directory is used.
        """
        if lock_dir:
            self.lock_dir = lock_dir
            os.makedirs(lock_dir, exist_ok=True)
        else:
            # Use system temp directory
            self.lock_dir = os.path.join(tempfile.gettempdir(), "ticket_locks")
            os.makedirs(self.lock_dir, exist_ok=True)
            
        logger.info(f"Using lock directory: {self.lock_dir}")
    
    async def acquire_lock(self, ticket_id: str, timeout: int = 0) -> bool:
        """
        Try to acquire a lock for a ticket using file locking for reliability
        
        Args:
            ticket_id: ID of the ticket to lock
            timeout: Seconds to wait for lock (0 means don't wait)
            
        Returns:
            bool: True if lock was acquired, False otherwise
        """
        lock_file_path = os.path.join(self.lock_dir, f"{ticket_id}.lock")
        
        # Check if lock file exists and is not stale
        start_time = time.time()
        lock_file = None
        
        try:
            while True:
                try:
                    # Try to open and exclusively lock the file
                    lock_file = open(lock_file_path, 'w+')
                    
                    # Use non-blocking for first attempt, then blocking if timeout specified
                    fcntl_op = fcntl.LOCK_EX | fcntl.LOCK_NB if timeout == 0 else fcntl.LOCK_EX
                    
                    fcntl.flock(lock_file.fileno(), fcntl_op)
                    
                    # If we got here, we have the lock
                    lock_file.write(f"{datetime.now().isoformat()}\n")
                    lock_file.write(f"{os.getpid()}\n")
                    lock_file.flush()
                    logger.info(f"Lock acquired for ticket {ticket_id}")
                    
                    # Keep the file handle open to maintain the lock
                    # We'll store it as an instance attribute so it stays open
                    setattr(self, f"_lock_file_{ticket_id}", lock_file)
                    return True
                    
                except IOError as e:
                    if timeout == 0:
                        # Non-blocking mode failed to acquire lock
                        logger.info(f"Could not acquire lock for ticket {ticket_id} (already locked)")
                        return False
                    
                    # If we've waited long enough, give up
                    if timeout > 0 and (time.time() - start_time) > timeout:
                        logger.warning(f"Timeout waiting for lock on ticket {ticket_id}")
                        return False
                        
                    # Wait a bit before trying again
                    await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error acquiring lock for {ticket_id}: {str(e)}")
            if lock_file:
                try:
                    lock_file.close()
                except:
                    pass
            return False
    
    async def release_lock(self, ticket_id: str) -> bool:
        """
        Release a lock for a ticket
        
        Args:
            ticket_id: ID of the ticket to unlock
            
        Returns:
            bool: True if lock was released, False otherwise
        """
        lock_attr = f"_lock_file_{ticket_id}"
        lock_file = getattr(self, lock_attr, None)
        
        try:
            if lock_file:
                # Release the lock
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                delattr(self, lock_attr)
                
                logger.info(f"Lock released for ticket {ticket_id}")
                
                # Try to remove the lock file, but don't worry if it fails
                lock_file_path = os.path.join(self.lock_dir, f"{ticket_id}.lock")
                try:
                    os.remove(lock_file_path)
                except OSError:
                    pass
                    
                return True
            else:
                logger.warning(f"No lock file handle found for ticket {ticket_id}")
                return False
        except Exception as e:
            logger.error(f"Error releasing lock for {ticket_id}: {str(e)}")
            return False
    
    async def cleanup_stale_locks(self, max_age_hours: int = 24) -> int:
        """
        Clean up stale lock files
        
        Args:
            max_age_hours: Maximum age of lock files in hours
            
        Returns:
            int: Number of stale locks cleaned up
        """
        cleaned = 0
        try:
            for filename in os.listdir(self.lock_dir):
                if filename.endswith(".lock"):
                    filepath = os.path.join(self.lock_dir, filename)
                    try:
                        # Try to open with exclusive non-blocking lock to test if it's stale
                        with open(filepath, 'r+') as f:
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                                # If we got here, the lock was stale - delete it
                                os.remove(filepath)
                                cleaned += 1
                                logger.info(f"Cleaned up stale lock: {filename}")
                            except IOError:
                                # Still locked by another process - leave it alone
                                pass
                    except Exception as e:
                        logger.error(f"Error checking stale lock {filename}: {str(e)}")
        except Exception as e:
            logger.error(f"Error cleaning up stale locks: {str(e)}")
            
        return cleaned
    
    async def get_active_locks(self) -> dict:
        """
        Get a list of all active locks
        
        Returns:
            dict: Dictionary mapping ticket IDs to lock information
        """
        locks = {}
        try:
            for filename in os.listdir(self.lock_dir):
                if filename.endswith(".lock"):
                    ticket_id = filename[:-5]  # Remove .lock extension
                    filepath = os.path.join(self.lock_dir, filename)
                    modified_time = os.path.getmtime(filepath)
                    
                    # Read PID from lock file if available
                    pid = None
                    try:
                        with open(filepath, 'r') as f:
                            lines = f.readlines()
                            if len(lines) >= 2:
                                pid = int(lines[1].strip())
                    except:
                        pass
                    
                    # Check if the process still exists
                    process_exists = False
                    if pid is not None:
                        try:
                            os.kill(pid, 0)  # Signal 0 doesn't kill the process, just checks if it exists
                            process_exists = True
                        except OSError:
                            pass
                    
                    locks[ticket_id] = {
                        "locked_since": datetime.fromtimestamp(modified_time).isoformat(),
                        "age_seconds": int(time.time() - modified_time),
                        "pid": pid,
                        "process_active": process_exists
                    }
        except Exception as e:
            logger.error(f"Error getting active locks: {str(e)}")
            
        return locks