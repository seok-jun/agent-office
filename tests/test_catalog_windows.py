import tkinter as tk
import unittest
from unittest.mock import patch

from app import AgentOffice


class CatalogWindowTests(unittest.TestCase):
    def test_repeated_open_reuses_window_and_reopen_after_close_works(self):
        with patch('office.load_sheet', return_value=None):
            app = AgentOffice(demo=True)
        try:
            for method, key in ((app.pet_catalog, 'pets'), (app.clawd_catalog, 'clawd')):
                method()
                first = app.catalog_windows[key]
                children = first.winfo_children()
                first.withdraw()
                method()
                app.root.update_idletasks()
                self.assertIs(app.catalog_windows[key], first)
                self.assertEqual(first.winfo_children(), children)
                self.assertNotEqual(first.state(), 'withdrawn')
                first.destroy()
                method()
                self.assertIsNot(app.catalog_windows[key], first)
            self.assertEqual(len([w for w in app.root.winfo_children()
                                  if isinstance(w, tk.Toplevel)]), 2)
        finally:
            app.close()
