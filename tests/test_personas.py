"""Unit tests for Multi-Tenant Nonprofit Personas."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.personas import (
    PERSONAS,
    get_persona_by_id,
    persona_to_org_profile,
)
from backend.storage.local_storage import storage


class TestNonprofitPersonas(unittest.TestCase):
    """Test suite for multi-tenant nonprofit personas and sector switching."""

    def test_01_personas_catalog(self):
        """Verify standard sector personas exist with complete metadata."""
        self.assertGreaterEqual(len(PERSONAS), 4)
        persona_ids = [p.id for p in PERSONAS]
        self.assertIn("youth-stem", persona_ids)
        self.assertIn("food-security", persona_ids)
        self.assertIn("clean-water", persona_ids)
        self.assertIn("veterans-health", persona_ids)

    def test_02_persona_lookup_and_profile_conversion(self):
        """Verify converting persona to OrgProfile maintains all sectoral fields."""
        food_bank = get_persona_by_id("food-security")
        self.assertIsNotNone(food_bank)
        assert food_bank is not None

        profile = persona_to_org_profile(food_bank)
        self.assertEqual(profile.name, "Second Harvest Community Network")
        self.assertEqual(profile.annual_budget, 850000)
        self.assertIn("food security", profile.keywords)
        self.assertTrue(len(profile.programs) > 0)

    def test_03_switch_active_persona_storage(self):
        """Verify saving switched persona to storage."""
        water_persona = get_persona_by_id("clean-water")
        assert water_persona is not None
        profile = persona_to_org_profile(water_persona)

        saved_id = storage.save_org_profile(profile.model_dump())
        self.assertEqual(saved_id, "default")

        retrieved = storage.get_org_profile("default")
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved["name"], "Clearwater Watershed Coalition")
        self.assertIn("clean drinking water", retrieved["keywords"])

        # Reset back to STEM default
        stem_persona = get_persona_by_id("youth-stem")
        assert stem_persona is not None
        storage.save_org_profile(persona_to_org_profile(stem_persona).model_dump())


if __name__ == "__main__":
    unittest.main(verbosity=2)
