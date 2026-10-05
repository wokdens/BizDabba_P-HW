import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from license_manager import (
    normalize_key,
    is_master_activated,
    get_demo_launch_count,
    get_demo_launches_remaining,
    verify_any_license_input,
    activate_master_license,
    verify_demo_key_and_consume,
    reset_license_state_for_testing,
    DEMO_LICENSE_KEYS,
    MASTER_LICENSE_KEYS,
    MAX_DEMO_LAUNCHES
)
import database

class TestLicenseManager(unittest.TestCase):

    def setUp(self):
        # Ensure database tables exist
        database.create_tables()
        # Reset license state to fresh unactivated state with 0 launches
        reset_license_state_for_testing(master_active=False, demo_count=0)

    def tearDown(self):
        # Clean up test license state
        reset_license_state_for_testing(master_active=False, demo_count=0)

    def test_normalize_key(self):
        self.assertEqual(normalize_key("7492-8160"), "74928160")
        self.assertEqual(normalize_key(" 9281-6045-38 "), "9281604538")
        self.assertEqual(normalize_key("8160 2026"), "81602026")
        self.assertEqual(normalize_key(""), "")
        self.assertEqual(normalize_key(None), "")

    def test_initial_state(self):
        self.assertFalse(is_master_activated())
        self.assertEqual(get_demo_launch_count(), 0)
        self.assertEqual(get_demo_launches_remaining(), 50)

    def test_invalid_key_rejected(self):
        ok, k_type, msg, meta = verify_any_license_input("12345678")
        self.assertFalse(ok)
        self.assertEqual(k_type, "invalid")
        self.assertFalse(is_master_activated())
        self.assertEqual(get_demo_launch_count(), 0)

    def test_demo_key_consumption_and_counter(self):
        # 1st launch
        ok, k_type, msg, meta = verify_any_license_input("7492-8160")
        self.assertTrue(ok)
        self.assertEqual(k_type, "demo")
        self.assertEqual(get_demo_launch_count(), 1)
        self.assertEqual(get_demo_launches_remaining(), 49)
        self.assertEqual(meta["used"], 1)
        self.assertEqual(meta["remaining"], 49)
        self.assertIn("1 out of 50 done (49 remaining)", msg)

        # 2nd launch
        ok, k_type, msg, meta = verify_any_license_input("74928160")
        self.assertTrue(ok)
        self.assertEqual(k_type, "demo")
        self.assertEqual(get_demo_launch_count(), 2)
        self.assertEqual(get_demo_launches_remaining(), 48)

    def test_demo_expiration_at_50(self):
        # Set count to 49
        reset_license_state_for_testing(master_active=False, demo_count=49)
        self.assertEqual(get_demo_launch_count(), 49)

        # 50th launch should succeed
        ok, k_type, msg, meta = verify_any_license_input("7492-8160")
        self.assertTrue(ok)
        self.assertEqual(meta["used"], 50)
        self.assertEqual(meta["remaining"], 0)

        # 51st launch with Demo Key MUST FAIL
        ok, k_type, msg, meta = verify_any_license_input("7492-8160")
        self.assertFalse(ok)
        self.assertIn("Demo limit reached", msg)
        self.assertIn("50/50", msg)

    def test_master_key_permanent_activation(self):
        self.assertFalse(is_master_activated())

        # Activate via formatted master key
        ok, k_type, msg, meta = verify_any_license_input("9281-6045-38")
        self.assertTrue(ok)
        self.assertEqual(k_type, "master")
        self.assertTrue(is_master_activated())

        # Check that is_master_activated() persists
        self.assertTrue(is_master_activated())

    def test_master_key_unlocks_expired_demo(self):
        # Simulate demo expired
        reset_license_state_for_testing(master_active=False, demo_count=50)
        self.assertEqual(get_demo_launch_count(), 50)

        # Demo key fails
        ok, k_type, msg, meta = verify_any_license_input("7492-8160")
        self.assertFalse(ok)

        # Entering Master Key activates permanently
        ok, k_type, msg, meta = verify_any_license_input("9281604538")
        self.assertTrue(ok)
        self.assertEqual(k_type, "master")
        self.assertTrue(is_master_activated())

if __name__ == "__main__":
    unittest.main()
