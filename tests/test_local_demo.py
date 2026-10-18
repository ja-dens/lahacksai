import unittest

from src.local_demo import collect_scenes, embed_json, render_page


class LocalDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenes, cls.sticker = collect_scenes()
        cls.by_id = {scene['id']: scene for scene in cls.scenes}

    def test_page_uses_the_pipeline_explanation_and_real_sticker(self):
        single = self.by_id['single']
        self.assertEqual(single['messages'][0]['text'], 'I tried to catch some fog yesterday. I mist.')
        self.assertEqual(single['messages'][1]['text'], 'That joke got me.')
        self.assertEqual(
            single['explanation'],
            'This probably means the joke was so funny they are crying.\n'
            'This is a likely interpretation, not confirmed sender intent.',
        )
        self.assertEqual(single['destination'], 'demo-private-assistant-thread')
        self.assertEqual(single['recipient'], 'Older recipient')
        self.assertEqual(single['model_calls'], 1)
        self.assertEqual(single['sends'], 1)
        self.assertTrue(single['replayed'])
        self.assertTrue(self.sticker.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_policy_cases_keep_private_routing(self):
        self.assertIn('playfully encouraging more jokes', self.by_id['compatible']['explanation'])
        self.assertNotIn('sarcastically', self.by_id['opposing']['explanation'])
        self.assertIn('sarcasm is still possible', self.by_id['opposing']['explanation'])
        self.assertEqual(
            self.by_id['unsupported']['explanation'],
            'I cannot reliably interpret this sticker from the available information.',
        )
        direct = self.by_id['direct']
        self.assertEqual(direct['destination'], 'demo-family-chat')
        self.assertEqual(direct['explanation'], self.by_id['single']['explanation'])
        for scene in self.scenes:
            self.assertEqual(scene['model_calls'], 1)
            self.assertEqual(scene['sends'], 1)

    def test_page_embeds_fixture_text_without_breaking_the_script(self):
        page = render_page(self.scenes)
        self.assertIn('I tried to catch some fog yesterday. I mist.', page)
        self.assertIn('/sticker.png', page)
        self.assertIn('What this sticker means', page)
        self.assertIn('id="draft"', page)
        self.assertIn('id="popup"', page)
        self.assertIn('Grandchild', page)
        self.assertNotIn('<script>', embed_json([{'text': '<script>alert(1)</script>'}]))
        self.assertIn('\\u003cscript>', embed_json([{'text': '<script>alert(1)</script>'}]))
