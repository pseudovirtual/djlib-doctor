from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_codex_skill_exists(self):
        skill = ROOT / ".agents" / "skills" / "djlib-doctor" / "SKILL.md"

        self.assertTrue(skill.exists())
        text = skill.read_text(encoding="utf-8")
        self.assertIn("name: djlib-doctor", text)
        self.assertIn("Rekordbox XML exports", text)

    def test_codex_plugin_manifest_points_to_skills(self):
        plugin = ROOT / "plugins" / "djlib-doctor" / ".codex-plugin" / "plugin.json"
        data = json.loads(plugin.read_text(encoding="utf-8"))

        self.assertEqual(data["name"], "djlib-doctor")
        self.assertEqual(data["skills"], "./skills/")
        self.assertTrue((plugin.parents[1] / "skills" / "djlib-doctor" / "SKILL.md").exists())

    def test_repo_marketplace_references_plugin(self):
        marketplace = ROOT / ".agents" / "plugins" / "marketplace.json"
        data = json.loads(marketplace.read_text(encoding="utf-8"))

        self.assertEqual(data["name"], "djlib-doctor-repo")
        self.assertEqual(data["plugins"][0]["name"], "djlib-doctor")
        self.assertEqual(data["plugins"][0]["source"]["path"], "./plugins/djlib-doctor")

    def test_claude_extension_is_marked_as_template(self):
        readme = ROOT / "claude-desktop-extension" / "README.md"
        manifest = ROOT / "claude-desktop-extension" / "manifest.template.json"

        self.assertTrue(readme.exists())
        self.assertTrue(manifest.exists())
        self.assertIn("not installable yet", readme.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["name"], "djlib-doctor")

    def test_release_workflow_builds_and_publishes_package(self):
        workflow = ROOT / ".github" / "workflows" / "release.yml"
        text = workflow.read_text(encoding="utf-8")

        self.assertIn("pypa/gh-action-pypi-publish", text)
        self.assertIn("python -m build", text)
        self.assertIn("tags:", text)


if __name__ == "__main__":
    unittest.main()
