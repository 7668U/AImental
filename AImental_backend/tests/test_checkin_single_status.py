import unittest

from model.checkin_dimensions import enrich_checkin_payload


class CheckinSingleStatusTestCase(unittest.TestCase):
    def test_enrich_checkin_payload_keeps_only_first_status(self):
        payload = enrich_checkin_payload(
            {
                "mood": "平静",
                "color": "#8BB8FF",
                "tags": "学习,放空,宅家",
            }
        )

        self.assertEqual(payload["tags"], "学习")
        self.assertEqual(payload["status_ids"], '["book"]')
        self.assertEqual(payload["status_families"], '["工作学习"]')

    def test_status_ids_are_also_reduced_to_one(self):
        payload = enrich_checkin_payload(
            {
                "mood": "平静",
                "color": "#8BB8FF",
                "status_ids": ["outdoor", "fitness"],
            }
        )

        self.assertEqual(payload["tags"], "户外")
        self.assertEqual(payload["status_ids"], '["outdoor"]')
        self.assertEqual(payload["status_families"], '["运动健康"]')


if __name__ == "__main__":
    unittest.main()
