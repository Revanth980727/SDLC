
#!/usr/bin/env python3
import asyncio
import logging
import os
import tempfile
import time
import unittest
from concurrent.futures import ProcessPoolExecutor
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the TicketLockManager
from ticket_lock import TicketLockManager

class TestTicketLock(unittest.TestCase):
    """Test cases for TicketLockManager"""
    
    def setUp(self):
        """Set up a temporary directory for lock files"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.lock_manager = TicketLockManager(self.temp_dir.name)
        
    def tearDown(self):
        """Clean up the temporary directory"""
        self.temp_dir.cleanup()
        
    def test_acquire_lock(self):
        """Test acquiring a lock"""
        # Acquire lock
        result = asyncio.run(self.lock_manager.acquire_lock("TEST-123"))
        self.assertTrue(result)
        
        # Check lock file exists
        lock_file = os.path.join(self.temp_dir.name, "TEST-123.lock")
        self.assertTrue(os.path.exists(lock_file))
        
    def test_acquire_twice(self):
        """Test acquiring the same lock twice"""
        # Acquire lock first time
        result1 = asyncio.run(self.lock_manager.acquire_lock("TEST-123"))
        self.assertTrue(result1)
        
        # Try to acquire it again
        result2 = asyncio.run(self.lock_manager.acquire_lock("TEST-123"))
        self.assertFalse(result2)
        
    def test_release_lock(self):
        """Test releasing a lock"""
        # Acquire and then release
        asyncio.run(self.lock_manager.acquire_lock("TEST-123"))
        result = asyncio.run(self.lock_manager.release_lock("TEST-123"))
        self.assertTrue(result)
        
        # Check lock file is removed
        lock_file = os.path.join(self.temp_dir.name, "TEST-123.lock")
        self.assertFalse(os.path.exists(lock_file))
        
    def test_acquire_after_release(self):
        """Test acquiring a lock after releasing it"""
        # Acquire, release, then acquire again
        asyncio.run(self.lock_manager.acquire_lock("TEST-123"))
        asyncio.run(self.lock_manager.release_lock("TEST-123"))
        result = asyncio.run(self.lock_manager.acquire_lock("TEST-123"))
        self.assertTrue(result)
        
    def test_stale_lock_cleanup(self):
        """Test cleaning up stale locks"""
        # Create a "stale" lock file manually
        lock_file = os.path.join(self.temp_dir.name, "TEST-123.lock")
        with open(lock_file, 'w') as f:
            f.write("test")
            
        # Modify the access and modify time to simulate an old file
        os.utime(lock_file, (time.time() - 3700, time.time() - 3700))  # 1 hour + 100 secs ago
        
        # Clean up stale locks
        cleaned = asyncio.run(self.lock_manager.cleanup_stale_locks(max_age_hours=1))
        self.assertEqual(cleaned, 1)
        self.assertFalse(os.path.exists(lock_file))
        
    def test_get_active_locks(self):
        """Test getting active locks"""
        # Create some locks
        asyncio.run(self.lock_manager.acquire_lock("TEST-123"))
        asyncio.run(self.lock_manager.acquire_lock("TEST-456"))
        
        # Get active locks
        locks = asyncio.run(self.lock_manager.get_active_locks())
        self.assertEqual(len(locks), 2)
        self.assertIn("TEST-123", locks)
        self.assertIn("TEST-456", locks)

# Async test function for running multiple tests concurrently
async def run_async_tests():
    # Create a temporary directory
    temp_dir = tempfile.TemporaryDirectory()
    lock_manager = TicketLockManager(temp_dir.name)
    
    # Test concurrent lock acquisition
    async def try_acquire(ticket_id):
        return await lock_manager.acquire_lock(ticket_id)
    
    # Try to acquire the same lock from multiple concurrent tasks
    results = await asyncio.gather(
        try_acquire("CONCURRENT-1"),
        try_acquire("CONCURRENT-1"),
        try_acquire("CONCURRENT-1")
    )
    
    # Only one should succeed
    assert sum(results) == 1, f"Expected exactly one successful lock, got {sum(results)}"
    
    # Clean up
    await lock_manager.release_lock("CONCURRENT-1")
    temp_dir.cleanup()
    
    logger.info("Concurrent lock test passed!")

def test_in_subprocess(lock_dir, ticket_id):
    """Test function to run in a subprocess"""
    import asyncio
    from ticket_lock import TicketLockManager
    
    async def acquire_and_hold():
        lock_manager = TicketLockManager(lock_dir)
        result = await lock_manager.acquire_lock(ticket_id)
        if result:
            # Hold the lock for 2 seconds
            await asyncio.sleep(2)
            await lock_manager.release_lock(ticket_id)
        return result
    
    return asyncio.run(acquire_and_hold())

async def run_multiprocess_test():
    """Test locking across multiple processes"""
    # Create a temporary directory
    temp_dir = tempfile.TemporaryDirectory()
    
    # Create a lock manager in the main process
    lock_manager = TicketLockManager(temp_dir.name)
    
    # Start a subprocess that acquires and holds a lock
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(test_in_subprocess, temp_dir.name, "MULTI-1")
        
        # Give the subprocess time to acquire the lock
        await asyncio.sleep(0.5)
        
        # Try to acquire the same lock in the main process
        result = await lock_manager.acquire_lock("MULTI-1")
        
        # The lock should be held by the subprocess
        assert result == False, "Lock should be held by subprocess"
        
        # Wait for the subprocess to finish and release the lock
        assert future.result() == True, "Subprocess should acquire the lock"
        
        # Now we should be able to acquire the lock
        result = await lock_manager.acquire_lock("MULTI-1")
        assert result == True, "Lock should be available after subprocess release"
        
        # Clean up
        await lock_manager.release_lock("MULTI-1")
    
    # Clean up the temporary directory
    temp_dir.cleanup()
    
    logger.info("Multiprocess lock test passed!")

if __name__ == "__main__":
    # Run the unittest tests
    unittest.main(exit=False)
    
    # Run the async tests
    asyncio.run(run_async_tests())
    
    # Run the multiprocess tests
    asyncio.run(run_multiprocess_test())
    
    logger.info("All tests completed successfully!")