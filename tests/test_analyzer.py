import unittest

from open_world_watch.analyzer import analyze_text, is_relevant, matches_query, summarize_articles


class AnalyzerTests(unittest.TestCase):
    def test_relevant_ps5_open_world_article(self):
        result = analyze_text(
            "Crimson Harbor launches as an open world game for PS5",
            "The preorder price is $69.99 with a new gameplay trailer.",
        )

        self.assertTrue(is_relevant("Crimson Harbor launches as an open world game for PS5"))
        self.assertIn("Open World", result["matched_terms"])
        self.assertIn("PS5", result["platforms"])
        self.assertIn("$69.99", result["prices"])
        self.assertIn("Crimson Harbor", result["games"])
        self.assertIn("price", result["tags"])

    def test_relevant_switch_2_open_world_article(self):
        result = analyze_text(
            "Open-world adventure Azure Fields arrives on Nintendo Switch 2",
            "A release date trailer confirms the new version.",
        )

        self.assertIn("Nintendo Switch 2", result["platforms"])
        self.assertIn("release date", result["tags"])
        self.assertIn("trailer", result["tags"])

    def test_price_signal_is_tagged_without_price_word(self):
        result = analyze_text(
            "Open world game Star Trail for PlayStation 5",
            "Available at 70 dollars during launch week.",
        )

        self.assertIn("price", result["tags"])
        self.assertIn("70 dollars", result["prices"])

    def test_relevant_pc_and_xbox_open_world_articles(self):
        pc_result = analyze_text("Crimson Harbor launches as an open world RPG on PC and Steam")
        xbox_result = analyze_text("Azure Fields open-world adventure arrives on Xbox Series X")

        self.assertTrue(is_relevant("Crimson Harbor launches as an open world RPG on PC and Steam"))
        self.assertTrue(is_relevant("Azure Fields open-world adventure arrives on Xbox Series X"))
        self.assertIn("PC", pc_result["platforms"])
        self.assertIn("Xbox Series X|S", xbox_result["platforms"])

    def test_relevant_new_gaming_system_news_without_open_world(self):
        result = analyze_text(
            "Xbox successor console reveal reportedly coming this fall",
            "The new gaming system would include handheld hardware features.",
        )

        self.assertTrue(is_relevant("Xbox successor console reveal reportedly coming this fall"))
        self.assertIn("Gaming System News", result["matched_terms"])
        self.assertIn("Xbox", result["platforms"])
        self.assertIn("system news", result["tags"])

    def test_game_clusters_ignore_headline_fragments(self):
        result = analyze_text(
            "Xbox successor console reveal reportedly coming this fall",
            "The new gaming system would include handheld hardware features.",
        )

        self.assertEqual(result["games"], [])

    def test_custom_query_matches_keywords_without_platform_requirement(self):
        self.assertTrue(matches_query("Hollow Knight Silksong release date trailer", "", "Silksong release trailer"))
        self.assertTrue(is_relevant("Hollow Knight Silksong release date trailer", query="Silksong release trailer"))
        self.assertFalse(matches_query("Hollow Knight Silksong trailer", "", "Metroid Prime 4"))

    def test_requires_open_world_and_platform(self):
        self.assertFalse(is_relevant("A PS5 racing game gets an update"))
        self.assertFalse(is_relevant("A new open world RPG is teased"))
        self.assertFalse(is_relevant("A new gaming system rumor has no platform named"))

    def test_summary_counts_groups(self):
        summary = summarize_articles(
            [
                {
                    "source": "IGN",
                    "platforms": ["PS5"],
                    "games": ["Crimson Harbor"],
                    "prices": ["$69.99"],
                    "tags": ["price", "PS5"],
                },
                {
                    "source": "Polygon",
                    "platforms": ["Nintendo Switch 2"],
                    "games": [],
                    "prices": [],
                    "tags": ["Nintendo Switch 2"],
                },
            ]
        )

        self.assertEqual(summary["total_articles"], 2)
        self.assertEqual(summary["platform_counts"]["PS5"], 1)
        self.assertNotIn("Unclassified", summary["game_counts"])
        self.assertEqual(summary["price_signal_count"], 1)


if __name__ == "__main__":
    unittest.main()
